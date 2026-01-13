"""Search endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ibis_backend.api.notes import note_to_read
from ibis_backend.api.videos import video_to_read
from ibis_backend.db import get_db
from ibis_backend.dependencies import get_current_user
from ibis_backend.models import Lesson, Note, TranscriptChunk, User, Video
from ibis_backend.schemas import LessonRead, SearchResponse, TranscriptMatchRead

router = APIRouter()


def normalize_query(value: str) -> str:
    """Normalize a search query for comparisons."""

    return value.strip().lower()


def matches_text(value: str | None, term: str) -> bool:
    """Case-insensitive substring match."""

    if not value:
        return False
    return term in value.lower()


def note_matches(note: Note, term: str) -> bool:
    """Return True when a note matches a search term."""

    if matches_text(note.title, term) or matches_text(note.body, term):
        return True
    return any(matches_text(tag, term) for tag in (note.tags or []))


def video_matches(video: Video, term: str) -> bool:
    """Return True when a video matches a search term."""

    return any(
        matches_text(value, term)
        for value in (video.title, video.original_filename, video.source_url)
    )


def lesson_matches(lesson: Lesson, term: str) -> bool:
    """Return True when a lesson matches a search term."""

    return matches_text(lesson.title, term)


@router.get("", response_model=SearchResponse)
def search_library(
    query: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search notes, lessons, videos, tags, and transcripts for the current user."""

    normalized = normalize_query(query)
    if not normalized:
        return SearchResponse(
            query=query,
            notes=[],
            videos=[],
            lessons=[],
            tags=[],
            transcript_matches=[],
        )

    notes_pool = (
        db.query(Note)
        .filter(Note.user_id == current_user.id)
        .filter(Note.archived.is_(False))
        .order_by(Note.updated_at.desc())
        .all()
    )
    matching_notes = [note for note in notes_pool if note_matches(note, normalized)]

    matching_lessons = (
        db.query(Lesson)
        .filter(Lesson.user_id == current_user.id)
        .order_by(Lesson.updated_at.desc())
        .all()
    )
    matching_lessons = [
        lesson for lesson in matching_lessons if lesson_matches(lesson, normalized)
    ]

    videos_pool = (
        db.query(Video)
        .filter(Video.user_id == current_user.id)
        .order_by(Video.created_at.desc())
        .all()
    )
    matching_videos = [video for video in videos_pool if video_matches(video, normalized)]

    tags = sorted(
        {
            tag
            for note in notes_pool
            for tag in (note.tags or [])
            if matches_text(tag, normalized)
        }
    )

    transcript_rows = (
        db.query(TranscriptChunk, Video)
        .join(Video, TranscriptChunk.video_id == Video.id)
        .filter(Video.user_id == current_user.id)
        .filter(TranscriptChunk.text.ilike(f"%{normalized}%"))
        .order_by(TranscriptChunk.start_seconds.asc())
        .limit(limit)
        .all()
    )

    transcript_matches: list[TranscriptMatchRead] = []
    transcript_video_ids: set[str] = set()
    transcript_videos: dict[str, Video] = {}

    for chunk, video in transcript_rows:
        transcript_video_ids.add(video.id)
        transcript_videos[video.id] = video
        transcript_matches.append(
            TranscriptMatchRead(
                video_id=video.id,
                video_title=video.title,
                video_source_type=video.source_type,
                start_seconds=chunk.start_seconds,
                end_seconds=chunk.end_seconds,
                text=chunk.text,
            )
        )

    transcript_notes = [
        note for note in notes_pool if note.video_id and note.video_id in transcript_video_ids
    ]

    notes: list[Note] = []
    seen_notes: set[str] = set()
    for note in matching_notes + transcript_notes:
        if note.id in seen_notes:
            continue
        seen_notes.add(note.id)
        notes.append(note)

    videos: list[Video] = []
    seen_videos: set[str] = set()
    for video in matching_videos + list(transcript_videos.values()):
        if video.id in seen_videos:
            continue
        seen_videos.add(video.id)
        videos.append(video)

    lessons = [LessonRead.model_validate(lesson) for lesson in matching_lessons]
    notes = [note_to_read(note) for note in notes]
    videos = [video_to_read(video) for video in videos]

    return SearchResponse(
        query=query,
        notes=notes,
        videos=videos,
        lessons=lessons,
        tags=tags,
        transcript_matches=transcript_matches,
    )
