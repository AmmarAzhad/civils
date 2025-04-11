# tests/test_task_service.py

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import task_service
from app.models.task import Task as TaskModel
from app.schemas.task import TaskCreate, TaskUpdate, TaskCreateNested
from app.models.enums import StatusEnum, ExecutionTypeEnum

from datetime import datetime
from typing import List

@pytest.fixture
def mock_db_session():
    """Provides a mocked AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock() 
    session.add = MagicMock()     
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session

def create_mock_task(
    id: int,
    workflow_id: int,
    name: str = "Test Task",
    status: StatusEnum = StatusEnum.PENDING,
    sequence: int = 1,
    **kwargs
) -> TaskModel:
    return TaskModel(
        id=id,
        workflow_id=workflow_id,
        name=name,
        description=kwargs.get("description"),
        status=status,
        sequence=sequence,
        config=kwargs.get("config"),
        created_at=kwargs.get("created_at", datetime.now()),
        updated_at=kwargs.get("updated_at")
    )


@pytest.mark.asyncio
async def test_get_task_found(mock_db_session: AsyncMock):
    """Test retrieving an existing task by ID."""
    task_id = 10
    workflow_id = 1
    mock_task_orm = create_mock_task(id=task_id, workflow_id=workflow_id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_task_orm
    mock_db_session.execute.return_value = mock_result

    result = await task_service.get_task(mock_db_session, task_id=task_id)

    assert result is not None
    assert result.id == task_id
    assert result.workflow_id == workflow_id

    mock_db_session.execute.assert_called_once()
    call_args = mock_db_session.execute.call_args[0][0]
    assert str(call_args).startswith("SELECT tasks.id")
    assert task_id in call_args.compile().params.values()

@pytest.mark.asyncio
async def test_get_task_not_found(mock_db_session: AsyncMock):
    """Test retrieving a non-existent task by ID."""
    task_id = 999

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    result = await task_service.get_task(mock_db_session, task_id=task_id)

    assert result is None
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_tasks_by_workflow_found(mock_db_session: AsyncMock):
    """Test retrieving tasks for a specific workflow."""
    workflow_id = 5
    skip = 0
    limit = 10
    mock_task1 = create_mock_task(id=1, workflow_id=workflow_id, sequence=1)
    mock_task2 = create_mock_task(id=2, workflow_id=workflow_id, sequence=2)
    mock_tasks_orm: List[TaskModel] = [mock_task1, mock_task2]

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_tasks_orm
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    result = await task_service.get_tasks_by_workflow(
        mock_db_session, workflow_id=workflow_id, skip=skip, limit=limit
    )

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].id == 1
    assert result[1].id == 2
    assert all(t.workflow_id == workflow_id for t in result)

    mock_db_session.execute.assert_called_once()
    call_args = mock_db_session.execute.call_args[0][0]
    compiled_query = call_args.compile(compile_kwargs={"literal_binds": True})
    assert str(compiled_query).startswith("SELECT tasks.id")
    assert f"tasks.workflow_id = {workflow_id}" in str(compiled_query)
    assert "ORDER BY tasks.sequence" in str(compiled_query)
    assert f"LIMIT {limit}" in str(compiled_query)
    assert f"OFFSET {skip}" in str(compiled_query)


@pytest.mark.asyncio
async def test_get_tasks_by_workflow_empty(mock_db_session: AsyncMock):
    """Test retrieving tasks when none exist for the workflow."""
    workflow_id = 6
    skip = 0
    limit = 10
    mock_tasks_orm: List[TaskModel] = []

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_tasks_orm
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    result = await task_service.get_tasks_by_workflow(
        mock_db_session, workflow_id=workflow_id, skip=skip, limit=limit
    )

    assert isinstance(result, list)
    assert len(result) == 0
    mock_db_session.execute.assert_called_once()

# --- Test create_task ---

@pytest.mark.asyncio
async def test_create_task(mock_db_session: AsyncMock):
    """Test creating a task using TaskCreate schema."""
    workflow_id = 7
    task_data = TaskCreate(
        name="Standalone Task",
        execution_type=ExecutionTypeEnum.SYNC,
        description="Created via TaskCreate",
        sequence=5,
        workflow_id=workflow_id,
        config={"key": "value"}
    )

    async def mock_refresh(obj, attribute_names=None):
        obj.id = 101 # Simulate DB assigning ID
        obj.created_at = datetime.now()
        obj.status = StatusEnum.PENDING # Simulate default
        return None

    mock_db_session.refresh.side_effect = mock_refresh

    created_task = await task_service.create_task(mock_db_session, obj_in=task_data)

    mock_db_session.add.assert_called_once()
    added_obj = mock_db_session.add.call_args[0][0]
    assert isinstance(added_obj, TaskModel)
    assert added_obj.name == task_data.name
    assert added_obj.description == task_data.description
    assert added_obj.sequence == task_data.sequence
    assert added_obj.workflow_id == task_data.workflow_id
    assert added_obj.config == task_data.config

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(added_obj)

    assert created_task is added_obj
    assert created_task.id == 101
    assert created_task.status == StatusEnum.PENDING

@pytest.mark.asyncio
async def test_create_workflow_task(mock_db_session: AsyncMock):
    """Test creating a task using TaskCreateNested schema and workflow_id argument."""
    workflow_id = 8
    task_data = TaskCreateNested(
        name="Nested Task",
        execution_type=ExecutionTypeEnum.SYNC,
        description="Created via TaskCreateNested",
        sequence=10,
        config={"nested": True}
    )

    async def mock_refresh(obj, attribute_names=None):
        obj.id = 102 # Simulate DB assigning ID
        obj.created_at = datetime.now()
        obj.status = StatusEnum.PENDING
        return None

    mock_db_session.refresh.side_effect = mock_refresh

    created_task = await task_service.create_workflow_task(
        mock_db_session, obj_in=task_data, workflow_id=workflow_id
    )

    mock_db_session.add.assert_called_once()
    added_obj = mock_db_session.add.call_args[0][0]
    assert isinstance(added_obj, TaskModel)
    assert added_obj.name == task_data.name
    assert added_obj.description == task_data.description
    assert added_obj.sequence == task_data.sequence
    assert added_obj.config == task_data.config
    assert added_obj.workflow_id == workflow_id # Verify workflow_id from arg is used

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(added_obj)

    assert created_task is added_obj
    assert created_task.id == 102
    assert created_task.status == StatusEnum.PENDING

@pytest.mark.asyncio
async def test_update_task(mock_db_session: AsyncMock):
    """Test updating an existing task."""
    task_id = 20
    workflow_id = 9
    existing_task = create_mock_task(
        id=task_id,
        workflow_id=workflow_id,
        name="Original Task Name",
        description="Original Desc",
        status=StatusEnum.PENDING,
        sequence=1
    )

    update_data = TaskUpdate(
        name="Updated Task Name",
        status=StatusEnum.RUNNING,
        config={"new_key": "new_value"}
        # description and sequence not set, should not be updated
    )

    async def mock_refresh(obj, attribute_names=None):
        obj.updated_at = datetime.now() # Simulate DB update timestamp
        return None

    mock_db_session.refresh.side_effect = mock_refresh

    updated_task = await task_service.update_task(
        db=mock_db_session, db_obj=existing_task, obj_in=update_data
    )

    assert existing_task.name == "Updated Task Name"
    assert existing_task.status == StatusEnum.RUNNING
    assert existing_task.config == {"new_key": "new_value"}
    assert existing_task.description == "Original Desc" # Unchanged
    assert existing_task.sequence == 1 # Unchanged

    mock_db_session.add.assert_called_once_with(existing_task)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(existing_task)

    assert updated_task is existing_task
    assert updated_task.name == "Updated Task Name"
    assert hasattr(updated_task, 'updated_at') # Check timestamp added


@pytest.mark.asyncio
async def test_update_task_no_changes(mock_db_session: AsyncMock):
    """Test updating a task with no changes in the input schema."""
    task_id = 21
    workflow_id = 9
    existing_task = create_mock_task(
        id=task_id,
        workflow_id=workflow_id,
        name="No Change Task",
        status=StatusEnum.COMPLETED,
    )
    update_data = TaskUpdate() # All fields None (unset)

    original_name = existing_task.name
    original_status = existing_task.status

    updated_task = await task_service.update_task(
        db=mock_db_session, db_obj=existing_task, obj_in=update_data
    )

    assert existing_task.name == original_name # Unchanged
    assert existing_task.status == original_status # Unchanged

    mock_db_session.add.assert_called_once_with(existing_task)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(existing_task)

    assert updated_task is existing_task


@patch('app.services.task_service.get_task', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_delete_task_found(mock_get_task: AsyncMock, mock_db_session: AsyncMock):
    """Test deleting an existing task."""
    task_id = 30
    workflow_id = 10
    mock_task_to_delete = create_mock_task(id=task_id, workflow_id=workflow_id, name="To Delete")
    mock_get_task.return_value = mock_task_to_delete

    deleted_task = await task_service.delete_task(mock_db_session, task_id=task_id)

    mock_get_task.assert_called_once_with(mock_db_session, task_id)
    mock_db_session.delete.assert_called_once_with(mock_task_to_delete)
    mock_db_session.commit.assert_called_once()
    assert deleted_task is mock_task_to_delete # Return the deleted object

@patch('app.services.task_service.get_task', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_delete_task_not_found(mock_get_task: AsyncMock, mock_db_session: AsyncMock):
    """Test deleting a non-existent task."""
    task_id = 999
    mock_get_task.return_value = None # Simulate task not found

    deleted_task = await task_service.delete_task(mock_db_session, task_id=task_id)

    mock_get_task.assert_called_once_with(mock_db_session, task_id)
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()
    assert deleted_task is None # Return None