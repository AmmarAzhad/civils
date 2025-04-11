import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.services import workflow_service
from app.models.workflow import Workflow as WorkflowModel
from app.models.task import Task as TaskModel
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.pagination import Page
from app.models.enums import StatusEnum 

from datetime import datetime

@pytest.fixture
def mock_db_session():
    """Provides a mocked AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_get_workflow_found(mock_db_session: AsyncMock):
    """Test retrieving an existing workflow by ID."""
    workflow_id = 1
    mock_workflow_orm = WorkflowModel(
        id=workflow_id,
        name="Test Workflow",
        description="A test workflow",
        status=StatusEnum.PENDING,
        created_at=datetime.now(),
        tasks=[]
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_workflow_orm
    mock_db_session.execute.return_value = mock_result

    result = await workflow_service.get_workflow(mock_db_session, workflow_id=workflow_id)

    assert result is not None
    assert result.id == workflow_id
    assert result.name == "Test Workflow"
    assert result.tasks == [] 

    mock_db_session.execute.assert_called_once()

    call_args = mock_db_session.execute.call_args[0][0] 
    assert str(call_args).startswith("SELECT workflows.id") 
    assert workflow_id in call_args.compile().params.values()
    assert "tasks" in str(call_args.compile()) 

@pytest.mark.asyncio
async def test_get_workflow_not_found(mock_db_session: AsyncMock):
    """Test retrieving a non-existent workflow by ID."""
    workflow_id = 999

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    result = await workflow_service.get_workflow(mock_db_session, workflow_id=workflow_id)

    assert result is None
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_workflows_basic(mock_db_session: AsyncMock):
    """Test retrieving a paginated list of workflows."""
    skip = 0
    limit = 2
    total_count = 5

    mock_workflow_1 = WorkflowModel(id=1, name="WF 1", status=StatusEnum.PENDING, created_at=datetime.now(), tasks=[])
    mock_workflow_2 = WorkflowModel(id=2, name="WF 2", status=StatusEnum.COMPLETED, created_at=datetime.now(), tasks=[])
    mock_items = [mock_workflow_1, mock_workflow_2]

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = total_count

    mock_items_result = MagicMock()
    mock_items_scalars = MagicMock()
    mock_items_scalars.all.return_value = mock_items
    mock_items_result.scalars.return_value = mock_items_scalars 

    mock_db_session.execute.side_effect = [
        mock_count_result,  
        mock_items_result   
    ]

    result_page = await workflow_service.get_workflows(mock_db_session, skip=skip, limit=limit)

    assert isinstance(result_page, Page)
    assert len(result_page.items) == 2
    assert result_page.items[0].id == 1 
    assert result_page.items[1].id == 2
    assert result_page.page == 1 
    assert result_page.size == limit
    assert result_page.total == total_count
    assert result_page.pages == 3 

    assert mock_db_session.execute.call_count == 2

    count_call_args = mock_db_session.execute.call_args_list[0][0][0]
    assert "count(workflows.id)" in str(count_call_args.compile()).lower()

    items_call_args = mock_db_session.execute.call_args_list[1][0][0]
    compiled_items_query = items_call_args.compile(compile_kwargs={"literal_binds": True}) 
    assert f"LIMIT {limit}" in str(compiled_items_query)
    assert f"OFFSET {skip}" in str(compiled_items_query)
    assert "ORDER BY workflows.id" in str(compiled_items_query)
    assert "tasks" in str(compiled_items_query) 

@pytest.mark.asyncio
async def test_get_workflows_empty(mock_db_session: AsyncMock):
    """Test retrieving workflows when there are none."""
    skip = 0
    limit = 10
    total_count = 0
    mock_items = []

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = total_count

    mock_items_result = MagicMock()
    mock_items_scalars = MagicMock()
    mock_items_scalars.all.return_value = mock_items
    mock_items_result.scalars.return_value = mock_items_scalars

    mock_db_session.execute.side_effect = [mock_count_result, mock_items_result]

    result_page = await workflow_service.get_workflows(mock_db_session, skip=skip, limit=limit)

    assert isinstance(result_page, Page)
    assert len(result_page.items) == 0
    assert result_page.page == 1
    assert result_page.size == limit
    assert result_page.total == 0
    assert result_page.pages == 0 

    assert mock_db_session.execute.call_count == 2

@pytest.mark.asyncio
async def test_get_workflows_invalid_pagination(mock_db_session: AsyncMock):
    """Test if invalid skip/limit are corrected."""
    skip = -5
    limit = 0
    corrected_skip = 0
    corrected_limit = 100 
    total_count = 10

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = total_count
    mock_items_result = MagicMock()
    mock_items_scalars = MagicMock()
    mock_items_scalars.all.return_value = [] 
    mock_items_result.scalars.return_value = mock_items_scalars

    mock_db_session.execute.side_effect = [mock_count_result, mock_items_result]

    await workflow_service.get_workflows(mock_db_session, skip=skip, limit=limit)

    items_call_args = mock_db_session.execute.call_args_list[1][0][0]
    compiled_items_query = items_call_args.compile(compile_kwargs={"literal_binds": True})
    assert f"LIMIT {corrected_limit}" in str(compiled_items_query)
    assert f"OFFSET {corrected_skip}" in str(compiled_items_query)


@pytest.mark.asyncio
async def test_create_workflow(mock_db_session: AsyncMock):
    """Test creating a new workflow."""
    workflow_data = WorkflowCreate(
        name="New Workflow",
        description="Description for new workflow"
    )

    async def mock_refresh(obj, attribute_names=None):
        obj.id = 123 
        obj.created_at = datetime.now()
        obj.status = StatusEnum.PENDING 
        obj.tasks = [] 
        return None

    mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)
    mock_db_session.commit = AsyncMock()
    mock_db_session.add = MagicMock() 

    created_workflow = await workflow_service.create_workflow(mock_db_session, obj_in=workflow_data)

    mock_db_session.add.assert_called_once()
    added_obj = mock_db_session.add.call_args[0][0] 
    assert isinstance(added_obj, WorkflowModel)
    assert added_obj.name == workflow_data.name
    assert added_obj.description == workflow_data.description

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(added_obj) 

    assert created_workflow is added_obj 
    assert created_workflow.id == 123
    assert created_workflow.status == StatusEnum.PENDING
    assert created_workflow.name == workflow_data.name


@pytest.mark.asyncio
async def test_update_workflow(mock_db_session: AsyncMock):
    """Test updating an existing workflow."""
    existing_workflow_id = 1
    existing_workflow = WorkflowModel(
        id=existing_workflow_id,
        name="Original Name",
        description="Original Desc",
        status=StatusEnum.PENDING,
        created_at=datetime.now(),
        tasks=[]
    )

    update_data = WorkflowUpdate(
        name="Updated Name",
        status=StatusEnum.RUNNING

    )

    async def mock_refresh(obj, attribute_names=None):
        if attribute_names and 'tasks' in attribute_names:
            if not hasattr(obj, 'tasks'):
                 obj.tasks = [] 
        obj.updated_at = datetime.now() 
        return None

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)
    mock_db_session.add = MagicMock() 

    updated_workflow = await workflow_service.update_workflow(
        db=mock_db_session, db_obj=existing_workflow, obj_in=update_data
    )

    assert existing_workflow.name == "Updated Name"
    assert existing_workflow.status == StatusEnum.RUNNING
    assert existing_workflow.description == "Original Desc" 

    mock_db_session.add.assert_called_once_with(existing_workflow)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_has_calls([
        call(existing_workflow), 
        call(existing_workflow, attribute_names=['tasks']) 
    ], any_order=False) 

    assert updated_workflow is existing_workflow
    assert updated_workflow.name == "Updated Name"
    assert updated_workflow.status == StatusEnum.RUNNING
    assert hasattr(updated_workflow, 'updated_at') 
    assert hasattr(updated_workflow, 'tasks') 

@pytest.mark.asyncio
async def test_update_workflow_no_changes(mock_db_session: AsyncMock):
    """Test update when input schema has no fields set."""
    existing_workflow = WorkflowModel(
        id=2, name="No Change", status=StatusEnum.PENDING, created_at=datetime.now(), tasks=[]
    )
    update_data = WorkflowUpdate() 

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    mock_db_session.add = MagicMock()

    original_name = existing_workflow.name 

    updated_workflow = await workflow_service.update_workflow(
        db=mock_db_session, db_obj=existing_workflow, obj_in=update_data
    )

    assert existing_workflow.name == original_name

    mock_db_session.add.assert_called_once_with(existing_workflow)
    mock_db_session.commit.assert_called_once()
    assert mock_db_session.refresh.call_count == 2

    assert updated_workflow is existing_workflow

@patch('app.services.workflow_service.get_workflow', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_delete_workflow_found(mock_get_workflow: AsyncMock, mock_db_session: AsyncMock):
    """Test deleting an existing workflow."""
    workflow_id = 5
    mock_workflow_to_delete = WorkflowModel(id=workflow_id, name="To Delete")
    mock_get_workflow.return_value = mock_workflow_to_delete

    mock_db_session.delete = AsyncMock()
    mock_db_session.commit = AsyncMock()

    deleted_workflow = await workflow_service.delete_workflow(mock_db_session, workflow_id=workflow_id)

    mock_get_workflow.assert_called_once_with(mock_db_session, workflow_id)
    mock_db_session.delete.assert_called_once_with(mock_workflow_to_delete)
    mock_db_session.commit.assert_called_once()
    assert deleted_workflow is mock_workflow_to_delete 

@patch('app.services.workflow_service.get_workflow', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_delete_workflow_not_found(mock_get_workflow: AsyncMock, mock_db_session: AsyncMock):
    """Test deleting a non-existent workflow."""
    workflow_id = 999
    mock_get_workflow.return_value = None

    mock_db_session.delete = AsyncMock()
    mock_db_session.commit = AsyncMock()

    deleted_workflow = await workflow_service.delete_workflow(mock_db_session, workflow_id=workflow_id)

    mock_get_workflow.assert_called_once_with(mock_db_session, workflow_id)
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()
    assert deleted_workflow is None 