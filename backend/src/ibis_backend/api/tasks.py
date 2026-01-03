"""Task endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ibis_backend.dependencies import get_current_user
from ibis_backend.db import get_db
from ibis_backend.models import Note, Task, User, utcnow
from ibis_backend.note_versions import upsert_note_version
from ibis_backend.schemas import TaskRead, TaskUpdate
from ibis_backend.task_sync import apply_task_completion, sync_tasks_for_note

router = APIRouter()


def task_to_read(task: Task) -> TaskRead:
    """Convert a Task ORM model to a response schema.

    Args:
        task: Task ORM instance.

    Returns:
        TaskRead: Serialized task.
    """

    return TaskRead(
        id=task.id,
        note_id=task.note_id,
        note_title=task.note.title if task.note else "",
        text=task.text,
        completed=task.completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("", response_model=list[TaskRead])
def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskRead]:
    """List tasks for the current user."""

    tasks = (
        db.query(Task)
        .join(Note, Task.note_id == Note.id)
        .filter(Note.user_id == current_user.id)
        .filter(Note.archived.is_(False))
        .order_by(Task.created_at.asc())
        .all()
    )
    return [task_to_read(task) for task in tasks]


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskRead:
    """Update a task completion state."""

    task = (
        db.query(Task)
        .join(Note, Task.note_id == Note.id)
        .filter(Task.id == task_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.completed is None:
        return task_to_read(task)

    note = task.note
    if not note:
        raise HTTPException(status_code=404, detail="Task note not found")

    updated = apply_task_completion(note, task, payload.completed)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to locate task in note.",
        )

    note.updated_at = utcnow()
    task.completed = payload.completed
    task.updated_at = utcnow()

    upsert_note_version(note, db)
    sync_tasks_for_note(note, db)
    db.commit()
    db.refresh(task)

    return task_to_read(task)
