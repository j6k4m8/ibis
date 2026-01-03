"""Note endpoints."""

from __future__ import annotations

import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ibis_backend.dependencies import get_current_user
from ibis_backend.config import get_settings
from ibis_backend.db import get_db
from ibis_backend.models import Note, NoteVersion, User, Video, utcnow
from ibis_backend.note_versions import upsert_note_version
from ibis_backend.task_sync import sync_tasks_for_note
from ibis_backend.schemas import NoteCreate, NoteRead, NoteUpdate, NoteVersionRead
from ibis_backend.services.video_metadata import fetch_youtube_title, is_youtube_url

router = APIRouter()


def resolve_video_url(video: Video | None) -> str | None:
    """Resolve the video URL for a note.

    Args:
        video: Video ORM instance or None.

    Returns:
        str | None: Resolved video URL.
    """

    if not video:
        return None
    if video.source_type == "local":
        settings = get_settings()
        return f"{settings.public_base_url}/videos/{video.id}/stream"
    return video.source_url


def note_to_read(note: Note) -> NoteRead:
    """Convert a Note ORM model to a response schema.

    Args:
        note: Note ORM instance.

    Returns:
        NoteRead: Serialized note.
    """

    video_url = resolve_video_url(note.video)
    cleaned_body = note.body
    if "<!--" in cleaned_body:
        cleaned_body = re.sub(r"\s*<!--.*?-->\s*$", "", cleaned_body, flags=re.MULTILINE)
    return NoteRead(
        id=note.id,
        title=note.title,
        body=cleaned_body,
        tags=note.tags or [],
        archived=note.archived,
        created_at=note.created_at,
        updated_at=note.updated_at,
        video_id=note.video.id if note.video else None,
        video_title=note.video.title if note.video else None,
        video_source_type=note.video.source_type if note.video else None,
        video_url=video_url,
        video_start_seconds=note.video_start_seconds,
        video_end_seconds=note.video_end_seconds,
    )



@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    """Create a new note.

    Args:
        payload: Incoming note payload.
        db: Database session.

    Returns:
        NoteRead: Created note.
    """

    if payload.video_url and payload.video_id:
        raise HTTPException(
            status_code=400, detail="Provide either video_url or video_id, not both."
        )

    video = None
    if payload.video_id:
        video = (
            db.query(Video)
            .filter(Video.id == payload.video_id)
            .filter(Video.user_id == current_user.id)
            .first()
        )
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        if payload.video_title:
            video.title = payload.video_title
            video.updated_at = utcnow()
    elif payload.video_url:
        resolved_title = payload.video_title
        if not resolved_title and get_settings().fetch_video_titles:
            if is_youtube_url(payload.video_url):
                resolved_title = fetch_youtube_title(payload.video_url)
        video = Video(
            source_type="external",
            source_url=payload.video_url,
            title=resolved_title,
            created_at=utcnow(),
            updated_at=utcnow(),
            user=current_user,
        )
        db.add(video)
        db.flush()

    note = Note(
        title=payload.title,
        body=payload.body,
        tags=payload.tags,
        created_at=utcnow(),
        updated_at=utcnow(),
        video=video,
        video_start_seconds=payload.video_start_seconds,
        video_end_seconds=payload.video_end_seconds,
        user=current_user,
    )
    db.add(note)
    db.flush()

    upsert_note_version(note, db)
    sync_tasks_for_note(note, db)
    db.commit()
    db.refresh(note)

    return note_to_read(note)


@router.get("", response_model=list[NoteRead])
def list_notes(
    archived: bool = False,
    video_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteRead]:
    """List notes.

    Args:
        archived: Whether to include archived notes.
        db: Database session.

    Returns:
        list[NoteRead]: List of notes.
    """

    query = db.query(Note).filter(Note.user_id == current_user.id)
    if not archived:
        query = query.filter(Note.archived.is_(False))
    if video_id:
        query = query.filter(Note.video_id == video_id)
    notes = query.order_by(Note.updated_at.desc()).all()
    return [note_to_read(note) for note in notes]


@router.get("/{note_id}", response_model=NoteRead)
def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    """Fetch a note by ID.

    Args:
        note_id: Note ID.
        db: Database session.

    Returns:
        NoteRead: Retrieved note.
    """

    note = (
        db.query(Note)
        .filter(Note.id == note_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note_to_read(note)


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteRead:
    """Update a note and create a new history snapshot.

    Args:
        note_id: Note ID.
        payload: Update payload.
        db: Database session.

    Returns:
        NoteRead: Updated note.
    """

    note = (
        db.query(Note)
        .filter(Note.id == note_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is not None:
        note.title = payload.title
    if payload.body is not None:
        note.body = payload.body
    if payload.tags is not None:
        note.tags = payload.tags
    if payload.archived is not None:
        note.archived = payload.archived
    if "video_start_seconds" in payload.model_fields_set:
        note.video_start_seconds = payload.video_start_seconds
    if "video_end_seconds" in payload.model_fields_set:
        note.video_end_seconds = payload.video_end_seconds

    note.updated_at = utcnow()

    upsert_note_version(note, db)
    sync_tasks_for_note(note, db)
    db.commit()
    db.refresh(note)

    return note_to_read(note)


@router.get("/{note_id}/versions", response_model=list[NoteVersionRead])
def list_note_versions(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteVersionRead]:
    """List versions for a note.

    Args:
        note_id: Note ID.
        db: Database session.

    Returns:
        list[NoteVersionRead]: Note versions.
    """

    note = (
        db.query(Note)
        .filter(Note.id == note_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    versions = (
        db.query(NoteVersion)
        .filter(NoteVersion.note_id == note_id)
        .order_by(NoteVersion.created_at.desc())
        .all()
    )
    return [
        NoteVersionRead(
            id=version.id,
            note_id=version.note_id,
            title=version.title,
            body=re.sub(r"\s*<!--.*?-->\s*$", "", version.body, flags=re.MULTILINE),
            tags=version.tags or [],
            created_at=version.created_at,
        )
        for version in versions
    ]


@router.get("/{note_id}/versions/{version_id}", response_model=NoteVersionRead)
def get_note_version(
    note_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteVersionRead:
    """Fetch a specific version of a note.

    Args:
        note_id: Note ID.
        version_id: Version ID.
        db: Database session.

    Returns:
        NoteVersionRead: Note version snapshot.
    """

    note = (
        db.query(Note)
        .filter(Note.id == note_id)
        .filter(Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    version = (
        db.query(NoteVersion)
        .filter(NoteVersion.note_id == note_id)
        .filter(NoteVersion.id == version_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return NoteVersionRead(
        id=version.id,
        note_id=version.note_id,
        title=version.title,
        body=re.sub(r"\s*<!--.*?-->\s*$", "", version.body, flags=re.MULTILINE),
        tags=version.tags or [],
        created_at=version.created_at,
    )
