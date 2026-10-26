
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import User


def get_or_create_user(db: Session, userinfo: dict) -> User:
    """Find an existing LinkedIn user or create a new one."""
    subject = userinfo.get("sub")

    if not subject:
        raise ValueError("LinkedIn subject is required.")

    user = db.scalar(
        select(User).where(User.linkedin_subject == subject)
    )

    if user is None:
        user = User(
            linkedin_subject=subject,
            name=userinfo.get("name"),
            email=userinfo.get("email"),
        )
        db.add(user)
    else:
        user.name = userinfo.get("name") or user.name
        user.email = userinfo.get("email") or user.email

    db.commit()
    db.refresh(user)

    return user
