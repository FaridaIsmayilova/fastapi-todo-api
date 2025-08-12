# app/models.py
from __future__ import annotations

from enum import Enum
from typing import Type, List

from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TaskStatus(str, Enum):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


# Typed helper so Pylance knows the return type (fixes Unknown in lambda)
def task_status_values(_: Type[TaskStatus]) -> List[str]:
    return [member.value for member in TaskStatus]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # Store human-readable values ("New", "In Progress", "Completed") as VARCHAR
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(
            TaskStatus,
            native_enum=False,                 # store as VARCHAR (no PG enum type)
            values_callable=task_status_values,  # persist .value, not .name
            validate_strings=True,            # reject invalid strings
            name="task_status",               # helpful for migrations
        ),
        default=TaskStatus.NEW,
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="tasks")
