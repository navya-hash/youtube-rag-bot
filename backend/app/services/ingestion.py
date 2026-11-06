
import logging
import uuid

from sqlalchemy.orm import Session
from app.services.transcript_errors import TranscriptIngestionError

from app.models import Video
from app.db.repository import (
    get_or_create_video,
    add_video_to_chat,
)
from app.models import Chat
from app.services.youtube import (
    extract_video_id,
    fetch_transcript_with_fallback,
)
from app.services.chunking import chunk_transcript
from app.services.embeddings import embed_texts
from app.services.vector_store import ensure_collection, upsert_chunks,delete_video_chunks


logger = logging.getLogger(__name__)


class VideoIngestionError(Exception):
    """Raised when a video cannot be fully ingested."""


def ingest_video_for_chat(
    db: Session,
    chat: Chat,
    owner_id: uuid.UUID,
    url: str,
    language: str = "en",
) -> dict:
    """
    Fetch, chunk, embed, and store a YouTube video.

    The video is associated with the chat only after successful
    vector storage. Existing completed videos are reused.
    """

    youtube_video_id = extract_video_id(url)

    video = get_or_create_video(
        db=db,
        owner_id=owner_id,
        youtube_video_id=youtube_video_id,
        url=url,
    )

    # Reuse a previously completed ingestion.
    if video.status == "completed":
        add_video_to_chat(db, chat, video)

        return {
            "video_id": video.id,
            "youtube_video_id": video.youtube_video_id,
            "chat_id": chat.id,
            "status": video.status,
            "language": video.language,
            "is_generated": None,
            "chunk_count": 0,
            "message": "Video was already ingested and has been added to this chat.",
        }

    try:
        video.status = "processing"
        video.error_message = None
        db.commit()

        # 1. Fetch transcript.
        transcript_data = fetch_transcript_with_fallback(
            youtube_video_id,
            language,
        )

        # 2. Create timestamp-aware chunks.
        chunks = chunk_transcript(
            segments=transcript_data["segments"],
            video_id=str(video.id),
            youtube_video_id=youtube_video_id,
            language=transcript_data["language"],
            is_generated=transcript_data["is_generated"],
        )

        if not chunks:
            raise VideoIngestionError(
                "No usable transcript chunks were generated."
            )

        # 3. Generate embeddings.
        vectors = embed_texts(
            [chunk["text"] for chunk in chunks]
        )

        if len(vectors) != len(chunks):
            raise VideoIngestionError(
                "The number of embeddings does not match the number of chunks."
            )

        # 4. Ensure the Qdrant collection exists.
        ensure_collection(vector_size=384)

        # 5. Remove old chunks before storing the new transcript.
        delete_video_chunks(
            owner_id=owner_id,
            video_id=video.id,
        )

        # 6. Store the new transcript chunks.
        upsert_chunks(
            chunks=chunks,
            vectors=vectors,
            owner_id=owner_id,
        )

        # 6. Associate the successfully ingested video with the chat.
        add_video_to_chat(db, chat, video)

        # 7. Mark ingestion as completed.
        video.status = "completed"
        video.language = transcript_data["language"]
        video.error_message = None

        db.commit()
        db.refresh(video)

        return {
            "video_id": video.id,
            "youtube_video_id": youtube_video_id,
            "chat_id": chat.id,
            "status": video.status,
            "language": video.language,
            "is_generated": transcript_data["is_generated"],
            "chunk_count": len(chunks),
            "message": "Video successfully ingested and added to chat.",
        }

    except Exception as exc:
        logger.exception(
            "Video ingestion failed for video_id=%s",
            video.id,
        )

        db.rollback()

        # Persist the failure status so that ingestion can be retried.
        try:
            video = db.get(Video, video.id)

            if video is not None:
                video.status = "failed"
                video.error_message = str(exc)[:2000]
                db.commit()

        except Exception:
            db.rollback()
            logger.exception(
                "Could not update failed ingestion status for video_id=%s",
                video.id,
            )

        if isinstance(exc, (VideoIngestionError, TranscriptIngestionError)):
            raise

        raise VideoIngestionError(
            "Video ingestion failed. Please try again."
        ) from exc
