
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
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

    # Simulate an existing post owned by the authenticated user.
    mock_db.get.return_value = content

    def save_record(record):
        record.id = uuid4()
        record.recorded_at = datetime.now(timezone.utc)
        mock_db.saved_performance = record

    mock_db.add.side_effect = save_record

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

    payload = {
        "impressions": 500,
        "likes": 40,
        "comments": 12,
        "reposts": 8,
        "data_source": "simulated",
    }

    response = client.post(
        f"/api/content/{content_id}/performance",
        json=payload,
    )

    assert response.status_code in (200, 201)
    mock_db.add.assert_called_once()

    saved_record = mock_db.saved_performance

    assert saved_record.impressions == 500
    assert saved_record.likes == 40
    assert saved_record.comments == 12
    assert saved_record.reposts == 8
    assert saved_record.data_source == "simulated"

    # Simulate the record returned by the database query.
    mock_db.scalars.return_value.all.return_value = [saved_record]

    response = client.get(
        f"/api/content/{content_id}/performance"
    )

    assert response.status_code == 200

    snapshots = response.json()

    assert len(snapshots) == 1
    assert snapshots[0]["impressions"] == 500
    assert snapshots[0]["likes"] == 40
    assert snapshots[0]["comments"] == 12
    assert snapshots[0]["reposts"] == 8


def test_negative_performance_metrics_are_rejected(performance_client):
    client, mock_db, content_id = performance_client

    payload = {
        "impressions": -1,
        "likes": 0,
        "comments": 0,
        "reposts": 0,
        "data_source": "manual",
    }

    response = client.post(
        f"/api/content/{content_id}/performance",
        json=payload,
    )

    assert response.status_code == 422
    mock_db.add.assert_not_called()
