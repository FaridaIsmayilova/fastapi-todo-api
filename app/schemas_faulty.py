# app/schemas.py
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

# Public strings your API exposes
StatusLiteral = Literal["New", "In Progress", "Completed"]

class TaskOut(BaseModel):
    # Needed so Pydantic can read SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    status: StatusLiteral
    user_id: int

class PaginatedTasks(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    limit: int

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: StatusLiteral = "New"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StatusLiteral] = None
