from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.redis_session import get_redis_client
from redis.asyncio import Redis

async def get_redis() -> Redis:
  return await get_redis_client()

from app import schemas 
from app import services
from app.db.session import get_session
from app.schemas.pagination import Page

router = APIRouter()

@router.post("/", response_model=schemas.Workflow, status_code=201)
async def create_workflow(
    *,
    db: AsyncSession = Depends(get_session),
    workflow_in: schemas.WorkflowCreate,
):
    """
    Create a new workflow.
    """
    workflow = await services.workflow_service.create_workflow(db=db, obj_in=workflow_in)
    return workflow

@router.get("/", response_model=Page[schemas.Workflow])
async def read_workflows(
    db: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = Query(default=100, le=200),
):
    """
    Retrieve workflows with their tasks.
    """
    workflows = await services.workflow_service.get_workflows(db=db, skip=skip, limit=limit)
    return workflows

@router.get("/{workflow_id}", response_model=schemas.Workflow)
async def read_workflow(
    *,
    db: AsyncSession = Depends(get_session),
    workflow_id: int,
    redis_client: Redis = Depends(get_redis),
):
    """
    Get a specific workflow by ID, including its tasks.
    """
    db_workflow = await services.workflow_service.get_workflow(db=db, workflow_id=workflow_id, redis_client=redis_client)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow

@router.put("/{workflow_id}", response_model=schemas.Workflow)
async def update_workflow(
    *,
    db: AsyncSession = Depends(get_session),
    workflow_id: int,
    workflow_in: schemas.WorkflowUpdate,
    redis_client: Redis = Depends(get_redis),
):
    """
    Update a workflow.
    """
    db_workflow = await services.workflow_service.get_workflow(db=db, workflow_id=workflow_id, redis_client=redis_client)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    updated_workflow = await services.workflow_service.update_workflow(
        db=db, db_obj=db_workflow, obj_in=workflow_in, redis_client=redis_client
    )
    return updated_workflow

@router.delete("/{workflow_id}", response_model=schemas.Workflow)
async def delete_workflow(
    *,
    db: AsyncSession = Depends(get_session),
    workflow_id: int,
    redis_client: Redis = Depends(get_redis),
):
    """
    Delete a workflow and its associated tasks.
    """
    deleted_workflow = await services.workflow_service.delete_workflow(db=db, workflow_id=workflow_id, redis_client=redis_client)
    if not deleted_workflow:
         raise HTTPException(status_code=404, detail="Workflow not found")
    return deleted_workflow


# --- Endpoints for managing tasks *within* a workflow ---

@router.post("/{workflow_id}/tasks/", response_model=schemas.Task, status_code=201)
async def create_task_for_workflow(
    *,
    db: AsyncSession = Depends(get_session),
    workflow_id: int,
    task_in: schemas.TaskCreateNested,
    redis_client: Redis = Depends(get_redis),
):
    """
    Create a task associated with a specific workflow.
    """
    db_workflow = await services.workflow_service.get_workflow(db=db, workflow_id=workflow_id, redis_client=redis_client)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Parent workflow not found")

    task = await services.task_service.create_workflow_task(
        db=db, obj_in=task_in, workflow_id=workflow_id, redis_client=redis_client
    )
    return task

@router.get("/{workflow_id}/tasks/", response_model=List[schemas.Task])
async def read_workflow_tasks(
    *,
    db: AsyncSession = Depends(get_session),
    workflow_id: int,
    skip: int = 0,
    limit: int = Query(default=100, le=200),
    redis_client: Redis = Depends(get_redis),
):
    """
    Retrieve tasks for a specific workflow.
    """
    db_workflow = await services.workflow_service.get_workflow(db=db, workflow_id=workflow_id, redis_client=redis_client)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Parent workflow not found")

    tasks = await services.task_service.get_tasks_by_workflow(
        db=db, workflow_id=workflow_id, skip=skip, limit=limit
    )
    return tasks