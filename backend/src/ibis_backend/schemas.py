"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    """Serialized user response."""

    id: str
    email: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class VideoRead(BaseModel):
    """Serialized video response."""

    id: str
    title: Optional[str] = None
    source_type: str
    video_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    original_created_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoUpdate(BaseModel):
    """Payload to update a video."""

    title: Optional[str] = Field(None, max_length=255)


class JobRead(BaseModel):
    """Serialized processing job."""

    id: str
    video_id: str
    job_type: str
    status: str
    progress: Optional[float] = None
    detail: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    """Payload to enqueue processing jobs."""

    job_types: list[str] = Field(default_factory=list)


class TranscriptChunkRead(BaseModel):
    """Serialized transcript chunk response."""

    id: str
    start_seconds: float
    end_seconds: float
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Token response payload."""

    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Authentication response including user data."""

    access_token: str
    token_type: str = "bearer"
    user: UserRead


class MeRead(BaseModel):
    """Serialized response for the /me endpoint."""

    user: UserRead
    storage_used_bytes: int
    storage_limit_bytes: int


class RegisterRequest(BaseModel):
    """Payload to register a new user."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    """Payload to log in."""

    email: str
    password: str


class NoteCreate(BaseModel):
    """Payload to create a new note."""

    title: str = Field(..., min_length=1, max_length=255)
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    video_id: Optional[str] = None
    video_title: Optional[str] = Field(None, max_length=255)
    video_start_seconds: Optional[float] = Field(None, ge=0)
    video_end_seconds: Optional[float] = Field(None, ge=0)


class NoteUpdate(BaseModel):
    """Payload to update a note."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    body: Optional[str] = None
    tags: Optional[list[str]] = None
    archived: Optional[bool] = None
    video_start_seconds: Optional[float] = Field(None, ge=0)
    video_end_seconds: Optional[float] = Field(None, ge=0)


class NoteRead(BaseModel):
    """Serialized note response."""

    id: str
    title: str
    body: str
    tags: list[str]
    archived: bool
    created_at: datetime
    updated_at: datetime
    video_id: Optional[str] = None
    video_title: Optional[str] = None
    video_source_type: Optional[str] = None
    video_url: Optional[str] = None
    video_start_seconds: Optional[float] = None
    video_end_seconds: Optional[float] = None

    model_config = {"from_attributes": True}


class NoteVersionRead(BaseModel):
    """Serialized note version response."""

    id: str
    note_id: str
    title: str
    body: str
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskRead(BaseModel):
    """Serialized task response."""

    id: str
    note_id: str
    note_title: str
    text: str
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    """Payload to update a task."""

    completed: Optional[bool] = None
