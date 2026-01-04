"""Lesson auto-grouping helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ibis_backend.models import Lesson, LessonNote, LessonVideo, Note, User, Video, utcnow


def round_to_quarter(dt: datetime) -> datetime:
    """Round a datetime to the nearest 15-minute mark."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    minutes = dt.minute + dt.second / 60 + dt.microsecond / 60_000_000
    quarter = int(minutes / 15 + 0.5)
    if quarter >= 4:
        dt = dt + timedelta(hours=1)
        quarter = 0
    rounded = dt.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=quarter * 15)
    return rounded


def auto_group_video(video: Video, user: User, db: Session) -> None:
    """Auto-group uploaded videos into lessons."""

    if video.source_type != "local":
        return
    if user.lesson_autogroup_hours <= 0:
        return

    window = timedelta(hours=user.lesson_autogroup_hours)
    start = video.created_at - window
    end = video.created_at + window
    videos = (
        db.query(Video)
        .filter(Video.user_id == user.id)
        .filter(Video.source_type == "local")
        .filter(Video.created_at >= start)
        .filter(Video.created_at <= end)
        .order_by(Video.created_at.asc())
        .all()
    )
    if len(videos) < 2:
        return

    video_ids = [vid.id for vid in videos]
    lesson = (
        db.query(Lesson)
        .join(LessonVideo, LessonVideo.lesson_id == Lesson.id)
        .filter(Lesson.user_id == user.id)
        .filter(LessonVideo.video_id.in_(video_ids))
        .order_by(Lesson.created_at.desc())
        .first()
    )

    if not lesson:
        note = (
            db.query(Note)
            .filter(Note.video_id.in_(video_ids))
            .order_by(Note.created_at.asc())
            .first()
        )
        base_time = note.created_at if note else videos[0].created_at
        lesson = Lesson(
            title=None,
            created_at=round_to_quarter(base_time),
            updated_at=utcnow(),
            user_id=user.id,
        )
        db.add(lesson)
        db.flush()

    existing_videos = {
        item.video_id
        for item in db.query(LessonVideo).filter(LessonVideo.lesson_id == lesson.id).all()
    }
    for vid in videos:
        if vid.id not in existing_videos:
            db.add(LessonVideo(lesson_id=lesson.id, video_id=vid.id, created_at=utcnow()))

    notes = db.query(Note).filter(Note.video_id.in_(video_ids)).all()
    existing_notes = {
        item.note_id
        for item in db.query(LessonNote).filter(LessonNote.lesson_id == lesson.id).all()
    }
    for note in notes:
        if note.id not in existing_notes:
            db.add(LessonNote(lesson_id=lesson.id, note_id=note.id, created_at=utcnow()))

    lesson.updated_at = utcnow()
    db.commit()
