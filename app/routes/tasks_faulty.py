# app/routes/tasks.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models_faulty, schemas_faulty

router = APIRouter(prefix="/tasks", tags=["tasks"])


# TEMP auth via header until JWT
def get_current_user_id(
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id")
) -> int:
    if x_user_id is None:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return x_user_id


# 1) List all tasks (optional status filter + pagination)
@router.get("/", response_model=schemas_faulty.PaginatedTasks)
def list_tasks(
    db: Session = Depends(get_db),
    status_filter: Optional[schemas_faulty.StatusLiteral] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(models_faulty.Task)
    if status_filter is not None:
        try:
            status_enum = models_faulty.TaskStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        stmt = stmt.where(models_faulty.Task.status == status_enum)

    # COUNT safely (remove ORDER BY from the subquery)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total: int = db.execute(count_stmt).scalar_one()

    result = db.execute(
        stmt.order_by(models_faulty.Task.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
    )
    # ✅ Recommended option: force a real list for Pylance
    rows: list[models_faulty.Task] = list(result.scalars().all())

    # Convert ORM -> Pydantic to satisfy type checker
    items: list[schemas_faulty.TaskOut] = [schemas_faulty.TaskOut.model_validate(r) for r in rows]

    return schemas_faulty.PaginatedTasks(items=items, total=total, page=page, limit=limit)


# 2) List only current user's tasks
@router.get("/mine", response_model=schemas_faulty.PaginatedTasks)
def list_my_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    status_filter: Optional[schemas_faulty.StatusLiteral] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(models_faulty.Task).where(models_faulty.Task.user_id == user_id)
    if status_filter is not None:
        try:
            status_enum = models_faulty.TaskStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        stmt = stmt.where(models_faulty.Task.status == status_enum)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total: int = db.execute(count_stmt).scalar_one()

    result = db.execute(
        stmt.order_by(models_faulty.Task.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
    )
    # ✅ Recommended option: force a real list for Pylance
    rows: list[models_faulty.Task] = list(result.scalars().all())
    items: list[schemas_faulty.TaskOut] = [schemas_faulty.TaskOut.model_validate(r) for r in rows]

    return schemas_faulty.PaginatedTasks(items=items, total=total, page=page, limit=limit)


# 3) Get a specific task
@router.get("/{task_id}", response_model=schemas_faulty.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models_faulty.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return schemas_faulty.TaskOut.model_validate(task)


# 4) Create a new task
@router.post("/", response_model=schemas_faulty.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas_faulty.TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        task = models_faulty.Task(
            title=payload.title,
            description=payload.description,
            status=models_faulty.TaskStatus(payload.status),  # cast string -> Enum
            user_id=user_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return schemas_faulty.TaskOut.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {e}")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Integrity error (likely invalid user_id / FK). Make sure the user exists.",
        )


# 5) Update an existing task (owner-only)
@router.patch("/{task_id}", response_model=schemas_faulty.TaskOut)
def update_task(
    task_id: int,
    payload: schemas_faulty.TaskUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = db.get(models_faulty.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        try:
            data["status"] = models_faulty.TaskStatus(data["status"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid status: {e}")

    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return schemas_faulty.TaskOut.model_validate(task)


# 6) Delete a task (owner-only)
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = db.get(models_faulty.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this task")

    db.delete(task)
    db.commit()
    return None

