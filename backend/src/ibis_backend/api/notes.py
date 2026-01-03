"""Note endpoints."""

from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ibis_backend.dependencies import get_current_user
from ibis_backend.db import get_db
from ibis_backend.models import Note, NoteVersion, User, Video, utcnow
from ibis_backend.schemas import NoteCreate, NoteRead, NoteUpdate, NoteVersionRead

router = APIRouter()


def note_to_read(note: Note) -> NoteRead:
    """Convert a Note ORM model to a response schema.

    Args:
        note: Note ORM instance.

    Returns:
        NoteRead: Serialized note.
    """

    video_url = note.video.source_url if note.video else None
    return NoteRead(
        id=note.id,
        title=note.title,
        body=note.body,
        tags=note.tags or [],
        archived=note.archived,
        created_at=note.created_at,
        updated_at=note.updated_at,
        video_url=video_url,
    )


def upsert_note_version(note: Note, db: Session) -> NoteVersion:
    """Create or update a note snapshot, throttled to one per minute.

    Args:
        note: Note ORM instance.
        db: Database session.

    Returns:
        NoteVersion: Stored note version.
    """

    now = utcnow()
    latest = (
        db.query(NoteVersion)
        .filter(NoteVersion.note_id == note.id)
        .order_by(NoteVersion.created_at.desc())
        .first()
    )

    if latest:
        latest_time = latest.created_at
        if latest_time.tzinfo is None:
            latest_time = latest_time.replace(tzinfo=timezone.utc)
        if (now - latest_time).total_seconds() < 60:
            latest.title = note.title
            latest.body = note.body
            latest.tags = note.tags or []
            latest.created_at = now
            db.add(latest)
            return latest

    version = NoteVersion(
        note_id=note.id,
        title=note.title,
        body=note.body,
        tags=note.tags or [],
        created_at=now,
    )
    db.add(version)
    return version


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

    video = None
    if payload.video_url:
        video = Video(
            source_type="external",
            source_url=payload.video_url,
            created_at=utcnow(),
            updated_at=utcnow(),
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
        user=current_user,
    )
    db.add(note)
    db.flush()

    upsert_note_version(note, db)
    db.commit()
    db.refresh(note)

    return note_to_read(note)


@router.get("", response_model=list[NoteRead])
def list_notes(
    archived: bool = False,
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

    note.updated_at = utcnow()

    upsert_note_version(note, db)
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
            body=version.body,
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
        body=version.body,
        tags=version.tags or [],
        created_at=version.created_at,
    )
