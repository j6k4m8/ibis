"""Background media processing worker."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from ibis_backend.config import get_settings
from ibis_backend.db import SessionLocal
from ibis_backend.models import ProcessingJob, TranscriptChunk, Video, utcnow
from ibis_backend.services.video_metadata import is_youtube_url


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
        "26",
        "-preset",
        "slow",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
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


def process_thumbnail(video: Video, db: Session) -> tuple[bool, str | None]:
    """Generate a thumbnail for a video."""

    settings = get_settings()
    if not shutil.which(settings.ffmpeg_path):
        return False, "FFmpeg not available"

    source = get_video_source_path(video)
    if not source or not source.exists():
        return False, "Source file unavailable"

    output_dir = Path(settings.upload_dir).expanduser() / "thumbnails" / video.user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video.id}.jpg"

    command = [
        settings.ffmpeg_path,
        "-i",
        str(source),
        "-ss",
        "00:00:03.000",
        "-vframes",
        "1",
        "-q:v",
        "3",
        "-y",
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.decode("utf-8", errors="ignore")[:500]

    if output_path.exists():
        video.thumbnail_key = f"thumbnails/{video.user_id}/{output_path.name}"
        video.updated_at = utcnow()
        db.commit()
        return True, "Thumbnail generated"
    return False, "Thumbnail generation failed"


def process_duration(video: Video, db: Session) -> tuple[bool, str | None]:
    """Read duration metadata for a video."""

    settings = get_settings()
    ffprobe_path = getattr(settings, "ffprobe_path", "ffprobe")
    if not shutil.which(ffprobe_path):
        return False, "FFprobe not available"

    source = get_video_source_path(video)
    if not source or not source.exists():
        return False, "Source file unavailable"

    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr[-500:]

    try:
        duration_seconds = float(result.stdout.strip())
    except ValueError:
        return False, "Duration parse failed"

    if duration_seconds <= 0:
        return False, "Duration unavailable"

    video.duration_seconds = int(math.ceil(duration_seconds))
    video.updated_at = utcnow()
    db.commit()
    return True, f"Duration {int(math.ceil(duration_seconds))}s"


def process_creation_time(video: Video, db: Session) -> tuple[bool, str | None]:
    """Read creation_time metadata for a video."""

    settings = get_settings()
    ffprobe_path = getattr(settings, "ffprobe_path", "ffprobe")
    if not shutil.which(ffprobe_path):
        return False, "FFprobe not available"

    source = get_video_source_path(video)
    if not source or not source.exists():
        return False, "Source file unavailable"

    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format_tags=creation_time",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr[-500:]

    raw = result.stdout.strip()
    if not raw:
        return False, "No creation_time metadata"

    parsed = _parse_ffprobe_datetime(raw)
    if not parsed:
        return False, "creation_time parse failed"

    video.original_created_at = parsed
    video.created_at = parsed
    video.updated_at = parsed
    db.commit()
    return True, parsed.isoformat()


def process_transcription(video: Video, db: Session) -> tuple[bool, str | None]:
    """Run Whisper CLI and store transcript chunks."""

    settings = get_settings()
    if video.source_type != "local":
        if video.source_url and is_youtube_url(video.source_url):
            return process_youtube_captions(video, db)
        return False, "Transcription not supported for this video"

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


def process_youtube_captions(video: Video, db: Session) -> tuple[bool, str | None]:
    """Fetch YouTube captions and store transcript chunks."""

    settings = get_settings()
    if not shutil.which(settings.ytdlp_path):
        return False, "yt-dlp not available"
    if not video.source_url:
        return False, "Missing video URL"

    output_dir = Path(settings.upload_dir).expanduser() / "transcripts" / video.user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"{video.id}.%(ext)s")

    command = [
        settings.ytdlp_path,
        "--skip-download",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang",
        "en.*",
        "--sub-format",
        "vtt",
        "-o",
        output_template,
        video.source_url,
    ]

    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.decode("utf-8", errors="ignore")[:500]

    vtt_files = sorted(output_dir.glob(f"{video.id}*.vtt"))
    if not vtt_files:
        return False, "No captions available"

    chunks = parse_vtt(vtt_files[0].read_text())
    if not chunks:
        return False, "Caption parse failed"

    db.query(TranscriptChunk).filter(TranscriptChunk.video_id == video.id).delete()
    for chunk in chunks:
        db.add(
            TranscriptChunk(
                video_id=video.id,
                start_seconds=chunk["start"],
                end_seconds=chunk["end"],
                text=chunk["text"],
                created_at=utcnow(),
            )
        )
    db.commit()
    return True, "YouTube captions"


def parse_vtt(contents: str) -> list[dict[str, float | str]]:
    """Parse WebVTT into transcript chunks."""

    chunks: list[dict[str, float | str]] = []
    lines = [line.strip() for line in contents.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.upper() == "WEBVTT":
            i += 1
            continue
        if "-->" not in line:
            i += 1
            continue
        start_raw, end_raw = [part.strip() for part in line.split("-->")[:2]]
        start = parse_vtt_timestamp(start_raw)
        end = parse_vtt_timestamp(end_raw.split(" ")[0])
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i]:
            text_lines.append(lines[i])
            i += 1
        text = " ".join(text_lines).strip()
        if start is not None and end is not None and text:
            chunks.append({"start": start, "end": end, "text": text})
        i += 1
    return chunks


def parse_vtt_timestamp(value: str) -> float | None:
    """Parse a WebVTT timestamp into seconds."""

    parts = value.replace(",", ".").split(":")
    if len(parts) < 2:
        return None
    try:
        parts = [float(part) for part in parts]
    except ValueError:
        return None
    if len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        hours = 0.0
        minutes, seconds = parts
    return hours * 3600 + minutes * 60 + seconds


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

    if job.job_type == "thumbnail":
        ok, detail = process_thumbnail(video, db)
        mark_job_finished(job, "succeeded" if ok else "failed", detail)
        return

    if job.job_type == "duration":
        ok, detail = process_duration(video, db)
        mark_job_finished(job, "succeeded" if ok else "failed", detail)
        return

    if job.job_type == "creation_time":
        ok, detail = process_creation_time(video, db)
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


def _parse_ffprobe_datetime(value: str) -> datetime | None:
    """Parse ffprobe creation_time values."""

    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        if cleaned.endswith("Z"):
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


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
