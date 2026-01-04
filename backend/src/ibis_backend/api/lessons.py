"""Lesson endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ibis_backend.api.notes import note_to_read
from ibis_backend.api.videos import video_to_read
from ibis_backend.db import get_db
from ibis_backend.dependencies import get_current_user
from ibis_backend.models import Lesson, LessonNote, LessonVideo, Note, Task, User, Video, utcnow
from ibis_backend.schemas import (
    LessonCreate,
    LessonNoteCreate,
    LessonRead,
    LessonUpdate,
    LessonVideoCreate,
    NoteRead,
    TaskRead,
    VideoRead,
)

router = APIRouter()


def lesson_to_read(lesson: Lesson) -> LessonRead:
    """Convert lesson ORM to schema."""

    return LessonRead(
        id=lesson.id,
        title=lesson.title,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


@router.get("", response_model=list[LessonRead])
def list_lessons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LessonRead]:
    """List lessons for the current user."""

    lessons = (
        db.query(Lesson)
        .filter(Lesson.user_id == current_user.id)
        .order_by(Lesson.created_at.desc())
        .all()
    )
    return [lesson_to_read(lesson) for lesson in lessons]


@router.post("", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonRead:
    """Create a lesson manually."""

    created_at = payload.created_at or utcnow()
    lesson = Lesson(
        title=payload.title,
        created_at=created_at,
        updated_at=created_at,
        user_id=current_user.id,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson_to_read(lesson)


@router.get("/{lesson_id}", response_model=LessonRead)
def get_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonRead:
    """Fetch a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson_to_read(lesson)


@router.patch("/{lesson_id}", response_model=LessonRead)
def update_lesson(
    lesson_id: str,
    payload: LessonUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonRead:
    """Update lesson metadata."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if payload.title is not None:
        lesson.title = payload.title
    lesson.updated_at = utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson_to_read(lesson)


@router.get("/{lesson_id}/notes", response_model=list[NoteRead])
def list_lesson_notes(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteRead]:
    """List notes within a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    notes = (
        db.query(Note)
        .join(LessonNote, LessonNote.note_id == Note.id)
        .filter(LessonNote.lesson_id == lesson_id)
        .order_by(Note.created_at.asc())
        .all()
    )
    return [note_to_read(note) for note in notes]


@router.get("/{lesson_id}/videos", response_model=list[VideoRead])
def list_lesson_videos(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VideoRead]:
    """List videos within a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    videos = (
        db.query(Video)
        .join(LessonVideo, LessonVideo.video_id == Video.id)
        .filter(LessonVideo.lesson_id == lesson_id)
        .order_by(Video.created_at.asc())
        .all()
    )
    return [video_to_read(video) for video in videos]


@router.get("/{lesson_id}/tasks", response_model=list[TaskRead])
def list_lesson_tasks(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskRead]:
    """List tasks for notes in a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    tasks = (
        db.query(Task)
        .join(Note, Task.note_id == Note.id)
        .join(LessonNote, LessonNote.note_id == Note.id)
        .filter(LessonNote.lesson_id == lesson_id)
        .filter(Note.user_id == current_user.id)
        .order_by(Task.created_at.asc())
        .all()
    )
    return [
        TaskRead(
            id=task.id,
            note_id=task.note_id,
            note_title=task.note.title if task.note else "",
            text=task.text,
            completed=task.completed,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@router.post("/{lesson_id}/notes", response_model=LessonRead)
def add_note_to_lesson(
    lesson_id: str,
    payload: LessonNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonRead:
    """Add a note to a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    note = (
        db.query(Note)
        .filter(Note.id == payload.note_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    existing = (
        db.query(LessonNote)
        .filter(LessonNote.lesson_id == lesson_id)
        .filter(LessonNote.note_id == note.id)
        .first()
    )
    if not existing:
        db.add(LessonNote(lesson_id=lesson_id, note_id=note.id, created_at=utcnow()))

    if note.video_id:
        existing_video = (
            db.query(LessonVideo)
            .filter(LessonVideo.lesson_id == lesson_id)
            .filter(LessonVideo.video_id == note.video_id)
            .first()
        )
        if not existing_video:
            db.add(
                LessonVideo(
                    lesson_id=lesson_id, video_id=note.video_id, created_at=utcnow()
                )
            )

    lesson.updated_at = utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson_to_read(lesson)


@router.delete("/{lesson_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_note_from_lesson(
    lesson_id: str,
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Remove a note from a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    db.query(LessonNote).filter(LessonNote.lesson_id == lesson_id).filter(
        LessonNote.note_id == note_id
    ).delete()
    lesson.updated_at = utcnow()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{lesson_id}/videos", response_model=LessonRead)
def add_video_to_lesson(
    lesson_id: str,
    payload: LessonVideoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonRead:
    """Add a video (and its notes) to a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    video = (
        db.query(Video)
        .filter(Video.id == payload.video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    existing = (
        db.query(LessonVideo)
        .filter(LessonVideo.lesson_id == lesson_id)
        .filter(LessonVideo.video_id == video.id)
        .first()
    )
    if not existing:
        db.add(LessonVideo(lesson_id=lesson_id, video_id=video.id, created_at=utcnow()))

    notes = db.query(Note).filter(Note.video_id == video.id).all()
    for note in notes:
        existing_note = (
            db.query(LessonNote)
            .filter(LessonNote.lesson_id == lesson_id)
            .filter(LessonNote.note_id == note.id)
            .first()
        )
        if not existing_note:
            db.add(LessonNote(lesson_id=lesson_id, note_id=note.id, created_at=utcnow()))

    lesson.updated_at = utcnow()
    db.commit()
    db.refresh(lesson)
    return lesson_to_read(lesson)


@router.delete("/{lesson_id}/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_video_from_lesson(
    lesson_id: str,
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Remove a video (and its notes) from a lesson."""

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .filter(Lesson.user_id == current_user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    db.query(LessonVideo).filter(LessonVideo.lesson_id == lesson_id).filter(
        LessonVideo.video_id == video_id
    ).delete()
    db.query(LessonNote).filter(LessonNote.lesson_id == lesson_id).join(
        Note, LessonNote.note_id == Note.id
    ).filter(Note.video_id == video_id).delete(synchronize_session=False)
    lesson.updated_at = utcnow()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notes/{note_id}", response_model=list[LessonRead])
def list_note_lessons(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LessonRead]:
    """List lessons that include a note."""

    note = (
        db.query(Note)
        .filter(Note.id == note_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    lessons = (
        db.query(Lesson)
        .join(LessonNote, LessonNote.lesson_id == Lesson.id)
        .filter(LessonNote.note_id == note_id)
        .order_by(Lesson.created_at.desc())
        .all()
    )
    return [lesson_to_read(lesson) for lesson in lessons]

