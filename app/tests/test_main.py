"""
Unit Tests - Task Management Service
=====================================
Tests for all API endpoints with happy paths, edge cases, and error scenarios.
"""

import pytest
from fastapi.testclient import TestClient

# Add parent to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import app, _tasks, get_task_store


# -- Fixtures -------------------------------------------------
@pytest.fixture(autouse=True)
def clear_task_store():
    """Clear the in-memory store before each test."""
    _tasks.clear()
    import main
    main._next_id = 1
    yield
    _tasks.clear()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_task(client):
    """Create and return a sample task for tests that need existing data."""
    response = client.post("/api/v1/tasks", json={
        "title": "Test Task",
        "description": "A test task",
        "priority": "medium",
    })
    assert response.status_code == 201
    return response.json()


# -- Health Check ----------------------------------------------
class TestHealthCheck:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


# -- Create Task -----------------------------------------------
class TestCreateTask:
    def test_create_task_returns_201(self, client):
        response = client.post("/api/v1/tasks", json={"title": "New Task"})
        assert response.status_code == 201

    def test_create_task_returns_task_data(self, client):
        response = client.post("/api/v1/tasks", json={
            "title": "My Task",
            "description": "Task description",
            "priority": "high",
        })
        data = response.json()
        assert data["title"] == "My Task"
        assert data["description"] == "Task description"
        assert data["priority"] == "high"
        assert data["status"] == "open"
        assert data["id"] == 1

    def test_create_task_with_minimal_data(self, client):
        response = client.post("/api/v1/tasks", json={"title": "Minimal"})
        assert response.status_code == 201
        data = response.json()
        assert data["description"] is None
        assert data["priority"] == "medium"

    def test_create_task_empty_title_fails(self, client):
        response = client.post("/api/v1/tasks", json={"title": ""})
        assert response.status_code == 422

    def test_create_task_invalid_priority_fails(self, client):
        response = client.post("/api/v1/tasks", json={
            "title": "Task", "priority": "urgent"
        })
        assert response.status_code == 422

    @pytest.mark.parametrize("priority", ["low", "medium", "high", "critical"])
    def test_create_task_all_valid_priorities(self, client, priority):
        response = client.post("/api/v1/tasks", json={"title": "Task", "priority": priority})
        assert response.status_code == 201
        assert response.json()["priority"] == priority


# -- List Tasks ------------------------------------------------
class TestListTasks:
    def test_list_empty_returns_empty_list(self, client):
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_all_tasks(self, client):
        client.post("/api/v1/tasks", json={"title": "Task 1"})
        client.post("/api/v1/tasks", json={"title": "Task 2"})
        client.post("/api/v1/tasks", json={"title": "Task 3"})

        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_list_filter_by_priority(self, client):
        client.post("/api/v1/tasks", json={"title": "High Task", "priority": "high"})
        client.post("/api/v1/tasks", json={"title": "Low Task", "priority": "low"})

        response = client.get("/api/v1/tasks?priority_filter=high")
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "High Task"


# -- Get Task --------------------------------------------------
class TestGetTask:
    def test_get_existing_task(self, client, sample_task):
        task_id = sample_task["id"]
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["id"] == task_id

    def test_get_nonexistent_task_returns_404(self, client):
        response = client.get("/api/v1/tasks/9999")
        assert response.status_code == 404

    def test_get_task_404_has_error_structure(self, client):
        response = client.get("/api/v1/tasks/9999")
        data = response.json()
        assert "detail" in data


# -- Update Task -----------------------------------------------
class TestUpdateTask:
    def test_update_task_title(self, client, sample_task):
        task_id = sample_task["id"]
        response = client.patch(f"/api/v1/tasks/{task_id}", json={"title": "Updated Title"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_task_status(self, client, sample_task):
        task_id = sample_task["id"]
        response = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_nonexistent_task_returns_404(self, client):
        response = client.patch("/api/v1/tasks/9999", json={"title": "X"})
        assert response.status_code == 404

    def test_update_preserves_unchanged_fields(self, client, sample_task):
        task_id = sample_task["id"]
        original_description = sample_task["description"]
        client.patch(f"/api/v1/tasks/{task_id}", json={"title": "New Title"})

        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.json()["description"] == original_description


# -- Delete Task -----------------------------------------------
class TestDeleteTask:
    def test_delete_existing_task_returns_204(self, client, sample_task):
        task_id = sample_task["id"]
        response = client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 204

    def test_deleted_task_not_found(self, client, sample_task):
        task_id = sample_task["id"]
        client.delete(f"/api/v1/tasks/{task_id}")
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_task_returns_404(self, client):
        response = client.delete("/api/v1/tasks/9999")
        assert response.status_code == 404
