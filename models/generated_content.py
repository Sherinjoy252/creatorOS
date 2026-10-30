import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class GeneratedContent(Base):
    __tablename__ = "generated_contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    topic: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    draft: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    approved: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    strategist_angle: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    strategy_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    revision_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    audit_trail: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    initial_evaluation: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    final_evaluation: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    evaluation_score_delta: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )

    image_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None
    )

    image_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )

    image_model: Mapped[str | None] = mapped_column(
        String(150), nullable=True, default=None
    )

    image_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="not_generated"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
