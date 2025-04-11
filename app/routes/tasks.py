from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis_session import get_redis_client
from redis.asyncio import Redis

async def get_redis() -> Redis:
  return await get_redis_client()

from app import schemas
from app import services
from app.db.session import get_session

router_tasks = APIRouter() 

@router_tasks.get("/{task_id}", response_model=schemas.Task)
async def read_task(
    *,
    db: AsyncSession = Depends(get_session),
    task_id: int,
):
    """
    Get a specific task by ID.
    """
    db_task = await services.task_service.get_task(db=db, task_id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@router_tasks.put("/{task_id}", response_model=schemas.Task)
async def update_task(
    *,
    db: AsyncSession = Depends(get_session),
    task_id: int,
    task_in: schemas.TaskUpdate,
    redis_client: Redis = Depends(get_redis),
):
    """
    Update a specific task.
    """
    db_task = await services.task_service.get_task(db=db, task_id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    updated_task = await services.task_service.update_task(db=db, db_obj=db_task, obj_in=task_in, redis_client=redis_client)
    return updated_task

@router_tasks.delete("/{task_id}", response_model=schemas.Task)
async def delete_task(
    *,
    db: AsyncSession = Depends(get_session),
    task_id: int,
    redis_client: Redis = Depends(get_redis),
):
    """
    Delete a specific task.
    """
    deleted_task = await services.task_service.delete_task(db=db, task_id=task_id, redis_client=redis_client)
    if not deleted_task:
         raise HTTPException(status_code=404, detail="Task not found")
    return deleted_task