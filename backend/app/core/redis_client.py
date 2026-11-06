
import logging
from functools import lru_cache

from redis import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """
    Create and reuse a Redis client for application caching.

    Uses the existing Redis URL configured for Celery.
    """
    settings = get_settings()

    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )

# Why separate this from Celery?
# - Both use the same Redis server.
# - Each has its own connection pool.
# - Celery task queues and cache keys remain independent.
# - @lru_cache ensures we reuse the same Redis client within each process.