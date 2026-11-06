
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
)
from fastapi import Query
from sqlalchemy.orm import Session

from app.core.auth import require_user
from app.db.session import get_db
from app.db.repository import (
    get_or_create_user,
    get_owned_chat,
    claim_video_summary_job,
)
from app.schemas.youtube import IngestRequest, IngestResponse
from app.services.ingestion import (
    ingest_video_for_chat,
    VideoIngestionError,
)
from app.services.transcript_errors import TranscriptIngestionError

from app.db.repository import update_video_summary_status
# from app.services.summary_worker import process_video_summary
from app.tasks.summary_tasks import generate_video_summary
import uuid

from fastapi import status
from sqlalchemy import select

from app.models import Video
from app.db.repository import get_video_summary
from app.services.summarization import (
    summarize_video,
    SummarizationError,
)
from app.core.languages import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

from fastapi.responses import StreamingResponse
from app.services.pdf_generator import generate_summary_pdf

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/youtube",
    tags=["YouTube"],
)


@router.post(
    "/ingest",
    response_model=IngestResponse,
)
def ingest_video_endpoint(
    request: IngestRequest,
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    # 1. Resolve the authenticated Clerk user.
    user = get_or_create_user(db, clerk_user_id)

    # 2. Verify that the chat belongs to this user.
    chat = get_owned_chat(
        db=db,
        chat_id=request.chat_id,
        owner_id=user.id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    try:
        # 3. Perform the complete video ingestion workflow.
        result = ingest_video_for_chat(
            db=db,
            chat=chat,
            owner_id=user.id,
            url=str(request.url),
            language=request.language,
        )

        # 4. Return the structured response.
        return IngestResponse(**result)

    except TranscriptIngestionError as exc:
        logger.warning(
            "Transcript ingestion error: %s",
            exc.message,
        )

        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.message,
            },
        ) from exc

    except VideoIngestionError as exc:
        logger.exception("Video ingestion failed.")

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc



video_router = APIRouter(
    prefix="/api/v1/videos",
    tags=["Video Summarization"],
)


@video_router.post("/{video_id}/summarize")
def summarize_video_endpoint(
    video_id: uuid.UUID,
    response: Response,
    language: str = Query(default=DEFAULT_LANGUAGE),
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    language = validate_output_language(language)
    # 1. Resolve authenticated user.
    user = get_or_create_user(db, clerk_user_id)

    # 2. Verify video ownership.
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == user.id,
        )
    )

    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Video ingestion is not completed yet.",
        )

    # 3. Check for a summary in the requested language.
    existing_summary = get_video_summary(
        db=db,
        video_id=video_id,
        owner_id=user.id,
        language=language,
    )

    if existing_summary and existing_summary.status == "completed":
        return {
            "message": "Summary already exists",
            "summary": {
                "id": str(existing_summary.id),
                "video_id": str(existing_summary.video_id),
                "summary": existing_summary.summary,
                "key_points": existing_summary.key_points,
                "topics": existing_summary.topics,
                "status": existing_summary.status,
                "model_name": existing_summary.model_name,
                "language": existing_summary.language,
            },
        }

    # 4. Atomically claim a job for this language.
    claimed = claim_video_summary_job(
        db=db,
        video_id=video_id,
        owner_id=user.id,
        language=language,
    )

    if not claimed:
        latest_summary = get_video_summary(
            db=db,
            video_id=video_id,
            owner_id=user.id,
            language=language,
        )

        if latest_summary and latest_summary.status == "completed":
            return {
                "message": "Summary already exists",
                "summary": {
                    "id": str(latest_summary.id),
                    "video_id": str(latest_summary.video_id),
                    "summary": latest_summary.summary,
                    "key_points": latest_summary.key_points,
                    "topics": latest_summary.topics,
                    "status": latest_summary.status,
                    "model_name": latest_summary.model_name,
                    "language": latest_summary.language,
                },
            }

        response.status_code = 202

        return {
            "message": "Summarization is already in progress",
            "video_id": str(video_id),
            "language": language,
            "status": latest_summary.status if latest_summary else "pending",
        }

    # 5. Enqueue the language-specific Celery task.
    try:
        task = generate_video_summary.delay(
            video_id=str(video_id),
            owner_id=str(user.id),
            language=language,
        )

    except Exception as exc:
        logger.exception("Could not enqueue video summarization task.")

        update_video_summary_status(
            db=db,
            video_id=video_id,
            owner_id=user.id,
            status="failed",
            error_message="Could not enqueue summarization task.",
            language=language,
        )

        raise HTTPException(
            status_code=503,
            detail="Summarization service is temporarily unavailable.",
        ) from exc

    # 6. Return immediately.
    response.status_code = 202

    return {
        "message": "Video summarization job queued successfully",
        "video_id": str(video_id),
        "task_id": task.id,
        "language": language,
        "status": "pending",
    }


@video_router.get("/{video_id}/summary")
def get_video_summary_endpoint(
    video_id: uuid.UUID,
    language: str = Query(default=DEFAULT_LANGUAGE),
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    language = validate_output_language(language)
    # 1. Resolve authenticated user.
    user = get_or_create_user(db, clerk_user_id)

    # 2. Verify video ownership.
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == user.id,
        )
    )

    if video is None:
        raise HTTPException(
            status_code=404,
            detail="Video not found",
        )

    # 3. Fetch summary for the requested language.
    saved_summary = get_video_summary(
        db=db,
        video_id=video_id,
        owner_id=user.id,
        language=language,
    )

    if saved_summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"Summary not found in {language}. Please summarize the video first.",
        )

    return {
        "id": str(saved_summary.id),
        "video_id": str(saved_summary.video_id),
        "summary": saved_summary.summary,
        "key_points": saved_summary.key_points,
        "topics": saved_summary.topics,
        "status": saved_summary.status,
        "error_message": saved_summary.error_message,
        "model_name": saved_summary.model_name,
        "language": saved_summary.language,
    }


@video_router.get("/{video_id}/summary/pdf")
def download_video_summary_pdf(
    video_id: uuid.UUID,
    language: str = Query(default=DEFAULT_LANGUAGE),
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    # 1. Validate the requested output language.
    language = validate_output_language(language)

    # 2. Resolve authenticated user.
    user = get_or_create_user(db, clerk_user_id)

    # 3. Verify video ownership.
    video = db.scalar(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == user.id,
        )
    )

    if video is None:
        raise HTTPException(
            status_code=404,
            detail="Video not found",
        )

    # 4. Fetch the summary in the requested language.
    saved_summary = get_video_summary(
        db=db,
        video_id=video_id,
        owner_id=user.id,
        language=language,
    )

    if saved_summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"Summary not found in {language}. Please summarize the video first.",
        )

    # 5. Only completed summaries can be exported.
    if saved_summary.status != "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Summary is not ready for PDF export.",
                "status": saved_summary.status,
            },
        )

    # 6. Generate PDF.
    try:
        pdf_buffer = generate_summary_pdf(
            video=video,
            video_summary=saved_summary,
        )

    except Exception as exc:
        logger.exception("PDF generation failed.")

        raise HTTPException(
            status_code=500,
            detail="Could not generate the summary PDF.",
        ) from exc

    # 7. Return downloadable PDF.
    filename = (
        f"video-summary-{video_id}-{language.lower()}.pdf"
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )
    
def validate_output_language(language: str) -> str:
    language = language.strip()

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported output language.",
                "supported_languages": SUPPORTED_LANGUAGES,
            },
        )

    return language