from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from fastapi import HTTPException

from redis.asyncio import Redis 
from app.core.cache_keys import workflow_cache_key

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskCreateNested
from app.services.workflow_service import get_workflow

async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_tasks_by_workflow(db: AsyncSession, workflow_id: int, skip: int = 0, limit: int = 100) -> List[Task]:
    query = select(Task).where(Task.workflow_id == workflow_id).order_by(Task.sequence).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def create_task(db: AsyncSession, *, obj_in: TaskCreate, redis_client: Redis | None = None) -> Task:
    workflow = await get_workflow(db, obj_in.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Parent workflow not found")
    db_obj = Task(**obj_in.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    # --- Invalidate PARENT Workflow Cache ---
    if redis_client:
        cache_key = workflow_cache_key(obj_in.workflow_id)
        try:
            await redis_client.delete(cache_key)
            print(f"Invalidated parent workflow cache for key {cache_key} due to task creation")
        except Exception as e:
            print(f"Redis DELETE error for key {cache_key}: {e}")
    # --- End Invalidation ---

    return db_obj

async def create_workflow_task(
    db: AsyncSession, *,
    obj_in: TaskCreateNested,
    workflow_id: int,
    redis_client: Redis | None = None 
) -> Task:
    db_obj = Task(**obj_in.model_dump(), workflow_id=workflow_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    # --- Invalidate PARENT Workflow Cache ---
    if redis_client:
        cache_key = workflow_cache_key(workflow_id)
        try:
            await redis_client.delete(cache_key)
            print(f"Invalidated parent workflow cache for key {cache_key} due to task creation")
        except Exception as e:
            print(f"Redis DELETE error for key {cache_key}: {e}")
    # --- End Invalidation ---

    return db_obj


async def update_task(
    db: AsyncSession, *,
    db_obj: Task, 
    obj_in: TaskUpdate,
    redis_client: Redis | None = None 
) -> Task:
    """
    Updates a task and invalidates the parent workflow cache.
    """
    parent_workflow_id = db_obj.workflow_id

    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit() 
    await db.refresh(db_obj) 

    # --- Invalidate PARENT Workflow Cache ---
    if redis_client and parent_workflow_id is not None:
        cache_key = workflow_cache_key(parent_workflow_id)
        try:
            await redis_client.delete(cache_key)
            print(f"Invalidated parent workflow cache for key {cache_key} due to task update")
        except Exception as e:
            print(f"Redis DELETE error during task update for key {cache_key}: {e}")
    # --- End Invalidation ---

    return db_obj

async def delete_task(
    db: AsyncSession, *,
    task_id: int,
    redis_client: Redis | None = None 
) -> Optional[Task]:
    """
    Deletes a task and invalidates the parent workflow cache.
    """
    db_obj = await get_task(db, task_id)

    if db_obj:
        parent_workflow_id = db_obj.workflow_id

        await db.delete(db_obj) 
        await db.commit() 

        # --- Invalidate PARENT Workflow Cache ---
        if redis_client and parent_workflow_id is not None:
            cache_key = workflow_cache_key(parent_workflow_id)
            try:
                await redis_client.delete(cache_key)
                print(f"Invalidated parent workflow cache for key {cache_key} due to task deletion")
            except Exception as e:
                 # Log Redis errors but don't let them break the main operation
                print(f"Redis DELETE error during task deletion for key {cache_key}: {e}")
        # --- End Invalidation ---

        return db_obj 
    return None