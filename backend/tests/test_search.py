from fastapi.testclient import TestClient

from ibis_backend.db import SessionLocal
from ibis_backend.models import Note, TranscriptChunk, Video, utcnow


def test_search_includes_core_types(client: TestClient, auth_headers: dict[str, str]) -> None:
    note_payload = {
        "title": "Minor arpeggio",
        "body": "Practice with a metronome.",
        "tags": ["arpeggio"],
        "video_url": "https://youtube.com/watch?v=abc123",
        "video_title": "Arpeggio clip",
    }
    note_response = client.post("/notes", json=note_payload, headers=auth_headers)
    assert note_response.status_code == 201
    note = note_response.json()

    lesson_response = client.post(
        "/lessons",
        json={"title": "Arpeggio drills"},
        headers=auth_headers,
    )
    assert lesson_response.status_code == 201
    lesson = lesson_response.json()

    response = client.get("/search", params={"query": "arpeggio"}, headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()

    assert payload["query"] == "arpeggio"
    assert any(result["id"] == note["id"] for result in payload["notes"])
    assert any(result["id"] == lesson["id"] for result in payload["lessons"])
    assert any(result["id"] == note["video_id"] for result in payload["videos"])
    assert "arpeggio" in payload["tags"]


def test_search_returns_transcript_video_notes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    me_response = client.get("/auth/me", headers=auth_headers)
    user_id = me_response.json()["id"]

    with SessionLocal() as session:
        video = Video(
            source_type="external",
            source_url="https://example.com/video",
            title="Modes session",
            created_at=utcnow(),
            updated_at=utcnow(),
            user_id=user_id,
        )
        session.add(video)
        session.flush()

        note = Note(
            title="Mode practice",
            body="Focus on timing.",
            tags=["modes"],
            created_at=utcnow(),
            updated_at=utcnow(),
            video_id=video.id,
            user_id=user_id,
        )
        session.add(note)

        chunk = TranscriptChunk(
            video_id=video.id,
            start_seconds=12,
            end_seconds=24,
            text="Lydian dominant approach",
            created_at=utcnow(),
        )
        session.add(chunk)
        session.commit()

    response = client.get("/search", params={"query": "lydian"}, headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()

    assert any(match["video_id"] == video.id for match in payload["transcript_matches"])
    assert any(result["id"] == video.id for result in payload["videos"])
    assert any(result["id"] == note.id for result in payload["notes"])
