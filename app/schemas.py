# app/schemas.py
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from . import models  # import the Enum so TaskOut can accept it

# Requests should only allow these exact strings:
StatusLiteral = Literal["New", "In Progress", "Completed"]

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    status: StatusLiteral = "New"

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[StatusLiteral] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    # Accept Enum from the ORM, but serialize to its string value automatically
    status: models.TaskStatus
    user_id: int

    # Accept attributes from SQLAlchemy models and render Enum as its .value
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class PaginatedTasks(BaseModel):
    items: list[TaskOut]  # the actual tasks on this page
    total: int            # total number of tasks in DB
    page: int             # current page number
    limit: int            # how many per page
