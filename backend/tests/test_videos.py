import pytest
from fastapi.testclient import TestClient

from ibis_backend.app import create_app
from ibis_backend.config import get_settings
from ibis_backend.db import SessionLocal
from ibis_backend.models import TranscriptChunk, utcnow


def register_user(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "supersecret"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def upload_client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("IBIS_UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("IBIS_PUBLIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("IBIS_UPLOAD_MAX_BYTES", "1048576")
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def upload_auth_headers(upload_client: TestClient) -> dict[str, str]:
    return register_user(upload_client, "videos@example.com")


def test_upload_and_stream_video(
    upload_client: TestClient, upload_auth_headers: dict[str, str]
) -> None:
    payload = b"video-bytes"
    response = upload_client.post(
        "/videos/upload",
        data={"title": "Lesson Clip"},
        files={"file": ("lesson.mp4", payload, "video/mp4")},
        headers=upload_auth_headers,
    )
    assert response.status_code == 201
    video = response.json()
    assert video["title"] == "Lesson Clip"
    assert video["file_size_bytes"] == len(payload)
    assert video["video_url"]

    list_response = upload_client.get("/videos", headers=upload_auth_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = upload_client.get(f"/videos/{video['id']}", headers=upload_auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == video["id"]

    stream_response = upload_client.get(
        f"/videos/{video['id']}/stream", headers=upload_auth_headers
    )
    assert stream_response.status_code == 200
    assert stream_response.content == payload


def test_upload_enqueues_jobs_when_enabled(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("IBIS_UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("IBIS_PUBLIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("IBIS_UPLOAD_MAX_BYTES", "1048576")
    monkeypatch.setenv("IBIS_PROCESSING_ENABLED", "true")
    monkeypatch.setenv("IBIS_TRANSCRIPTION_ENABLED", "true")
    monkeypatch.setenv("IBIS_TRANSCODE_ENABLED", "true")
    get_settings.cache_clear()
    client = TestClient(create_app())
    headers = register_user(client, "jobs@example.com")

    payload = b"video-bytes"
    response = client.post(
        "/videos/upload",
        data={"title": "Lesson Clip"},
        files={"file": ("lesson.mp4", payload, "video/mp4")},
        headers=headers,
    )
    assert response.status_code == 201

    jobs_response = client.get("/jobs", headers=headers)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    job_types = {job["job_type"] for job in jobs}
    assert {"transcode", "transcribe"} <= job_types


def test_me_storage_usage(
    upload_client: TestClient, upload_auth_headers: dict[str, str]
) -> None:
    payload = b"storage-check"
    upload_client.post(
        "/videos/upload",
        data={"title": "Storage"},
        files={"file": ("lesson.mp4", payload, "video/mp4")},
        headers=upload_auth_headers,
    )

    me_response = upload_client.get("/me", headers=upload_auth_headers)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["storage_used_bytes"] == len(payload)
    assert data["storage_limit_bytes"] >= data["storage_used_bytes"]


def test_upload_rejects_large_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("IBIS_UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("IBIS_PUBLIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("IBIS_UPLOAD_MAX_BYTES", "5")
    get_settings.cache_clear()
    client = TestClient(create_app())
    headers = register_user(client, "limit@example.com")

    response = client.post(
        "/videos/upload",
        files={"file": ("big.mp4", b"123456", "video/mp4")},
        headers=headers,
    )
    assert response.status_code == 413


def test_delete_video(
    upload_client: TestClient, upload_auth_headers: dict[str, str]
) -> None:
    payload = b"video-bytes"
    response = upload_client.post(
        "/videos/upload",
        data={"title": "Lesson Clip"},
        files={"file": ("lesson.mp4", payload, "video/mp4")},
        headers=upload_auth_headers,
    )
    video = response.json()

    delete_response = upload_client.delete(
        f"/videos/{video['id']}", headers=upload_auth_headers
    )
    assert delete_response.status_code == 204

    list_response = upload_client.get("/videos", headers=upload_auth_headers)
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_video_rejects_when_notes_attached(
    upload_client: TestClient, upload_auth_headers: dict[str, str]
) -> None:
    payload = b"video-bytes"
    response = upload_client.post(
        "/videos/upload",
        data={"title": "Lesson Clip"},
        files={"file": ("lesson.mp4", payload, "video/mp4")},
        headers=upload_auth_headers,
    )
    video_id = response.json()["id"]

    note_response = upload_client.post(
        "/notes",
        json={"title": "Lesson", "body": "", "tags": [], "video_id": video_id},
        headers=upload_auth_headers,
    )
    assert note_response.status_code == 201

    delete_response = upload_client.delete(
        f"/videos/{video_id}", headers=upload_auth_headers
    )
    assert delete_response.status_code == 409


def test_list_transcript_chunks(
    upload_client: TestClient, upload_auth_headers: dict[str, str]
) -> None:
    payload = b"video-bytes"
    response = upload_client.post(
        "/videos/upload",
        data={"title": "Lesson Clip"},
        files={"file": ("lesson.mp4", payload, "video/mp4")},
        headers=upload_auth_headers,
    )
    video_id = response.json()["id"]

    with SessionLocal() as session:
        session.add(
            TranscriptChunk(
                video_id=video_id,
                start_seconds=2.0,
                end_seconds=4.0,
                text="Second chunk",
                created_at=utcnow(),
            )
        )
        session.add(
            TranscriptChunk(
                video_id=video_id,
                start_seconds=0.5,
                end_seconds=1.5,
                text="First chunk",
                created_at=utcnow(),
            )
        )
        session.commit()

    transcript_response = upload_client.get(
        f"/videos/{video_id}/transcript", headers=upload_auth_headers
    )
    assert transcript_response.status_code == 200
    chunks = transcript_response.json()
    assert len(chunks) == 2
    assert chunks[0]["text"] == "First chunk"
