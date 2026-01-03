from fastapi.testclient import TestClient


def test_create_and_list_note(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "title": "Lesson 1",
        "body": "Intro",
        "tags": ["tag1", "tag2"],
        "video_url": "https://youtube.com/watch?v=abc123",
        "video_start_seconds": 12,
        "video_end_seconds": 94,
    }
    response = client.post("/notes", json=payload, headers=auth_headers)
    assert response.status_code == 201
    note = response.json()
    assert note["title"] == "Lesson 1"
    assert note["tags"] == ["tag1", "tag2"]
    assert note["video_url"] == payload["video_url"]
    assert note["video_start_seconds"] == payload["video_start_seconds"]
    assert note["video_end_seconds"] == payload["video_end_seconds"]

    list_response = client.get("/notes", headers=auth_headers)
    assert list_response.status_code == 200
    notes = list_response.json()
    assert len(notes) == 1
    assert notes[0]["id"] == note["id"]


def test_update_creates_version(client: TestClient, auth_headers: dict[str, str]) -> None:
    create_response = client.post(
        "/notes",
        json={"title": "Lesson 2", "body": "Old body", "tags": []},
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    update_response = client.patch(
        f"/notes/{note_id}",
        json={"body": "New body", "tags": ["updated"], "video_start_seconds": 5},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    updated_note = update_response.json()
    assert updated_note["video_start_seconds"] == 5

    versions_response = client.get(f"/notes/{note_id}/versions", headers=auth_headers)
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) >= 1
    assert versions[0]["body"] == "New body"


def test_versions_throttled_to_one_per_minute(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    create_response = client.post(
        "/notes",
        json={"title": "Lesson 3", "body": "First", "tags": []},
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    client.patch(
        f"/notes/{note_id}",
        json={"body": "Second"},
        headers=auth_headers,
    )
    client.patch(
        f"/notes/{note_id}",
        json={"body": "Third"},
        headers=auth_headers,
    )

    versions_response = client.get(f"/notes/{note_id}/versions", headers=auth_headers)
    versions = versions_response.json()
    assert len(versions) == 1
    assert versions[0]["body"] == "Third"


def test_notes_require_auth(client: TestClient) -> None:
    response = client.get("/notes")
    assert response.status_code == 401


def test_notes_are_scoped_to_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post(
        "/notes",
        json={"title": "Lesson 3", "body": "Scoped", "tags": []},
        headers=auth_headers,
    )

    other = client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "supersecret"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    list_response = client.get("/notes", headers=other_headers)
    assert list_response.status_code == 200
    assert list_response.json() == []
