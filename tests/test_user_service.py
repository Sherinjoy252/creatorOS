
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.user_service import get_or_create_user


def test_first_login_creates_user():
    db = MagicMock()
    db.scalar.return_value = None

    userinfo = {
        "sub": "linkedin-user-1",
        "name": "Sherin Joy",
        "email": "sherin@example.com",
    }

    user = get_or_create_user(db, userinfo)

    assert user.linkedin_subject == "linkedin-user-1"
    assert user.name == "Sherin Joy"
    assert user.email == "sherin@example.com"
    db.add.assert_called_once_with(user)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(user)


def test_repeated_login_reuses_existing_user():
    db = MagicMock()

    user_id = uuid4()

    existing_user = MagicMock()
    existing_user.id = user_id
    existing_user.linkedin_subject = "linkedin-user-1"
    existing_user.name = "Sherin Joy"
    existing_user.email = "old@example.com"

    # First login: no user found.
    # Second login: the same persisted user is found.
    db.scalar.side_effect = [None, existing_user]

    def assign_id_when_added(user):
        user.id = user_id

    db.add.side_effect = assign_id_when_added

    first_user = get_or_create_user(
        db,
        {
            "sub": "linkedin-user-1",
            "name": "Sherin Joy",
            "email": "old@example.com",
        },
    )

    second_user = get_or_create_user(
        db,
        {
            "sub": "linkedin-user-1",
            "name": "Sherin Joy",
            "email": "new@example.com",
        },
    )

    assert first_user.id == second_user.id == user_id
    assert second_user is existing_user
    assert second_user.email == "new@example.com"

    # Only the first login creates a user.
    db.add.assert_called_once_with(first_user)
    assert db.commit.call_count == 2


def test_different_linkedin_subject_creates_separate_user():
    db = MagicMock()
    db.scalar.return_value = None

    user = get_or_create_user(
        db,
        {
            "sub": "linkedin-user-2",
            "name": "Another User",
            "email": "another@example.com",
        },
    )

    assert user.linkedin_subject == "linkedin-user-2"
    db.add.assert_called_once_with(user)


def test_missing_linkedin_subject_is_rejected():
    db = MagicMock()

    with pytest.raises(ValueError, match="LinkedIn subject is required"):
        get_or_create_user(
            db,
            {"name": "Sherin Joy"},
        )

    db.scalar.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()
