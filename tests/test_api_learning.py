
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib import response
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import api
from api import app, get_db, require_current_user


@pytest.fixture
def authenticated_learning_client(monkeypatch):
    mock_db = MagicMock()
    user_id = uuid4()
    content_id = uuid4()

    content = SimpleNamespace(
        id=content_id,
        user_id=user_id,
        topic="Spring Boot",
        draft="A sample LinkedIn post about Spring Boot.",
    )

    performance_snapshot = SimpleNamespace(
        id=uuid4(),
        content_id=content_id,
        impressions=500,
        likes=40,
        comments=12,
        reposts=8,
        data_source="manual",
        recorded_at=datetime.now(timezone.utc),
    )

    saved_lessons = []

    # Simulate the database returning the content and performance data.
    def fake_scalar(statement):
        sql = str(statement)

        if "generated_contents" in sql:
            # Approval queries also reference generated_contents.
            return content

        if "learning_lessons" in sql:
            # Return the matching lesson for approval.
            for lesson in saved_lessons:
                return lesson
            return None

        return None

    def fake_scalars(statement):
        sql = str(statement).lower()

        if "post_performance" in sql:
            return SimpleNamespace(
                all=lambda: [performance_snapshot]
            )

        if "learning_lesson" in sql:
            return SimpleNamespace(
                all=lambda: list(reversed(saved_lessons))
            )

        return SimpleNamespace(all=lambda: [])

    mock_db.scalar.side_effect = fake_scalar
    mock_db.scalars.side_effect = fake_scalars

    def save_lessons(lessons):
        for lesson in lessons:
            lesson.id = uuid4()
            lesson.created_at = datetime.now(timezone.utc)
            lesson.approved_at = None
            saved_lessons.append(lesson)

    mock_db.add_all.side_effect = save_lessons

    def refresh(record):
        # Simulate func.now() being applied by the database.
        if getattr(record, "status", None) == "approved":
            record.approved_at = datetime.now(timezone.utc)

    mock_db.refresh.side_effect = refresh

    # Avoid calling the real Mesh API.
    class FakeLearningService:
        def propose_lessons(self, db, content, user_id):
            return [
                "Posts with clear practical examples may encourage engagement."
            ]

    monkeypatch.setattr(api, "LearningService", FakeLearningService)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )

    try:
        with TestClient(app) as client:
            yield client, content_id, saved_lessons
    finally:
        app.dependency_overrides.clear()


def test_lesson_proposal_retrieval_and_approval(
    authenticated_learning_client,
):
    client, content_id, saved_lessons = authenticated_learning_client

    # Generate lesson proposals from saved performance data.
    response = client.post(f"/api/content/{content_id}/teach")

    assert response.status_code == 200, (
        f"Status: {response.status_code}, Response: {response.text}"
        )

    proposed_lessons = response.json()["lessons"]
    assert proposed_lessons

    lesson = proposed_lessons[0]
    lesson_id = lesson["id"]

    assert lesson["lesson"]
    assert lesson["status"] == "proposed"

    # Retrieve the saved lessons.
    response = client.get(f"/api/content/{content_id}/lessons")

    assert response.status_code == 200
    assert any(item["id"] == lesson_id for item in response.json())

    # Approve the proposed lesson.
    response = client.post(
        f"/api/content/{content_id}/lessons/{lesson_id}/approve"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["approved_at"] is not None

    # Confirm that the approved status persists.
    response = client.get(f"/api/content/{content_id}/lessons")

    assert response.status_code == 200
    
    approved = next(
        item for item in response.json()
        if item["id"] == lesson_id
    )

    assert approved["status"] == "approved"
    assert approved["approved_at"] is not None
