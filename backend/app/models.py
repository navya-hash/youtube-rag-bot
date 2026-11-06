
# This file defines all five tables
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clerk_user_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "youtube_video_id", name="uq_video_owner_youtube_id"
        ),
        UniqueConstraint("id", "owner_id", name="uq_video_id_owner"),
        Index("ix_videos_owner_status", "owner_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    youtube_video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), default="pending", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (
        UniqueConstraint("id", "owner_id", name="uq_chat_id_owner"),
        Index("ix_chats_owner_updated", "owner_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200), default="New chat", nullable=False
    )
    output_language: Mapped[str] = mapped_column(
    String(50),
    default="English",
    nullable=False,
)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ChatVideo(Base):
    __tablename__ = "chat_videos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "owner_id"],
            ["chats.id", "chats.owner_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["video_id", "owner_id"],
            ["videos.id", "videos.owner_id"],
            ondelete="CASCADE",
        ),
        Index("ix_chat_videos_owner", "owner_id"),
    )

    chat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "owner_id"],
            ["chats.id", "chats.owner_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_message_role",
        ),
        Index("ix_messages_chat_created", "chat_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    output_language: Mapped[str | None] = mapped_column(
    String(50),
    nullable=True,
)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class VideoSummary(Base):
    __tablename__ = "video_summaries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["video_id", "owner_id"],
            ["videos.id", "videos.owner_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
    "video_id",
    "owner_id",
    "language",
    name="uq_video_summary_video_owner_language",
),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_video_summary_status",
        ),
        Index("ix_video_summaries_owner", "owner_id"),
        Index("ix_video_summaries_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    
    language: Mapped[str] = mapped_column(
    String(50),
    default="English",
    nullable=False,
)
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    key_points: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    topics: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(24),
        default="pending",
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

