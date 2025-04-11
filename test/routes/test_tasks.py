# tests/test_tasks_api.py

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app import schemas 
from app.models.enums import StatusEnum 

from .test_workflows import create_test_workflow 

async def create_test_task(client: AsyncClient, workflow_id: int, name: str, sequence: int = 0) -> schemas.Task:
    """Helper to create a task via API under a specific workflow."""
    response = await client.post(
        f"/workflows/{workflow_id}/tasks/",
        json={"name": name, "sequence": sequence, "execution_type": "sync"}
    )
    assert response.status_code == 201
    return schemas.Task(**response.json())

@pytest.mark.asyncio
async def test_read_task_found(client: AsyncClient):
    """Test reading a specific task that exists."""
    workflow = await create_test_workflow(client, "WF for Standalone Task Read")
    task = await create_test_task(client, workflow.id, "Standalone Task Read")

    response = await client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["name"] == task.name
    assert data["workflow_id"] == workflow.id

@pytest.mark.asyncio
async def test_read_task_not_found(client: AsyncClient):
    """Test reading a specific task that does not exist."""
    response = await client.get("/tasks/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

@pytest.mark.asyncio
async def test_update_task(client: AsyncClient):
    """Test updating an existing task."""
    workflow = await create_test_workflow(client, "WF for Task Update")
    task = await create_test_task(client, workflow.id, "Task To Update")
    update_data = {
        "name": "Task Updated Name",
        "status": StatusEnum.COMPLETED.value,
        "sequence": 100
    }

    response = await client.put(f"/tasks/{task.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["name"] == update_data["name"]
    assert data["status"] == update_data["status"]
    assert data["sequence"] == update_data["sequence"]
    assert "updated_at" in data
    assert data["updated_at"] != data["created_at"]

    # Verify persistence
    response_get = await client.get(f"/tasks/{task.id}")
    assert response_get.status_code == 200
    assert response_get.json()["name"] == update_data["name"]
    assert response_get.json()["status"] == update_data["status"]

@pytest.mark.asyncio
async def test_update_task_not_found(client: AsyncClient):
    """Test updating a task that does not exist."""
    update_data = {"name": "Cannot Update Task"}
    response = await client.put("/tasks/99999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient):
    """Test deleting an existing task."""
    workflow = await create_test_workflow(client, "WF for Task Delete")
    task = await create_test_task(client, workflow.id, "Task To Delete")

    response = await client.delete(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["name"] == task.name

    response_get = await client.get(f"/tasks/{task.id}")
    assert response_get.status_code == 404

    response_wf_get = await client.get(f"/workflows/{workflow.id}")
    assert response_wf_get.status_code == 200

@pytest.mark.asyncio
async def test_delete_task_not_found(client: AsyncClient):
    """Test deleting a task that does not exist."""
    response = await client.delete("/tasks/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"