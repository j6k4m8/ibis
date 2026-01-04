"""Processing job endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ibis_backend.config import get_settings
from ibis_backend.db import get_db
from ibis_backend.dependencies import get_current_user
from ibis_backend.models import ProcessingJob, User, Video, utcnow
from ibis_backend.schemas import JobCreate, JobRead

router = APIRouter()


def job_to_read(job: ProcessingJob) -> JobRead:
    """Convert a ProcessingJob ORM model to a response schema."""

    return JobRead(
        id=job.id,
        video_id=job.video_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("", response_model=list[JobRead])
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobRead]:
    """List processing jobs for the current user."""

    jobs = (
        db.query(ProcessingJob)
        .join(Video, ProcessingJob.video_id == Video.id)
        .filter(Video.user_id == current_user.id)
        .order_by(ProcessingJob.created_at.desc())
        .all()
    )
    return [job_to_read(job) for job in jobs]


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRead:
    """Fetch a processing job by ID."""

    job = (
        db.query(ProcessingJob)
        .join(Video, ProcessingJob.video_id == Video.id)
        .filter(ProcessingJob.id == job_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_read(job)


@router.post("/videos/{video_id}", response_model=list[JobRead], status_code=status.HTTP_201_CREATED)
def enqueue_jobs(
    video_id: str,
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobRead]:
    """Enqueue processing jobs for a video."""

    settings = get_settings()
    if not settings.processing_enabled:
        raise HTTPException(status_code=409, detail="Processing is disabled")

    video = (
        db.query(Video)
        .filter(Video.id == video_id)
        .filter(Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    job_types = payload.job_types or []
    if not job_types:
        job_types = []
        if settings.transcode_enabled:
            job_types.append("transcode")
        if settings.transcription_enabled:
            job_types.append("transcribe")

    now = utcnow()
    jobs: list[ProcessingJob] = []
    for job_type in job_types:
        job = ProcessingJob(
            video_id=video.id,
            job_type=job_type,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)
    return [job_to_read(job) for job in jobs]
