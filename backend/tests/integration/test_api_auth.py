"""Integration tests for auth + healthz. Does not require GCP credentials."""
import os

os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password-123")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_success_returns_token():
    response = client.post("/auth/login", json={"username": "admin", "password": "test-password-123"})
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_failure_rejected():
    response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_protected_route_requires_session():
    response = client.get("/artifacts/some-project")
    assert response.status_code == 401


def test_protected_route_accepts_valid_session():
    login = client.post("/auth/login", json={"username": "admin", "password": "test-password-123"})
    token = login.json()["token"]
    response = client.get("/artifacts/some-project", headers={"Authorization": f"Bearer {token}"})
    # 200 or 500 depending on GCS credentials in this environment; the point of
    # this test is that auth itself doesn't block it with a 401.
    assert response.status_code != 401


def test_delete_artifact_requires_session():
    response = client.delete("/artifacts/some-project/some-file.csv")
    assert response.status_code == 401


def test_delete_all_artifacts_requires_session():
    response = client.delete("/artifacts/some-project")
    assert response.status_code == 401
