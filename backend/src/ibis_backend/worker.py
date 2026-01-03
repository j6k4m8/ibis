"""Background media processing worker."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from sqlalchemy.orm import Session

from ibis_backend.config import get_settings
from ibis_backend.db import SessionLocal
from ibis_backend.models import ProcessingJob, TranscriptChunk, Video, utcnow


def pick_next_job(db: Session) -> ProcessingJob | None:
    """Fetch the next queued job."""

    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.status == "queued")
        .order_by(ProcessingJob.created_at.asc())
        .first()
    )


def mark_job_running(job: ProcessingJob) -> None:
    """Mark a job as running."""

    now = utcnow()
    job.status = "running"
    job.started_at = now
    job.updated_at = now


def mark_job_finished(
    job: ProcessingJob, status: str, detail: str | None = None
) -> None:
    """Mark a job as finished."""

    now = utcnow()
    job.status = status
    job.detail = detail
    job.finished_at = now
    job.updated_at = now


def get_video_source_path(video: Video) -> Path | None:
    """Resolve the local path for a video."""

    if video.source_type != "local" or not video.storage_key:
        return None
    return Path(get_settings().upload_dir).expanduser() / video.storage_key


def process_transcode(video: Video) -> tuple[bool, str | None]:
    """Run FFmpeg to transcode a video."""

    settings = get_settings()
    if not shutil.which(settings.ffmpeg_path):
        return False, "FFmpeg not available"

    source = get_video_source_path(video)
    if not source or not source.exists():
        return False, "Source file unavailable"

    source_size = source.stat().st_size
    output_dir = Path(settings.upload_dir).expanduser() / "transcoded" / video.user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video.id}.mp4"

    command = [
        settings.ffmpeg_path,
        "-i",
        str(source),
        "-vf",
        "scale='min(1920,iw)':'min(1080,ih)'",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-y",
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.decode("utf-8", errors="ignore")[:500]

    if output_path.exists():
        output_size = output_path.stat().st_size
        if source_size and output_size:
            saved = source_size - output_size
            detail = f"{format_bytes(source_size)} → {format_bytes(output_size)}"
            if saved > 0:
                detail = f"{detail} ({format_bytes(saved)} saved)"
            return True, detail
    return True, None


def process_transcription(video: Video, db: Session) -> tuple[bool, str | None]:
    """Run Whisper CLI and store transcript chunks."""

    settings = get_settings()
    if not shutil.which(settings.whisper_path):
        return False, "Whisper not available"

    source = get_video_source_path(video)
    if not source or not source.exists():
        return False, "Source file unavailable"

    output_dir = Path(settings.upload_dir).expanduser() / "transcripts" / video.user_id
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        settings.whisper_path,
        str(source),
        "--model",
        settings.whisper_model,
        "--language",
        settings.whisper_language,
        "--output_dir",
        str(output_dir),
        "--output_format",
        "json",
    ]

    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.decode("utf-8", errors="ignore")[:500]

    json_path = output_dir / f"{source.stem}.json"
    if not json_path.exists():
        return False, "Whisper output missing"

    data = json.loads(json_path.read_text())
    segments = data.get("segments", [])
    db.query(TranscriptChunk).filter(TranscriptChunk.video_id == video.id).delete()
    for segment in segments:
        db.add(
            TranscriptChunk(
                video_id=video.id,
                start_seconds=segment.get("start", 0.0),
                end_seconds=segment.get("end", 0.0),
                text=segment.get("text", ""),
                created_at=utcnow(),
            )
        )
    db.commit()
    return True, None


def handle_job(job: ProcessingJob, db: Session) -> None:
    """Handle a single processing job."""

    settings = get_settings()
    video = db.query(Video).filter(Video.id == job.video_id).first()
    if not video:
        mark_job_finished(job, "failed", "Video not found")
        return

    if not settings.processing_enabled:
        mark_job_finished(job, "skipped", "Processing disabled")
        return

    if job.job_type == "transcode":
        if not settings.transcode_enabled:
            mark_job_finished(job, "skipped", "Transcoding disabled")
            return
        ok, detail = process_transcode(video)
        mark_job_finished(job, "succeeded" if ok else "failed", detail)
        return

    if job.job_type == "transcribe":
        if not settings.transcription_enabled:
            mark_job_finished(job, "skipped", "Transcription disabled")
            return
        ok, detail = process_transcription(video, db)
        mark_job_finished(job, "succeeded" if ok else "failed", detail)
        return

    mark_job_finished(job, "skipped", "Unknown job type")


def log(message: str) -> None:
    """Log a message to stdout."""

    print(message)


def format_bytes(value: int) -> str:
    """Format bytes as a human-readable string."""

    if value < 1024:
        return f"{value} B"
    units = ["KB", "MB", "GB", "TB"]
    size = float(value)
    unit_index = -1
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    precision = 0 if size >= 10 else 1
    return f"{size:.{precision}f} {units[unit_index]}"


def run_once() -> bool:
    """Run one job if available."""

    with SessionLocal() as db:
        job = pick_next_job(db)
        if not job:
            # log(f"No queued jobs found\t{time.strftime('%Y-%m-%d %H:%M:%S')}")
            return False
        mark_job_running(job)
        log(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processing job {job.id} ({job.job_type})"
        )
        db.commit()
        db.refresh(job)
        handle_job(job, db)
        db.commit()
        log(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Finished job {job.id} with status {job.status}"
        )
        return True


def main() -> None:
    """Run the worker loop."""

    settings = get_settings()
    while True:
        handled = run_once()
        if not handled:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
