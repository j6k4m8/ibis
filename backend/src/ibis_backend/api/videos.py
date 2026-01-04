"""Video upload and library endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ibis_backend.config import get_settings
from ibis_backend.db import get_db
from ibis_backend.dependencies import get_current_user
from ibis_backend.models import Note, ProcessingJob, TranscriptChunk, User, Video, utcnow
from ibis_backend.schemas import TranscriptChunkRead, VideoRead, VideoUpdate

router = APIRouter()


def video_to_read(video: Video) -> VideoRead:
    """Convert a Video ORM model to a response schema.

    Args:
        video: Video ORM instance.

    Returns:
        VideoRead: Serialized video.
    """

    settings = get_settings()
    thumbnail_url = None
    if video.source_type == "local":
        video_url = f"{settings.public_base_url}/videos/{video.id}/stream"
        if video.thumbnail_key:
            thumbnail_url = f"{settings.public_base_url}/videos/{video.id}/thumbnail"
    else:
        video_url = video.source_url
        if video.source_url:
            youtube_id = extract_youtube_id(video.source_url)
            if youtube_id:
                thumbnail_url = f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg"

    return VideoRead(
        id=video.id,
        title=video.title,
        source_type=video.source_type,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        file_size_bytes=video.file_size_bytes,
        original_filename=video.original_filename,
        mime_type=video.mime_type,
        original_created_at=video.original_created_at,
        duration_seconds=video.duration_seconds,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def extract_youtube_id(url: str) -> str | None:
    """Extract a YouTube video ID from a URL."""

    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    if "youtube.com" in url:
        parts = url.split("v=")
        if len(parts) > 1:
            return parts[1].split("&")[0]
    return None


@router.get("", response_model=list[VideoRead])
def list_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VideoRead]:
    """List videos owned by the current user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        list[VideoRead]: Video library entries.
    """

    videos = (
        db.query(Video)
        .filter(Video.user_id == current_user.id)
        .order_by(Video.created_at.desc())
        .all()
    )
    return [video_to_read(video) for video in videos]


@router.get("/{video_id}", response_model=VideoRead)
def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoRead:
    """Fetch a video by ID.

    Args:
        video_id: Video ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        VideoRead: Video metadata.
    """

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video_to_read(video)


@router.post("/upload", response_model=VideoRead, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    last_modified_ms: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoRead:
    """Upload a local video file and add it to the library.

    Args:
        file: Uploaded video file.
        title: Optional display title.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        VideoRead: Stored video metadata.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing upload filename.")

    settings = get_settings()
    max_bytes = settings.upload_max_bytes
    upload_root = Path(settings.upload_dir).expanduser()
    user_dir = upload_root / current_user.id
    user_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix
    storage_name = f"{uuid4().hex}{suffix}"
    storage_key = f"{current_user.id}/{storage_name}"
    destination = upload_root / storage_key

    bytes_written = 0
    exceeded = False
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    exceeded = True
                    break
                handle.write(chunk)
    finally:
        await file.close()

    if exceeded:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds size limit.",
        )

    if bytes_written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    original_created_at = None
    if last_modified_ms is not None and last_modified_ms > 0:
        original_created_at = datetime.fromtimestamp(
            last_modified_ms / 1000, tz=timezone.utc
        )

    if title and title.strip():
        display_title = title.strip()
    elif original_created_at:
        display_title = original_created_at.strftime("%Y-%m-%d %H:%M")
    else:
        display_title = utcnow().strftime("%Y-%m-%d %H:%M")
    created_at = original_created_at or utcnow()
    video = Video(
        source_type="local",
        source_url=None,
        storage_key=storage_key,
        title=display_title,
        duration_seconds=None,
        file_size_bytes=bytes_written,
        original_filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        original_created_at=original_created_at,
        created_at=created_at,
        updated_at=created_at,
        user=current_user,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    settings = get_settings()
    if settings.processing_enabled:
        job_types: list[str] = []
        if settings.transcode_enabled:
            job_types.append("transcode")
        if settings.transcription_enabled:
            job_types.append("transcribe")
        job_types.extend(["thumbnail", "duration", "creation_time"])
        if job_types:
            now = utcnow()
            for job_type in job_types:
                db.add(
                    ProcessingJob(
                        video_id=video.id,
                        job_type=job_type,
                        status="queued",
                        created_at=now,
                        updated_at=now,
                    )
                )
            db.commit()
            db.refresh(video)

    return video_to_read(video)


@router.patch("/{video_id}", response_model=VideoRead)
def update_video(
    video_id: str,
    payload: VideoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoRead:
    """Update video metadata for a library item.

    Args:
        video_id: Video ID.
        payload: Update payload.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        VideoRead: Updated video.
    """

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if payload.title is not None:
        video.title = payload.title
    if payload.created_at is not None:
        video.created_at = payload.created_at
    video.updated_at = utcnow()
    db.commit()
    db.refresh(video)
    return video_to_read(video)


@router.get("/{video_id}/stream")
def stream_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream a locally stored video.

    Args:
        video_id: Video ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        FileResponse: Video file response.
    """

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.source_type != "local" or not video.storage_key:
        raise HTTPException(status_code=404, detail="Video file not available")

    settings = get_settings()
    path = Path(settings.upload_dir).expanduser() / video.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path,
        media_type=video.mime_type or "application/octet-stream",
        filename=video.original_filename,
    )


@router.get("/{video_id}/thumbnail")
def stream_thumbnail(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Return a thumbnail image for a locally stored video."""

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.source_type != "local" or not video.thumbnail_key:
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    settings = get_settings()
    path = Path(settings.upload_dir).expanduser() / video.thumbnail_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(path, media_type="image/jpeg", filename=path.name)


@router.get("/{video_id}/transcript", response_model=list[TranscriptChunkRead])
def list_transcript_chunks(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TranscriptChunkRead]:
    """List transcript chunks for a video.

    Args:
        video_id: Video ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        list[TranscriptChunkRead]: Transcript chunks ordered by start time.
    """

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    chunks = (
        db.query(TranscriptChunk)
        .filter(TranscriptChunk.video_id == video.id)
        .order_by(TranscriptChunk.start_seconds.asc())
        .all()
    )
    return [TranscriptChunkRead.model_validate(chunk) for chunk in chunks]


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a video from the library if it has no linked notes.

    Args:
        video_id: Video ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Response: Empty response on success.
    """

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    linked_notes = db.query(Note).filter(Note.video_id == video.id).count()
    if linked_notes > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video has notes attached.",
        )

    db.query(ProcessingJob).filter(ProcessingJob.video_id == video.id).delete()
    db.query(TranscriptChunk).filter(TranscriptChunk.video_id == video.id).delete()
    db.delete(video)
    db.commit()

    if video.source_type == "local" and video.storage_key:
        settings = get_settings()
        path = Path(settings.upload_dir).expanduser() / video.storage_key
        path.unlink(missing_ok=True)
        if video.thumbnail_key:
            thumb_path = Path(settings.upload_dir).expanduser() / video.thumbnail_key
            thumb_path.unlink(missing_ok=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
