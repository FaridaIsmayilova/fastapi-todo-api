# app/routes/tasks.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas
from .auth import get_current_user  # ⬅️ JWT auth dependency

router = APIRouter(prefix="/tasks", tags=["tasks"])


# 1) List all tasks (optional status filter + pagination)
@router.get(
    "/",
    response_model=schemas.PaginatedTasks,
    summary="List tasks",
    description=(
        "Return a paginated list of all tasks. Requires **Bearer** token (use the "
        "**Authorize** button in Swagger).\n\n"
        "• **Filter**: `status` ∈ {\"New\", \"In Progress\", \"Completed\"}\n"
        "• **Pagination**: `page` (≥1), `limit` (1..100)"
    ),
)
def list_tasks(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),  # ⬅️ enforce auth
    status_filter: Optional[schemas.StatusLiteral] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(models.Task)
    if status_filter:
        stmt = stmt.where(models.Task.status == models.TaskStatus(status_filter))  # cast for safety

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.execute(
        stmt.order_by(models.Task.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
    ).scalars().all()

    return schemas.PaginatedTasks(items=items, total=total, page=page, limit=limit)


# 2) List only current user's tasks
@router.get(
    "/mine",
    response_model=schemas.PaginatedTasks,
    summary="List my tasks",
    description=(
        "Return a paginated list of tasks owned by the current user. Requires **Bearer** token.\n\n"
        "• **Filter**: `status` ∈ {\"New\", \"In Progress\", \"Completed\"}\n"
        "• **Pagination**: `page` (≥1), `limit` (1..100)"
    ),
)
def list_my_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    status_filter: Optional[schemas.StatusLiteral] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(models.Task).where(models.Task.user_id == current_user.id)
    if status_filter:
        stmt = stmt.where(models.Task.status == models.TaskStatus(status_filter))  # cast

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.execute(
        stmt.order_by(models.Task.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
    ).scalars().all()

    return schemas.PaginatedTasks(items=items, total=total, page=page, limit=limit)


# 3) Get a specific task
@router.get("/{task_id}", response_model=schemas.TaskOut, summary="Get a task by ID")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),  # ⬅️ protected
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# 4) Create a new task
@router.post(
    "/",
    response_model=schemas.TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description="Create a new task for the current user. Requires **Bearer** token.",
)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        task = models.Task(
            title=payload.title,
            description=payload.description,
            status=models.TaskStatus(payload.status),  # cast string -> Enum
            user_id=current_user.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {e}")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Integrity error (likely invalid user_id / FK). Make sure the user exists.",
        )


# 4b) Mark a task as completed (owner-only, idempotent)
@router.patch(
    "/{task_id}/complete",
    response_model=schemas.TaskOut,
    summary="Mark as completed (owner-only)",
    description=(
        "Set the task `status` to **Completed**. Owner-only and idempotent. Requires **Bearer** token.\n\n"
        "• **404** if task not found\n"
        "• **403** if you are not the owner"
    ),
)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    if task.status != models.TaskStatus.COMPLETED:
        task.status = models.TaskStatus.COMPLETED
        db.commit()
        db.refresh(task)

    return task


# 5) Update an existing task (owner-only)
@router.patch("/{task_id}", response_model=schemas.TaskOut, summary="Update a task (owner-only)")
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        try:
            data["status"] = models.TaskStatus(data["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


# 6) Delete a task (owner-only)
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task (owner-only)",
    description="Delete a task permanently if you are the owner. Requires **Bearer** token.",
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    db.delete(task)
    db.commit()
    return None
