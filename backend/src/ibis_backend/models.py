"""ORM models for the Ibis backend."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ibis_backend.db import Base


def utcnow() -> datetime:
    """Return the current UTC time.

    Returns:
        datetime: Current UTC time.
    """

    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Generate a UUID4 string.

    Returns:
        str: UUID4 string.
    """

    return str(uuid.uuid4())


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    lesson_autogroup_hours: Mapped[int] = mapped_column(Integer, default=4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    notes: Mapped[list["Note"]] = relationship(back_populates="user")
    videos: Mapped[list["Video"]] = relationship(back_populates="user")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="user")


class Classroom(Base):
    """Classroom grouping for teachers and students."""

    __tablename__ = "classrooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    """Membership linking users to classrooms with a role."""

    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    classroom_id: Mapped[str] = mapped_column(ForeignKey("classrooms.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Video(Base):
    """Video metadata for notes."""

    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    storage_key: Mapped[Optional[str]] = mapped_column(String(1024))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(255))
    original_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(1024))
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    notes: Mapped[list["Note"]] = relationship(back_populates="video")
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="video")
    user: Mapped[User] = relationship(back_populates="videos")
    lessons: Mapped[list["LessonVideo"]] = relationship(back_populates="video")


class Note(Base):
    """Lesson note document."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    video_id: Mapped[Optional[str]] = mapped_column(ForeignKey("videos.id"))
    video_start_seconds: Mapped[Optional[float]] = mapped_column(Float)
    video_end_seconds: Mapped[Optional[float]] = mapped_column(Float)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    video: Mapped[Optional[Video]] = relationship(back_populates="notes", lazy="joined")
    tasks: Mapped[list["Task"]] = relationship(back_populates="note")
    versions: Mapped[list["NoteVersion"]] = relationship(back_populates="note")
    user: Mapped[User] = relationship(back_populates="notes")
    lessons: Mapped[list["LessonNote"]] = relationship(back_populates="note")


class Lesson(Base):
    """Lesson grouping for notes and videos."""

    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped[User] = relationship(back_populates="lessons")
    lesson_notes: Mapped[list["LessonNote"]] = relationship(back_populates="lesson")
    lesson_videos: Mapped[list["LessonVideo"]] = relationship(back_populates="lesson")


class LessonNote(Base):
    """Join table for lessons and notes."""

    __tablename__ = "lesson_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lesson: Mapped["Lesson"] = relationship(back_populates="lesson_notes")
    note: Mapped[Note] = relationship(back_populates="lessons")


class LessonVideo(Base):
    """Join table for lessons and videos."""

    __tablename__ = "lesson_videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lesson: Mapped["Lesson"] = relationship(back_populates="lesson_videos")
    video: Mapped[Video] = relationship(back_populates="lessons")


class NoteVersion(Base):
    """Historical snapshot of a note."""

    __tablename__ = "note_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    note: Mapped[Note] = relationship(back_populates="versions")


class Task(Base):
    """Checklist task extracted from a note."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False)
    text: Mapped[str] = mapped_column(String, default="", nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurrence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    note: Mapped[Note] = relationship(back_populates="tasks", lazy="joined")


class NoteYjsUpdate(Base):
    """Yjs updates for realtime collaboration."""

    __tablename__ = "note_yjs_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False)
    update: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TranscriptChunk(Base):
    """Transcript chunk for a video."""

    __tablename__ = "transcript_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcessingJob(Base):
    """Background processing job for media."""

    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[Optional[float]] = mapped_column(Float)
    detail: Mapped[Optional[str]] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    video: Mapped[Video] = relationship(back_populates="jobs")
