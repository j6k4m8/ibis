"""Note version helpers."""

from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from ibis_backend.models import Note, NoteVersion, utcnow


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
