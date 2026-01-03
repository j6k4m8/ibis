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


class TokenResponse(BaseModel):
    """Token response payload."""

    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Authentication response including user data."""

    access_token: str
    token_type: str = "bearer"
    user: UserRead


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


class NoteUpdate(BaseModel):
    """Payload to update a note."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    body: Optional[str] = None
    tags: Optional[list[str]] = None
    archived: Optional[bool] = None


class NoteRead(BaseModel):
    """Serialized note response."""

    id: str
    title: str
    body: str
    tags: list[str]
    archived: bool
    created_at: datetime
    updated_at: datetime
    video_url: Optional[str] = None

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
