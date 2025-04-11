import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from fastapi import HTTPException

from app.models.workflow_execution import WorkflowExecution
from app.models.enums import StatusEnum

async def create_execution(db: AsyncSession, *, workflow_definition_id: int, initial_status: StatusEnum, execution_id: uuid.UUID) -> WorkflowExecution:
    db_obj = WorkflowExecution(
        id=execution_id,
        workflow_definition_id=workflow_definition_id,
        status=initial_status
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_execution(db: AsyncSession, *, execution_id: uuid.UUID) -> WorkflowExecution | None:
    query = select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    result = await db.execute(query)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow Execution Not Found")
    return result.scalar_one_or_none()

async def update_execution_status(db: AsyncSession, *, execution_obj: WorkflowExecution, status: StatusEnum, message: str | None = None) -> WorkflowExecution:
    execution_obj.status = status
    if message:
        execution_obj.last_message = message
    # if status in [StatusEnum.COMPLETED, StatusEnum.FAILED]:
    #     execution_obj.finished_at = datetime.utcnow().replace(tzinfo=timezone.utc)
    db.add(execution_obj)
    await db.commit()
    await db.refresh(execution_obj)
    return execution_obj