
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from datetime import timedelta

from app.models import (
    User,
    Video,
    Chat,
    ChatVideo,
    Message,
    VideoSummary,
    utc_now,
)

def get_or_create_user(db: Session, clerk_user_id: str) -> User:
    """Return the application user associated with a Clerk identity."""
    user = db.scalar(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )

    if user:
        return user

    user = User(clerk_user_id=clerk_user_id)
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()

        # Handle a concurrent request creating the same user.
        existing_user = db.scalar(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        if existing_user:
            return existing_user
        raise


def create_chat(
    db: Session,
    owner_id: uuid.UUID,
    title: str = "New chat",
    output_language: str = "English",
) -> Chat:
    """Create a chat owned by the specified application user."""

    chat = Chat(
        owner_id=owner_id,
        title=title,
        output_language=output_language,
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return chat


def list_chats(db: Session, owner_id: uuid.UUID) -> list[Chat]:
    """Return only the specified user's chats, newest first."""
    statement = (
        select(Chat)
        .where(Chat.owner_id == owner_id)
        .order_by(Chat.updated_at.desc(), Chat.id.desc())
    )
    return list(db.scalars(statement).all())


def get_owned_chat(
    db: Session,
    chat_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Chat | None:
    """Fetch a chat only if it belongs to the specified user."""
    statement = select(Chat).where(
        Chat.id == chat_id,
        Chat.owner_id == owner_id,
    )
    return db.scalar(statement)


def get_or_create_video(
    db: Session,
    owner_id: uuid.UUID,
    youtube_video_id: str,
    url: str,
) -> Video:
    """
    Return an existing video for this user or create a new record.

    The same YouTube video can have separate records for different users.
    """
    video = db.scalar(
        select(Video).where(
            Video.owner_id == owner_id,
            Video.youtube_video_id == youtube_video_id,
        )
    )

    if video:
        return video

    video = Video(
        owner_id=owner_id,
        youtube_video_id=youtube_video_id,
        url=url,
        status="pending",
    )
    db.add(video)

    try:
        db.commit()
        db.refresh(video)
        return video
    except Exception:
        db.rollback()

        # Handle concurrent requests for the same user's video.
        existing_video = db.scalar(
            select(Video).where(
                Video.owner_id == owner_id,
                Video.youtube_video_id == youtube_video_id,
            )
        )
        if existing_video:
            return existing_video
        raise


def add_video_to_chat(
    db: Session,
    chat: Chat,
    video: Video,
) -> ChatVideo:
    """Associate a video with a chat, enforcing matching ownership."""
    if chat.owner_id != video.owner_id:
        raise ValueError("Chat and video must belong to the same user.")

    association = db.get(ChatVideo, (chat.id, video.id))
    if association:
        return association

    association = ChatVideo(
        chat_id=chat.id,
        video_id=video.id,
        owner_id=chat.owner_id,
    )
    db.add(association)
    db.commit()
    db.refresh(association)
    return association


def list_chat_videos(
    db: Session,
    chat: Chat,
) -> list[Video]:
    """Return videos associated with a chat, belonging to its owner."""
    statement = (
        select(Video)
        .join(
            ChatVideo,
            (ChatVideo.video_id == Video.id)
            & (ChatVideo.owner_id == Video.owner_id),
        )
        .where(
            ChatVideo.chat_id == chat.id,
            ChatVideo.owner_id == chat.owner_id,
        )
        .order_by(Video.created_at.asc(), Video.id.asc())
    )
    return list(db.scalars(statement).all())


def save_message(
    db: Session,
    chat: Chat,
    role: str,
    content: str,
    citations: list | None = None,
    output_language: str | None = None,
) -> Message:
    """Persist a user or assistant message in an owned chat."""

    if role not in {"user", "assistant"}:
        raise ValueError("role must be 'user' or 'assistant'")

    now = utc_now()

    message = Message(
        chat_id=chat.id,
        owner_id=chat.owner_id,
        role=role,
        content=content,
        citations=citations,
        output_language=output_language or chat.output_language or "English",
        created_at=now,
    )

    db.add(message)
    chat.updated_at = now
    db.commit()
    db.refresh(message)

    return message


def list_messages(
    db: Session,
    chat: Chat,
    limit: int = 100,
) -> list[Message]:
    """Return messages in chronological order for an owned chat."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")

    statement = (
        select(Message)
        .where(
            Message.chat_id == chat.id,
            Message.owner_id == chat.owner_id,
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())




def get_video_summary(
    db: Session,
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    language: str = "English",
) -> VideoSummary | None:
    """Get a summary for a specific video, owner, and language."""

    statement = select(VideoSummary).where(
        VideoSummary.video_id == video_id,
        VideoSummary.owner_id == owner_id,
        VideoSummary.language == language,
    )

    return db.scalar(statement)


def save_video_summary(
    db: Session,
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    summary: str,
    key_points: list,
    topics: list,
    model_name: str,
    language: str = "English",
) -> VideoSummary:
    """Create or update a video's summary for a specific language."""

    existing = get_video_summary(
        db=db,
        video_id=video_id,
        owner_id=owner_id,
        language=language,
    )

    now = utc_now()

    if existing:
        existing.summary = summary
        existing.key_points = key_points
        existing.topics = topics
        existing.status = "completed"
        existing.error_message = None
        existing.model_name = model_name
        existing.updated_at = now

        db.commit()
        db.refresh(existing)
        return existing

    video_summary = VideoSummary(
        video_id=video_id,
        owner_id=owner_id,
        language=language,
        summary=summary,
        key_points=key_points,
        topics=topics,
        status="completed",
        model_name=model_name,
        created_at=now,
        updated_at=now,
    )

    db.add(video_summary)
    db.commit()
    db.refresh(video_summary)

    return video_summary


def update_video_summary_status(
    db: Session,
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
    language: str = "English",
) -> VideoSummary:
    """Create or update a summarization job for a specific language."""

    allowed_statuses = {"pending", "processing", "completed", "failed"}

    if status not in allowed_statuses:
        raise ValueError("Invalid video summary status.")

    existing = get_video_summary(
        db=db,
        video_id=video_id,
        owner_id=owner_id,
        language=language,
    )

    now = utc_now()

    if existing:
        existing.status = status
        existing.error_message = error_message
        existing.updated_at = now

        db.commit()
        db.refresh(existing)
        return existing

    new_summary = VideoSummary(
        video_id=video_id,
        owner_id=owner_id,
        language=language,
        status=status,
        error_message=error_message,
        created_at=now,
        updated_at=now,
    )

    db.add(new_summary)
    db.commit()
    db.refresh(new_summary)

    return new_summary



# How the below function works:
# Existing database state	Can this request claim the job?
# No summary record	Yes
# failed	Yes
# pending	No
# processing	No
# completed	No

def claim_video_summary_job(
    db: Session,
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    language: str = "English",
) -> bool:
    """
    Atomically claim a summarization job for a specific language.

    A new or failed job can be claimed.
    Pending, processing, and completed jobs cannot be claimed.
    """

    now = utc_now()

    statement = (
        insert(VideoSummary)
        .values(
            video_id=video_id,
            owner_id=owner_id,
            language=language,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(
            index_elements=[
                VideoSummary.video_id,
                VideoSummary.owner_id,
                VideoSummary.language,
            ]
        )
        .returning(VideoSummary.id)
    )

    try:
        result = db.execute(statement).scalar_one_or_none()
        db.commit()

        if result is not None:
            return True

        statement = (
            update(VideoSummary)
            .where(
                VideoSummary.video_id == video_id,
                VideoSummary.owner_id == owner_id,
                VideoSummary.language == language,
                VideoSummary.status == "failed",
            )
            .values(
                status="pending",
                error_message=None,
                updated_at=now,
            )
            .returning(VideoSummary.id)
        )

        result = db.execute(statement).scalar_one_or_none()
        db.commit()

        return result is not None

    except Exception:
        db.rollback()
        raise



def reclaim_stale_video_summary_jobs(
    db: Session,
    stale_after_minutes: int = 10,
) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    """
    Atomically move stale processing jobs back to pending.

    Returns (video_id, owner_id, language) tuples.
    """

    if stale_after_minutes < 1:
        raise ValueError("stale_after_minutes must be at least 1")

    now = utc_now()
    cutoff = now - timedelta(minutes=stale_after_minutes)

    statement = (
        update(VideoSummary)
        .where(
            VideoSummary.status == "processing",
            VideoSummary.updated_at < cutoff,
        )
        .values(
            status="pending",
            updated_at=now,
            error_message="Job recovered after becoming stale.",
        )
        .returning(
            VideoSummary.video_id,
            VideoSummary.owner_id,
            VideoSummary.language,
        )
    )

    try:
        result = db.execute(statement)

        recovered_jobs = [
            (row.video_id, row.owner_id, row.language)
            for row in result.all()
        ]

        db.commit()
        return recovered_jobs

    except Exception:
        db.rollback()
        raise



def update_chat_language(
    db: Session,
    chat: Chat,
    output_language: str,
) -> Chat:
    """Update the output language of an existing chat."""

    chat.output_language = output_language
    chat.updated_at = utc_now()

    db.commit()
    db.refresh(chat)

    return chat