from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 
from sqlalchemy import func
from typing import Optional

from redis.asyncio import Redis 
from app.core.cache_keys import workflow_cache_key

from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.workflow import Workflow as WorkflowSchema 
from app.schemas.pagination import Page 


async def get_workflow(
    db: AsyncSession,
    workflow_id: int,
    redis_client: Redis | None = None
) -> Workflow | None: 
    """
    Gets a workflow, checking cache first.
    Returns the ORM model. Caching uses the Schema representation.
    """
    cache_key = workflow_cache_key(workflow_id)
    cached_workflow_json: str | None = None

    if redis_client:
        try:
            cached_workflow_json = await redis_client.get(cache_key)
        except Exception as e:
            print(f"Redis GET error for key {cache_key}: {e}") 
            
    if cached_workflow_json:
        print(f"Cache HIT for key {cache_key}")
        try:
            workflow_schema = WorkflowSchema.model_validate_json(cached_workflow_json)
            return workflow_schema 

        except Exception as e:
            print(f"Error deserializing cached workflow {cache_key}: {e}")
            await redis_client.delete(cache_key)


    print(f"Cache MISS or bypass for key {cache_key}")
    query = select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.tasks))
    result = await db.execute(query)
    db_workflow = result.scalar_one_or_none()

    if not redis_client:
        print("redis client not found")

    if db_workflow and redis_client:
        try:
            workflow_to_cache = WorkflowSchema.model_validate(db_workflow)
            value_to_cache = workflow_to_cache.model_dump_json()

            await redis_client.set(
                cache_key,
                value_to_cache,
            )
            print(f"Cached data for key {cache_key}")
        except Exception as e:
             print(f"Redis SET error for key {cache_key}: {e}") 

    return db_workflow 

async def get_workflows(db: AsyncSession, skip: int = 0, limit: int = 100) -> Page[WorkflowSchema]:
    """
    Retrieve a paginated list of workflows.
    """
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 100

    count_query = select(func.count(Workflow.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() 

    items_query = (
        select(Workflow)
        .offset(skip)
        .limit(limit)
        .options(selectinload(Workflow.tasks)) 
        .order_by(Workflow.id) 
    )
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()

    page = (skip // limit) + 1 if limit > 0 else 1
    pages = (total + limit - 1) // limit if limit > 0 else (1 if total > 0 else 0)

    return Page[WorkflowSchema](
        items=items,
        page=page,
        size=limit,
        total=total,
        pages=pages
    )

async def create_workflow(db: AsyncSession, *, obj_in: WorkflowCreate) -> Workflow:
    db_obj = Workflow(**obj_in.model_dump()) 
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    # await db.refresh(db_obj, attribute_names=['tasks'])
    return db_obj

async def update_workflow(
    db: AsyncSession, *,
    db_obj: Workflow,
    obj_in: WorkflowUpdate,
    redis_client: Redis | None = None
) -> Workflow:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await db.refresh(db_obj, attribute_names=['tasks'])

    # --- Invalidate Cache ---
    if redis_client:
        cache_key = workflow_cache_key(db_obj.id)
        try:
            await redis_client.delete(cache_key)
            print(f"Invalidated cache for key {cache_key}")
        except Exception as e:
            print(f"Redis DELETE error for key {cache_key}: {e}")
    # --- End Invalidation ---

    return db_obj

async def delete_workflow(
    db: AsyncSession, *,
    workflow_id: int,
    redis_client: Redis | None = None 
) -> Optional[Workflow]:
    db_obj = await get_workflow(db, workflow_id, redis_client=None) 
    if db_obj:
        await db.delete(db_obj)
        await db.commit()

        # --- Invalidate Cache ---
        if redis_client:
            cache_key = workflow_cache_key(workflow_id)
            try:
                await redis_client.delete(cache_key)
                print(f"Invalidated cache for key {cache_key}")
            except Exception as e:
                print(f"Redis DELETE error for key {cache_key}: {e}")
        # --- End Invalidation ---

        return db_obj
    return None
