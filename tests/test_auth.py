
import base64
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from api import app, get_db, SESSION_SECRET


@pytest.fixture
def setup_client():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as client:
        yield client, mock_db

    app.dependency_overrides.clear()


def set_session(client, session_data):
    """Create a signed session cookie for testing."""
    serialized = json.dumps(session_data).encode("utf-8")
    encoded = base64.b64encode(serialized)
    cookie = TimestampSigner(SESSION_SECRET).sign(encoded).decode("utf-8")

    client.cookies.set(
        "creatoros_session",
        cookie,
        domain="testserver.local",
        path="/",
    )


def test_protected_endpoint_rejects_unauthenticated_user(setup_client):
    client, _ = setup_client

    response = client.get("/api/protected-test")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_protected_endpoint_accepts_authenticated_user(setup_client):
    client, mock_db = setup_client
    user_id = uuid4()
    mock_db.get.return_value = SimpleNamespace(id=user_id)

    set_session(client, {"user_id": str(user_id)})

    response = client.get("/api/protected-test")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Authentication successful",
        "user_id": str(user_id),
    }



def test_invalid_user_id_is_rejected(setup_client):
    client, mock_db = setup_client

    set_session(client, {"user_id": "not-a-valid-uuid"})

    response = client.get("/api/protected-test")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid session. Please sign in again."


def test_nonexistent_user_is_rejected(setup_client):
    client, mock_db = setup_client
    mock_db.get.return_value = None
    user_id = uuid4()

    set_session(client, {"user_id": str(user_id)})

    response = client.get("/api/protected-test")

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found. Please sign in again."


def test_logout_clears_session(setup_client):
    client, mock_db = setup_client
    user_id = uuid4()
    mock_db.get.return_value = SimpleNamespace(id=user_id)

    set_session(client, {"user_id": str(user_id)})

    before_logout = client.get("/api/protected-test")
    assert before_logout.status_code == 200

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out successfully"

    # The logout response should expire the session cookie.
    set_cookie = logout_response.headers.get("set-cookie", "")
    assert "creatoros_session" in set_cookie
    assert "expires=Thu, 01 Jan 1970 00:00:00 GMT" in set_cookie

    # The client should no longer be authenticated.
    after_logout = client.get("/api/protected-test")
    assert after_logout.status_code == 401

