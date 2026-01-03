"""Video upload and library endpoints."""

from __future__ import annotations

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
    if video.source_type == "local":
        video_url = f"{settings.public_base_url}/videos/{video.id}/stream"
    else:
        video_url = video.source_url

    return VideoRead(
        id=video.id,
        title=video.title,
        source_type=video.source_type,
        video_url=video_url,
        file_size_bytes=video.file_size_bytes,
        original_filename=video.original_filename,
        mime_type=video.mime_type,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


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

    if title and title.strip():
        display_title = title.strip()
    else:
        display_title = utcnow().strftime("%Y-%m-%d %H:%M")
    video = Video(
        source_type="local",
        source_url=None,
        storage_key=storage_key,
        title=display_title,
        duration_seconds=None,
        file_size_bytes=bytes_written,
        original_filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        created_at=utcnow(),
        updated_at=utcnow(),
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)
