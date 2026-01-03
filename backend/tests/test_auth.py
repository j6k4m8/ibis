from fastapi.testclient import TestClient


def test_register_and_login(client: TestClient) -> None:
    register_payload = {
        "email": "teacher@example.com",
        "password": "supersecret",
        "display_name": "Teacher",
    }
    register_response = client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["user"]["email"] == "teacher@example.com"
    assert "access_token" in register_body

    login_response = client.post(
        "/auth/login", json={"email": "teacher@example.com", "password": "supersecret"}
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["user"]["email"] == "teacher@example.com"


def test_register_duplicate_email(client: TestClient) -> None:
    payload = {"email": "student@example.com", "password": "supersecret"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/auth/register", json=payload)
    assert duplicate.status_code == 409


def test_login_invalid_credentials(client: TestClient) -> None:
    payload = {"email": "student2@example.com", "password": "supersecret"}
    client.post("/auth/register", json=payload)

    invalid = client.post(
        "/auth/login", json={"email": "student2@example.com", "password": "wrong"}
    )
    assert invalid.status_code == 401
