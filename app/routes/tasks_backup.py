# app/routes/tasks.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas



router = APIRouter(prefix="/tasks", tags=["tasks"])

'''# TEMP auth: read current user id from header until we add JWT
def get_current_user_id(x_user_id: Optional[int] = Header(default=1, alias="X-User-Id")) -> int:
    return x_user_id or 1'''
    
# Strict user dependency for debugging 500 Internal serve rerror
def get_current_user_id(x_user_id: Optional[int] = Header(default=None, alias="X-User-Id")) -> int:
    if x_user_id is None:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return x_user_id

# 1) List all tasks (optional status filter + pagination)
@router.get("/", response_model=schemas.PaginatedTasks)
def list_tasks(
    db: Session = Depends(get_db),
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
@router.get("/mine", response_model=schemas.PaginatedTasks)
def list_my_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    status_filter: Optional[schemas.StatusLiteral] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(models.Task).where(models.Task.user_id == user_id)
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
@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# 4) Create a new task
'''@router.post("/", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = models.Task(
        title=payload.title,
        description=payload.description,
        status=models.TaskStatus(payload.status),  # <<< cast string -> Enum
        user_id=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task'''
# Debugging 500 Error: Internal Server Error
@router.post("/", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        task = models.Task(
            title=payload.title,
            description=payload.description,
            status=models.TaskStatus(payload.status),  # cast string -> Enum
            user_id=user_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    except ValueError as e:
        # Typically: invalid enum value like "Done"
        raise HTTPException(status_code=400, detail=f"Invalid status: {e}")

    except IntegrityError as e:
        db.rollback()
        # Most common: foreign key fails because user_id doesn't exist
        raise HTTPException(status_code=400, detail="Integrity error (likely invalid user_id / FK). Make sure the user exists.")


# 4b) Mark a task as completed (owner-only)
@router.patch("/{task_id}/complete", response_model=schemas.TaskOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    # Only update if not already completed (idempotent)
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
    user_id: int = Depends(get_current_user_id),
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    data = payload.model_dump(exclude_unset=True)  # Pydantic v2
    if "status" in data and data["status"] is not None:
        data["status"] = models.TaskStatus(data["status"])  # cast

    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task'''


# 6) Delete a task (owner-only)
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    db.delete(task)
    db.commit()
    return None

