# AI-ASSIST-METADATA:
#   tool: claude-code
#   model: claude-sonnet-4
#   developer: dev1
#   date: 2025-01-01
#   human-review: approved
#   ai-contribution-estimate: 70%

"""
Sample FastAPI Application - Task Management Service
=====================================================
A simple but well-structured FastAPI app demonstrating
proper patterns for the AI-SDLC POC.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.auth import router as auth_router

# -- Logging Setup ---------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -- Lifespan --------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Task Service starting up")
    yield
    logger.info("Task Service shutting down")


# -- App Init --------------------------------------------------
app = FastAPI(
    title="Task Management Service",
    description="AI-SDLC POC - Sample Application",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# -- Models ----------------------------------------------------
class TaskCreate(BaseModel):
    """Request model for creating a new task."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    assignee_id: Optional[int] = Field(None, gt=0)


class TaskUpdate(BaseModel):
    """Request model for updating an existing task."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, pattern="^(open|in_progress|done|cancelled)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")


class Task(BaseModel):
    """Task response model."""

    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    assignee_id: Optional[int]
    created_at: str
    updated_at: str


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: dict


# -- In-Memory Store (replace with DB in production) -----------
_tasks: dict[int, dict] = {}
_next_id: int = 1


def get_task_store() -> dict[int, dict]:
    """Dependency injection for task store."""
    return _tasks


# -- Routes ----------------------------------------------------
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get(
    "/api/v1/tasks",
    response_model=list[Task],
    summary="List all tasks",
)
async def list_tasks(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    store: dict = Depends(get_task_store),
) -> list[Task]:
    """Retrieve all tasks with optional filtering.

    Args:
        status_filter: Filter by task status
        priority_filter: Filter by priority level
        store: Injected task store

    Returns:
        List of tasks matching the filter criteria
    """
    tasks = list(store.values())

    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    if priority_filter:
        tasks = [t for t in tasks if t["priority"] == priority_filter]

    logger.info(
        "Tasks listed",
        extra={"count": len(tasks), "filters": {"status": status_filter, "priority": priority_filter}},
    )
    return [Task(**t) for t in tasks]


@app.post(
    "/api/v1/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(
    task_data: TaskCreate,
    store: dict = Depends(get_task_store),
) -> Task:
    """Create a new task.

    Args:
        task_data: Task creation payload
        store: Injected task store

    Returns:
        The newly created task
    """
    global _next_id

    now = datetime.utcnow().isoformat()
    new_task = {
        "id": _next_id,
        "title": task_data.title,
        "description": task_data.description,
        "status": "open",
        "priority": task_data.priority,
        "assignee_id": task_data.assignee_id,
        "created_at": now,
        "updated_at": now,
    }

    store[_next_id] = new_task
    _next_id += 1

    logger.info("Task created", extra={"task_id": new_task["id"], "title": new_task["title"]})
    return Task(**new_task)


@app.get(
    "/api/v1/tasks/{task_id}",
    response_model=Task,
    summary="Get a task by ID",
)
async def get_task(
    task_id: int,
    store: dict = Depends(get_task_store),
) -> Task:
    """Retrieve a single task by ID.

    Args:
        task_id: The task identifier
        store: Injected task store

    Returns:
        The task if found

    Raises:
        HTTPException: 404 if task not found
    """
    if task_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found"}},
        )
    return Task(**store[task_id])


@app.patch(
    "/api/v1/tasks/{task_id}",
    response_model=Task,
    summary="Update a task",
)
async def update_task(
    task_id: int,
    update_data: TaskUpdate,
    store: dict = Depends(get_task_store),
) -> Task:
    """Partially update an existing task.

    Args:
        task_id: The task identifier
        update_data: Fields to update
        store: Injected task store

    Returns:
        The updated task

    Raises:
        HTTPException: 404 if task not found
    """
    if task_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found"}},
        )

    task = store[task_id].copy()
    update_dict = update_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        task[key] = value
    task["updated_at"] = datetime.utcnow().isoformat()

    store[task_id] = task
    logger.info("Task updated", extra={"task_id": task_id, "fields": list(update_dict.keys())})
    return Task(**task)


@app.delete(
    "/api/v1/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
async def delete_task(
    task_id: int,
    store: dict = Depends(get_task_store),
) -> None:
    """Delete a task.

    Args:
        task_id: The task identifier to delete
        store: Injected task store

    Raises:
        HTTPException: 404 if task not found
    """
    if task_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found"}},
        )

    del store[task_id]
    logger.info("Task deleted", extra={"task_id": task_id})
