from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api import app, get_db, require_current_user


@pytest.fixture
def performance_client():
    mock_db = MagicMock()
    user_id = uuid4()
    content_id = uuid4()

    content = SimpleNamespace(
        id=content_id,
        user_id=user_id,
    )

    mock_db.get.return_value = content
    mock_db.scalar.return_value = content
    mock_db.performance_records = []

    def save_record(record):
        record.id = uuid4()
        record.recorded_at = datetime.now(timezone.utc)

        if record.__class__.__name__ == "PostPerformance":
            mock_db.performance_records.append(record)

    mock_db.add.side_effect = save_record

    # The GET endpoint uses db.scalars(...).all()
    mock_db.scalars.return_value.all.side_effect = (
        lambda: mock_db.performance_records
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )

    try:
        with TestClient(app) as client:
            yield client, mock_db, content_id
    finally:
        app.dependency_overrides.clear()


def test_performance_snapshots_save_and_retrieve(performance_client):
    client, mock_db, content_id = performance_client

    audience_comments = [
        "This was really helpful!",
        "Could you share a practical example?",
    ]

    payload = {
        "impressions": 500,
        "likes": 40,
        "comments": 12,
        "reposts": 8,
        "audience_comments": audience_comments,
        "data_source": "manual",
    }

    with patch("api.LearningService") as mock_learning:
        mock_learning.return_value.propose_lessons.return_value = [
            "Posts with practical examples receive better engagement."
        ]

        response = client.post(
            f"/api/content/{content_id}/performance",
            json=payload,
        )

    assert response.status_code == 200

    data = response.json()

    assert data["impressions"] == 500
    assert data["learning_status"] == "completed"
    assert data["lessons_created"] == 1
    assert data["audience_comments"] == audience_comments

    mock_learning.return_value.propose_lessons.assert_called_once()

    # Verify that the comments were persisted with the performance snapshot.
    assert len(mock_db.performance_records) == 1
    assert mock_db.performance_records[0].audience_comments == audience_comments

    # Verify that the performance snapshot and comments can be retrieved.
    response = client.get(
        f"/api/content/{content_id}/performance"
    )

    assert response.status_code == 200
    snapshots = response.json()

    saved_snapshot = next(
        item for item in snapshots if item["impressions"] == 500
    )

    assert saved_snapshot["likes"] == 40
    assert saved_snapshot["comments"] == 12
    assert saved_snapshot["reposts"] == 8
    assert saved_snapshot["audience_comments"] == audience_comments


def test_negative_performance_metrics_are_rejected(performance_client):
    client, mock_db, content_id = performance_client

    payload = {
        "impressions": -1,
        "likes": 0,
        "comments": 0,
        "reposts": 0,
        "audience_comments": [],
        "data_source": "manual",
    }

    response = client.post(
        f"/api/content/{content_id}/performance",
        json=payload,
    )

    assert response.status_code == 422
    mock_db.add.assert_not_called()
