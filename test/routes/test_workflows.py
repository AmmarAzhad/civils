import pytest
import pytest_asyncio
from httpx import AsyncClient

from app import schemas 
from app.models.enums import StatusEnum 

async def create_test_workflow(client: AsyncClient, name: str, description: str = None) -> schemas.Workflow:
    """Helper to create a workflow via API and return the response schema."""
    response = await client.post(
        "/workflows/",
        json={"name": name, "description": description}
    )
    assert response.status_code == 201
    return schemas.Workflow(**response.json())

@pytest.mark.asyncio
async def test_create_workflow(client: AsyncClient):
    """Test creating a new workflow."""
    workflow_data = {"name": "Test Workflow API", "description": "API creation test"}
    response = await client.post("/workflows/", json=workflow_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == workflow_data["name"]
    assert data["description"] == workflow_data["description"]
    assert data["status"] == StatusEnum.PENDING.value 
    assert "id" in data
    assert "created_at" in data
    assert data["tasks"] == []

@pytest.mark.asyncio
async def test_create_workflow_missing_name(client: AsyncClient):
    """Test creating a workflow with missing required field (name)."""
    response = await client.post("/workflows/", json={"description": "Missing name"})
    assert response.status_code == 422 

@pytest.mark.asyncio
async def test_read_workflows_empty(client: AsyncClient):
    """Test reading workflows when none exist."""
    response = await client.get("/workflows/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 100 
    assert data["pages"] == 0

@pytest.mark.asyncio
async def test_read_workflows_with_data(client: AsyncClient):
    """Test reading workflows with pagination."""
    wf1 = await create_test_workflow(client, "WF Read 1")
    wf2 = await create_test_workflow(client, "WF Read 2")

    response = await client.get("/workflows/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["size"] == 100
    assert data["pages"] == 1
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == wf1.id
    assert data["items"][1]["id"] == wf2.id

    response = await client.get("/workflows/?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["size"] == 1
    assert data["pages"] == 2
    assert data["page"] == 2 
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == wf2.id 

@pytest.mark.asyncio
async def test_read_workflow_found(client: AsyncClient):
    """Test reading a specific workflow that exists."""
    workflow = await create_test_workflow(client, "WF Read Single")
    response = await client.get(f"/workflows/{workflow.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow.id
    assert data["name"] == workflow.name
    assert data["tasks"] == [] 

@pytest.mark.asyncio
async def test_read_workflow_not_found(client: AsyncClient):
    """Test reading a specific workflow that does not exist."""
    response = await client.get("/workflows/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"

@pytest.mark.asyncio
async def test_update_workflow(client: AsyncClient):
    """Test updating an existing workflow."""
    workflow = await create_test_workflow(client, "WF To Update")
    update_data = {"name": "WF Updated Name", "status": StatusEnum.COMPLETED.value}

    response = await client.put(f"/workflows/{workflow.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow.id
    assert data["name"] == update_data["name"]
    assert data["status"] == update_data["status"]
    assert data["description"] == workflow.description 
    assert "updated_at" in data
    assert data["updated_at"] != data["created_at"]

    response_get = await client.get(f"/workflows/{workflow.id}")
    assert response_get.status_code == 200
    assert response_get.json()["name"] == update_data["name"]

@pytest.mark.asyncio
async def test_update_workflow_not_found(client: AsyncClient):
    """Test updating a workflow that does not exist."""
    update_data = {"name": "Cannot Update"}
    response = await client.put("/workflows/99999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"

@pytest.mark.asyncio
async def test_delete_workflow(client: AsyncClient):
    """Test deleting an existing workflow."""
    workflow = await create_test_workflow(client, "WF To Delete")

    response = await client.delete(f"/workflows/{workflow.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow.id
    assert data["name"] == workflow.name

    response_get = await client.get(f"/workflows/{workflow.id}")
    assert response_get.status_code == 404

@pytest.mark.asyncio
async def test_delete_workflow_not_found(client: AsyncClient):
    """Test deleting a workflow that does not exist."""
    response = await client.delete("/workflows/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"


@pytest.mark.asyncio
async def test_create_task_for_workflow(client: AsyncClient):
    """Test creating a task nested under a workflow."""
    workflow = await create_test_workflow(client, "WF with Tasks")
    task_data = {"name": "Nested Task 1", "sequence": 1, "execution_type": "sync"}

    response = await client.post(f"/workflows/{workflow.id}/tasks/", json=task_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == task_data["name"]
    assert data["sequence"] == task_data["sequence"]
    assert data["workflow_id"] == workflow.id
    assert data["status"] == StatusEnum.PENDING.value
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_task_for_workflow_not_found(client: AsyncClient):
    """Test creating a task for a non-existent workflow."""
    task_data = {"name": "Orphan Task", "sequence": 1, "execution_type": "sync"}
    response = await client.post("/workflows/99999/tasks/", json=task_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Parent workflow not found"

@pytest.mark.asyncio
async def test_read_workflow_tasks(client: AsyncClient):
    """Test reading tasks nested under a workflow."""
    workflow = await create_test_workflow(client, "WF Read Tasks")

    task1_resp = await client.post(f"/workflows/{workflow.id}/tasks/", json={"name": "Read Task 1", "sequence": 1, "execution_type": "sync"})
    task2_resp = await client.post(f"/workflows/{workflow.id}/tasks/", json={"name": "Read Task 2", "sequence": 0, "execution_type": "sync"})
    assert task1_resp.status_code == 201
    assert task2_resp.status_code == 201
    task1_id = task1_resp.json()["id"]
    task2_id = task2_resp.json()["id"]

    response = await client.get(f"/workflows/{workflow.id}/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    assert data[0]["id"] == task2_id
    assert data[0]["sequence"] == 0
    assert data[1]["id"] == task1_id
    assert data[1]["sequence"] == 1
    assert all(t["workflow_id"] == workflow.id for t in data)

@pytest.mark.asyncio
async def test_read_workflow_tasks_workflow_not_found(client: AsyncClient):
    """Test reading tasks for a non-existent workflow."""
    response = await client.get("/workflows/99999/tasks/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Parent workflow not found"