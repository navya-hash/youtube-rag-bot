import logging
import uuid

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.repository import (
    update_video_summary_status,
    reclaim_stale_video_summary_jobs,
)
from app.services.summary_worker import process_video_summary

logger = logging.getLogger(__name__)


def mark_summary_failed(
    video_id: str,
    owner_id: str,
    language: str,
    error_message: str,
) -> None:
    db = SessionLocal()

    try:
        update_video_summary_status(
            db=db,
            video_id=uuid.UUID(video_id),
            owner_id=uuid.UUID(owner_id),
            status="failed",
            error_message=error_message[:2000],
            language=language,
        )
    except Exception:
        logger.exception(
            "Failed to mark summary as failed for video %s",
            video_id,
        )
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.summary_tasks.generate_video_summary",
    max_retries=3,
    default_retry_delay=30,
)
def generate_video_summary(
    self,
    video_id: str,
    owner_id: str,
    language: str = "English",
):
    try:
        result = process_video_summary(
            video_id=uuid.UUID(video_id),
            owner_id=uuid.UUID(owner_id),
            language=language,
        )

        return {
            "video_id": video_id,
            "status": "completed",
            "summary_id": result.get("summary_id"),
            "language": language,
        }

    except Exception as exc:
        logger.exception(
            "Video summarization failed for video %s in %s",
            video_id,
            language,
        )

        if self.request.retries >= self.max_retries:
            mark_summary_failed(
                video_id=video_id,
                owner_id=owner_id,
                language=language,
                error_message=str(exc),
            )
            raise

        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.summary_tasks.recover_stale_video_summaries"
)
def recover_stale_video_summaries():
    db = SessionLocal()

    try:
        recovered_jobs = reclaim_stale_video_summary_jobs(
            db=db,
            stale_after_minutes=10,
        )

        queued_count = 0

        # Each recovered job now includes its language.
        for video_id, owner_id, language in recovered_jobs:
            try:
                generate_video_summary.delay(
                    video_id=str(video_id),
                    owner_id=str(owner_id),
                    language=language,
                )
                queued_count += 1

            except Exception as exc:
                logger.exception(
                    "Failed to requeue stale summary for video %s",
                    video_id,
                )

                try:
                    update_video_summary_status(
                        db=db,
                        video_id=video_id,
                        owner_id=owner_id,
                        status="failed",
                        error_message=(
                            f"Failed to requeue stale job: {str(exc)}"
                        )[:2000],
                        language=language,
                    )
                except Exception:
                    db.rollback()
                    logger.exception(
                        "Failed to update status for stale video %s",
                        video_id,
                    )

        logger.info(
            "Recovered %s stale jobs and requeued %s",
            len(recovered_jobs),
            queued_count,
        )

        return {
            "recovered": len(recovered_jobs),
            "requeued": queued_count,
        }

    finally:
        db.close()
# import logging
# import uuid

# from app.celery_app import celery_app
# from app.db.session import SessionLocal
# from app.db.repository import update_video_summary_status
# from app.services.summary_worker import process_video_summary
# from app.db.repository import reclaim_stale_video_summary_jobs

# logger = logging.getLogger(__name__)


# def mark_summary_failed(
#     video_id: str,
#     owner_id: str,
#     error_message: str,
# ) -> None:
#     """Mark a summary as failed after all Celery retries are exhausted."""

#     db = SessionLocal()

#     try:
#         update_video_summary_status(
#             db=db,
#             video_id=uuid.UUID(video_id),
#             owner_id=uuid.UUID(owner_id),
#             status="failed",
#             error_message=error_message[:2000],
#         )
#     except Exception:
#         logger.exception(
#             "Could not mark video summary as failed: %s",
#             video_id,
#         )
#     finally:
#         db.close()


# @celery_app.task(
#     bind=True,
#     name="app.tasks.summary_tasks.generate_video_summary",
#     max_retries=3,
#     default_retry_delay=30,
# )
# def generate_video_summary(
#     self,
#     video_id: str,
#     owner_id: str,
# ):
#     try:
#         result = process_video_summary(
#             video_id=uuid.UUID(video_id),
#             owner_id=uuid.UUID(owner_id),
#         )

#         return {
#             "video_id": video_id,
#             "status": "completed",
#             "summary_id": result.get("summary_id"),
#         }

#     except Exception as exc:
#         logger.exception(
#             "Celery summarization attempt failed for video %s. Retry: %s/%s",
#             video_id,
#             self.request.retries,
#             self.max_retries,
#         )

#         # All retries have been exhausted.
#         if self.request.retries >= self.max_retries:
#             mark_summary_failed(
#                 video_id=video_id,
#                 owner_id=owner_id,
#                 error_message=str(exc),
#             )
#             raise

#         # Retry after the configured delay.
#         raise self.retry(exc=exc)


# @celery_app.task(
#     name="app.tasks.summary_tasks.recover_stale_video_summaries",
# )
# def recover_stale_video_summaries():
#     """
#     Find stale summarization jobs and enqueue them again.
#     """

#     db = SessionLocal()

#     try:
#         recovered_jobs = reclaim_stale_video_summary_jobs(
#             db=db,
#             stale_after_minutes=10,
#         )

#         queued_count = 0

#         for video_id, owner_id in recovered_jobs:
#             try:
#                 generate_video_summary.delay(
#                     video_id=str(video_id),
#                     owner_id=str(owner_id),
#                 )

#                 queued_count += 1

#             except Exception as exc:
#                 logger.exception(
#                     "Failed to requeue stale summary job for video %s",
#                     video_id,
#                 )

#                 try:
#                     update_video_summary_status(
#                         db=db,
#                         video_id=video_id,
#                         owner_id=owner_id,
#                         status="failed",
#                         error_message=f"Failed to requeue stale job: {str(exc)}"[:2000],
#                     )
#                 except Exception:
#                     db.rollback()
#                     logger.exception(
#                         "Could not mark stale summary job as failed: %s",
#                         video_id,
#                     )







            










#         logger.info(
#             "Stale summary recovery finished. Requeued %s jobs.",
#             queued_count,
#         )

#         return {
#             "recovered": len(recovered_jobs),
#             "requeued": queued_count,
#         }

#     finally:
#         db.close()

