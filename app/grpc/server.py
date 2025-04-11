import asyncio
import uuid

from app.db.redis_session import get_redis_client
from redis.asyncio import Redis

async def get_redis() -> Redis:
  return await get_redis_client()


from app.grpc.generated import workflow_pb2
from app.grpc.generated import workflow_pb2_grpc
import grpc

from app.db.session import AsyncSessionFactory 
from app.models.enums import StatusEnum as AppStatusEnum 
from app.services import workflow_service, workflow_execution_service 
from app.models import Workflow, Task, WorkflowExecution 

def map_status_to_proto(app_status: AppStatusEnum) -> workflow_pb2.ExecutionStatus:
    status_map = {
        AppStatusEnum.PENDING: workflow_pb2.PENDING,
        AppStatusEnum.RUNNING: workflow_pb2.RUNNING,
        AppStatusEnum.COMPLETED: workflow_pb2.COMPLETED,
        AppStatusEnum.FAILED: workflow_pb2.FAILED,
        AppStatusEnum.CANCELLED: workflow_pb2.CANCELLED,
    }
    return status_map.get(app_status, workflow_pb2.STATUS_UNSPECIFIED)

async def execute_task_logic(task: Task, db_session) -> tuple[bool, str]:
    """
    Executes the actual logic for a single task.
    Returns (success_boolean, message_string).
    """
    print(f"--- Executing Task: {task.id} - {task.name} (Execution Type: {task.execution_type}) ---")

    # Simulate task execution:
    await asyncio.sleep(1) # Simulate work
    success = True # Simulate task success
    message = f"Task {task.name} completed successfully." if success else f"Task {task.name} failed."
    print(f"--- Finished Task: {task.id} - {task.name} ---")
    return success, message


class WorkflowServiceImpl(workflow_pb2_grpc.WorkflowServiceServicer):

    async def ExecuteWorkflow(self, request: workflow_pb2.ExecuteWorkflowRequest, context):
        """
        Triggers workflow execution and streams status updates.
        """
        execution_id = uuid.uuid4()
        print(f"Received request to execute workflow: {request.workflow_id}, Execution ID: {execution_id}")

        async with AsyncSessionFactory() as session: 
            try:
                workflow_def: Workflow | None = await workflow_service.get_workflow(db=session, workflow_id=int(request.workflow_id)) # Assuming ID is int
                if not workflow_def or not workflow_def.tasks:
                    yield workflow_pb2.WorkflowExecutionUpdate(
                        execution_id=str(execution_id),
                        workflow_id=request.workflow_id,
                        status=workflow_pb2.FAILED,
                        message=f"Workflow definition '{request.workflow_id}' not found or has no tasks."
                    )
                    print(f"Execution {execution_id}: Workflow definition {request.workflow_id} not found or empty.")
                    return

                execution_db = await workflow_execution_service.create_execution(
                    db=session,
                    workflow_definition_id=workflow_def.id,
                    initial_status=AppStatusEnum.PENDING,
                    execution_id=execution_id
                )

                yield workflow_pb2.WorkflowExecutionUpdate(
                    execution_id=str(execution_id),
                    workflow_id=request.workflow_id,
                    status=workflow_pb2.PENDING,
                    message="Workflow execution initiated."
                )

                execution_db = await workflow_execution_service.update_execution_status(
                    db=session, execution_obj=execution_db, status=AppStatusEnum.RUNNING, message="Execution started."
                )
                yield workflow_pb2.WorkflowExecutionUpdate(
                    execution_id=str(execution_id),
                    workflow_id=request.workflow_id,
                    status=workflow_pb2.RUNNING,
                    message="Workflow execution started."
                )
                print(f"Execution {execution_id}: Status RUNNING")

                tasks_by_sequence = {}
                for task in sorted(workflow_def.tasks, key=lambda t: t.sequence):
                    tasks_by_sequence.setdefault(task.sequence, []).append(task)

                final_status = AppStatusEnum.COMPLETED
                final_message = "Workflow completed successfully."

                for sequence_num in sorted(tasks_by_sequence.keys()):
                    tasks_in_sequence = tasks_by_sequence[sequence_num]
                    print(f"Execution {execution_id}: Processing sequence {sequence_num}")

                    async_tasks_coroutines = []
                    sync_tasks = []

                    for task in tasks_in_sequence:
                        if task.execution_type == "async":
                            async_tasks_coroutines.append(execute_task_logic(task, session))
                        else:
                            sync_tasks.append(task)

                    # Execute synchronous tasks sequentially first
                    for task in sync_tasks:
                        yield workflow_pb2.WorkflowExecutionUpdate(
                            execution_id=str(execution_id), workflow_id=request.workflow_id, status=workflow_pb2.RUNNING,
                            current_task_id=str(task.id), current_task_name=task.name, message=f"Starting task {task.name}"
                        )
                        success, message = await execute_task_logic(task, session)
                        yield workflow_pb2.WorkflowExecutionUpdate(
                             execution_id=str(execution_id), workflow_id=request.workflow_id, status=workflow_pb2.RUNNING,
                             current_task_id=str(task.id), current_task_name=task.name, message=message
                        )
                        if not success:
                            final_status = AppStatusEnum.FAILED
                            final_message = f"Workflow failed at task '{task.name}': {message}"
                            print(f"Execution {execution_id}: Failed at sync task {task.name}")
                            break 

                    if final_status == AppStatusEnum.FAILED: break 

                    # Execute asynchronous tasks concurrently (if any)
                    if async_tasks_coroutines:
                        yield workflow_pb2.WorkflowExecutionUpdate(
                            execution_id=str(execution_id), workflow_id=request.workflow_id, status=workflow_pb2.RUNNING,
                            message=f"Starting {len(async_tasks_coroutines)} parallel tasks for sequence {sequence_num}..."
                        )
                        results = await asyncio.gather(*async_tasks_coroutines, return_exceptions=True)

                        for i, result in enumerate(results):
                            task = next(t for t in tasks_in_sequence if t.execution_type == "async")
                            if isinstance(result, Exception):
                                success = False
                                message = f"Parallel task '{task.name}' failed: {result}"
                                final_status = AppStatusEnum.FAILED
                                final_message = f"Workflow failed at parallel task '{task.name}': {result}"
                                print(f"Execution {execution_id}: Failed at async task {task.name}")
                            else:
                                success, message = result

                            yield workflow_pb2.WorkflowExecutionUpdate(
                                execution_id=str(execution_id), workflow_id=request.workflow_id, status=workflow_pb2.RUNNING,
                                current_task_id=str(task.id), current_task_name=task.name, message=message
                            )
                            if not success and final_status != AppStatusEnum.FAILED: 
                                final_status = AppStatusEnum.FAILED
                                final_message = f"Workflow failed at parallel task '{task.name}': {message}"
                                print(f"Execution {execution_id}: Failed at async task {task.name}")

                    if final_status == AppStatusEnum.FAILED: break 

                await workflow_execution_service.update_execution_status(
                    db=session, execution_obj=execution_db, status=final_status, message=final_message
                )
                yield workflow_pb2.WorkflowExecutionUpdate(
                    execution_id=str(execution_id),
                    workflow_id=request.workflow_id,
                    status=map_status_to_proto(final_status),
                    message=final_message
                )
                print(f"Execution {execution_id}: Final status {final_status.value}")

            except Exception as e:
                print(f"Execution {execution_id}: Unhandled exception: {e}")
                try:
                     if 'execution_db' in locals() and execution_db:
                          await workflow_execution_service.update_execution_status(
                              db=session, execution_obj=execution_db, status=AppStatusEnum.FAILED, message=f"Internal error: {e}"
                          )
                except Exception as db_err:
                     print(f"Execution {execution_id}: Failed to update DB on error: {db_err}")

                yield workflow_pb2.WorkflowExecutionUpdate(
                    execution_id=str(execution_id),
                    workflow_id=request.workflow_id,
                    status=workflow_pb2.FAILED,
                    message=f"Internal server error during execution: {e}"
                )


    async def GetWorkflowStatus(self, request: workflow_pb2.GetWorkflowStatusRequest, context):
        """
        Gets the current status of a specific workflow execution.
        """
        print(f"Received request for status of execution: {request.execution_id}")
        async with AsyncSessionFactory() as session:
            try:
                execution_id_uuid = uuid.UUID(request.execution_id) 
                execution_db: WorkflowExecution | None = await workflow_execution_service.get_execution(db=session, execution_id=execution_id_uuid)

                if not execution_db:
                     await context.abort(grpc.StatusCode.NOT_FOUND, f"Execution ID '{request.execution_id}' not found.")

                return workflow_pb2.WorkflowStatusResponse(
                    execution_id=str(execution_db.id),
                    workflow_id=str(execution_db.workflow_definition_id), 
                    status=map_status_to_proto(execution_db.status),
                    last_message=execution_db.last_message or ""
                )
            except ValueError:
                 await context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Invalid Execution ID format: '{request.execution_id}'. Expected UUID.")
            except Exception as e:
                 print(f"Error fetching status for {request.execution_id}: {e}")
                 await context.abort(grpc.StatusCode.INTERNAL, "Internal server error fetching status.")