from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


class Clock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def __call__(self) -> datetime:
        value = self.current
        self.current = self.current + timedelta(minutes=2)
        return value


def test_tasks_sorted_by_created_at(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr("ibis_backend.api.notes.utcnow", clock)
    monkeypatch.setattr("ibis_backend.task_sync.utcnow", clock)

    create_response = client.post(
        "/notes",
        json={"title": "Lesson", "body": "- [ ] First task", "tags": []},
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    client.patch(
        f"/notes/{note_id}",
        json={"body": "- [ ] First task\n- [ ] Second task"},
        headers=auth_headers,
    )

    tasks_response = client.get("/tasks", headers=auth_headers)
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert [task["text"] for task in tasks] == ["First task", "Second task"]


def test_toggle_task_updates_note_body(client: TestClient, auth_headers: dict[str, str]) -> None:
    create_response = client.post(
        "/notes",
        json={"title": "Lesson", "body": "- [ ] First task\n- [ ] Second task", "tags": []},
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    tasks_response = client.get("/tasks", headers=auth_headers)
    tasks = tasks_response.json()
    target = next(task for task in tasks if task["text"] == "First task")

    update_response = client.patch(
        f"/tasks/{target['id']}",
        json={"completed": True},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    note_response = client.get(f"/notes/{note_id}", headers=auth_headers)
    note_body = note_response.json()["body"]
    assert "- [x] First task" in note_body
