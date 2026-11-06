import logging
import uuid

from app.db.session import SessionLocal
from app.db.repository import (
    get_video_summary,
    update_video_summary_status,
)
from app.services.summarization import summarize_video

logger = logging.getLogger(__name__)


def process_video_summary(
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    language: str = "English",
) -> dict:
    db = SessionLocal()

    try:
        # Check whether a summary already exists for this language.
        existing = get_video_summary(
            db=db,
            video_id=video_id,
            owner_id=owner_id,
            language=language,
        )

        if existing and existing.status == "completed":
            return {
                "video_id": str(video_id),
                "status": "completed",
                "message": "Summary already exists",
                "summary_id": str(existing.id),
                "language": language,
            }

        # Mark this language-specific summary as processing.
        update_video_summary_status(
            db=db,
            video_id=video_id,
            owner_id=owner_id,
            status="processing",
            language=language,
        )

        # Refresh the heartbeat while the summarization is running.
        def refresh_heartbeat():
            update_video_summary_status(
                db=db,
                video_id=video_id,
                owner_id=owner_id,
                status="processing",
                language=language,
            )

        result = summarize_video(
            db=db,
            video_id=video_id,
            owner_id=owner_id,
            language=language,
            heartbeat=refresh_heartbeat,
        )

        return {
            "video_id": str(video_id),
            "status": "completed",
            "summary_id": result["id"],
            "language": language,
        }

    finally:
        db.close()