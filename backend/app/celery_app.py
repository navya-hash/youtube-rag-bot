
import os
import ssl
from celery import Celery
from kombu import Queue
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
REDIS_URL = settings.redis_url

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is missing from the environment.")

celery_app = Celery(
    "youtube_rag_bot",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.summary_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    timezone="UTC",
    enable_utc=True,

    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    broker_use_ssl={
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    },

    broker_transport_options={"visibility_timeout": 3600},
    result_backend_transport_options={"visibility_timeout": 3600},
    visibility_timeout=3600,

    task_default_queue="video_summarization",
    task_queues=(Queue("video_summarization"),),

    result_expires=3600,
    beat_schedule={
    "recover-stale-video-summaries-every-5-minutes": {
        "task": "app.tasks.summary_tasks.recover_stale_video_summaries",
        "schedule": crontab(minute="*/5"),
    },
},
)


# Why these settings?
# - task_acks_late=True: acknowledges a task after execution rather than immediately when received.
# - task_reject_on_worker_lost=True: allows a task to be re-queued if its worker process is lost.
# - worker_prefetch_multiplier=1: prevents a worker from reserving too many long-running jobs.
# - task_track_started=True: lets Celery track when a task begins.