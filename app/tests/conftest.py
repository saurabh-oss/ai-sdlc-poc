"""
conftest.py - Shared pytest fixtures for the test suite.
"""

import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add app/src to path so all modules are importable by Jenkins and locally
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from main import app, _tasks  # noqa: E402


@pytest.fixture(autouse=True)
def clear_task_store():
    """Reset the in-memory task store before each test for isolation."""
    _tasks.clear()
    import main
    main._next_id = 1
    yield
    _tasks.clear()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_task(client: TestClient) -> dict:
    """Create and return a sample task for use in tests."""
    response = client.post("/api/v1/tasks", json={
        "title": "Sample Task",
        "description": "A task for testing",
        "priority": "medium"
    })
    assert response.status_code == 201
    return response.json()
