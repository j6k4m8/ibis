from fastapi.testclient import TestClient


def test_create_and_list_note(client: TestClient) -> None:
    payload = {
        "title": "Lesson 1",
        "body": "Intro",
        "tags": ["tag1", "tag2"],
        "video_url": "https://youtube.com/watch?v=abc123",
    }
    response = client.post("/notes", json=payload)
    assert response.status_code == 201
    note = response.json()
    assert note["title"] == "Lesson 1"
    assert note["tags"] == ["tag1", "tag2"]
    assert note["video_url"] == payload["video_url"]

    list_response = client.get("/notes")
    assert list_response.status_code == 200
    notes = list_response.json()
    assert len(notes) == 1
    assert notes[0]["id"] == note["id"]


def test_update_creates_version(client: TestClient) -> None:
    create_response = client.post(
        "/notes",
        json={"title": "Lesson 2", "body": "Old body", "tags": []},
    )
    note_id = create_response.json()["id"]

    update_response = client.patch(
        f"/notes/{note_id}",
        json={"body": "New body", "tags": ["updated"]},
    )
    assert update_response.status_code == 200

    versions_response = client.get(f"/notes/{note_id}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) >= 2
    assert versions[0]["body"] == "New body"
