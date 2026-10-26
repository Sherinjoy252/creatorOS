
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api import app, get_db, require_current_user


@pytest.fixture
def content_client():
    """Create a test client with mocked database and authenticated user."""
    mock_db = MagicMock()
    user_id = uuid4()
    current_user = SimpleNamespace(id=user_id)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_current_user] = lambda: current_user

    with TestClient(app) as client:
        yield client, mock_db, current_user

    app.dependency_overrides.clear()


def mock_brand_voice():
    """Return a mock brand voice service and saved profile."""
    voice_service = MagicMock()
    voice_service.load_voice.return_value = SimpleNamespace(
        profile="Simple, practical and professional."
    )
    return voice_service


def mock_graph_result():
    """Return a successful creator-agent workflow result."""
    return {
        "draft": "Here is a practical LinkedIn post about Java.",
        "approved": True,
        "strategist_angle": "Practical learning",
        "strategy_reason": "Readers benefit from real examples.",
        "revision_count": 1,
        "audit_trail": [
            "Strategist selected a practical angle.",
            "Editor requested a revision.",
            "Editor approved the revised draft.",
        ],
    }


def test_generate_content_saves_to_database(content_client):
    client, mock_db, current_user = content_client

    with (
        patch("api.BrandVoiceService", return_value=mock_brand_voice()),
        patch("api.build_creator_graph") as mock_build_graph,
    ):
        mock_build_graph.return_value.invoke.return_value = mock_graph_result()

        response = client.post(
            "/api/content/generate",
            json={"topic": "Java Streams"},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["topic"] == "Java Streams"
    assert data["draft"] == mock_graph_result()["draft"]
    assert data["approved"] is True
    assert data["revision_count"] == 1
    assert len(data["audit_trail"]) == 3

    mock_db.add.assert_called_once()
    saved_content = mock_db.add.call_args.args[0]

    assert str(saved_content.user_id) == str(current_user.id)
    assert saved_content.topic == "Java Streams"
    assert saved_content.draft == data["draft"]

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(saved_content)


def test_content_history_returns_only_current_users_posts(content_client):
    client, mock_db, current_user = content_client

    saved_post = SimpleNamespace(
        id=uuid4(),
        user_id=current_user.id,
        topic="Java Streams",
        draft="A saved LinkedIn post.",
        approved=True,
        strategist_angle="Practical examples",
        strategy_reason="Useful for learners.",
        revision_count=1,
        audit_trail=["Strategist planned", "Editor approved"],
        created_at=None,
    )

    mock_db.scalars.return_value.all.return_value = [saved_post]

    response = client.get("/api/content/history")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(saved_post.id)
    assert data[0]["topic"] == "Java Streams"

    # Verify that the database query filters by the logged-in user's ID.
    statement = mock_db.scalars.call_args.args[0]
    compiled = statement.compile()
    query_params = compiled.params

    assert any(
        str(value) == str(current_user.id)
        for value in query_params.values()
    )
    assert "generated_contents.user_id" in str(statement)


def test_generate_content_handles_ai_failure(content_client):
    client, mock_db, _ = content_client

    with (
        patch("api.BrandVoiceService", return_value=mock_brand_voice()),
        patch("api.build_creator_graph") as mock_build_graph,
    ):
        mock_build_graph.return_value.invoke.side_effect = RuntimeError(
            "Simulated AI failure"
        )

        response = client.post(
            "/api/content/generate",
            json={"topic": "Java Streams"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Content generation failed. Please try again."
    )

    # Failed generation must not save a content record.
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_generate_content_rejects_short_topic(content_client):
    client, mock_db, _ = content_client

    response = client.post(
        "/api/content/generate",
        json={"topic": "ab"},
    )

    assert response.status_code == 422
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_content_history_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/api/content/history")

    assert response.status_code == 401
