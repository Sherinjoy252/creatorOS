
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PostPerformance(Base):
    __tablename__ = "post_performance"

    __table_args__ = (
        CheckConstraint(
            "impressions >= 0",
            name="ck_post_performance_impressions",
        ),
        CheckConstraint(
            "likes >= 0",
            name="ck_post_performance_likes",
        ),
        CheckConstraint(
            "comments >= 0",
            name="ck_post_performance_comments",
        ),
        CheckConstraint(
            "reposts >= 0",
            name="ck_post_performance_reposts",
        ),
        
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    impressions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    likes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comments: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    reposts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    data_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )

    lesson: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    audience_comments: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
