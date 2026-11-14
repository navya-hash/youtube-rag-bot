
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Chat
from app.db.repository import list_chat_videos
from app.services.embeddings import embed_texts
from app.services.vector_store import search_chunks
from app.services.reranking import rerank_chunks

import hashlib
import json
from redis.exceptions import RedisError
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

RETRIEVAL_CACHE_PREFIX = "youtube_rag:retrieval:v2"
RETRIEVAL_CACHE_TTL = 60 * 15  # 15 minutes


def _retrieval_cache_key(
    owner_id: UUID,
    chat_id: UUID,
    video_ids: list[UUID],
    video_versions: dict[str, int],
    question: str,
    limit: int,
) -> str:
    """Generate a deterministic key for a retrieval request."""

    cache_data = {
        "owner_id": str(owner_id),
        "chat_id": str(chat_id),
        "video_ids": sorted(str(video_id) for video_id in video_ids),
        "video_versions": video_versions,
        "question": " ".join(question.casefold().split()),
        "limit": limit,
    }

    serialized = json.dumps(
        cache_data,
        sort_keys=True,
        ensure_ascii=False,
    )

    digest = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    return f"{RETRIEVAL_CACHE_PREFIX}:{digest}"


def _get_cached_chunks(cache_key: str) -> list[dict] | None:
    """Retrieve reranked chunks from Redis."""

    try:
        redis_client = get_redis_client()
        cached_value = redis_client.get(cache_key)

        if cached_value is None:
            return None

        chunks = json.loads(cached_value)

        if not isinstance(chunks, list) or not all(
            isinstance(chunk, dict) for chunk in chunks
        ):
            logger.warning("Invalid retrieval cache entry.")
            redis_client.delete(cache_key)
            return None

        return chunks

    except (RedisError, ValueError, TypeError):
        logger.warning(
            "Retrieval cache read failed. Running normal retrieval.",
            exc_info=True,
        )
        return None


def _cache_chunks(
    cache_key: str,
    chunks: list[dict],
    owner_id: UUID,
    video_ids: list[UUID],
) -> None:
    """
    Cache retrieval results and register their video dependencies.
    """

    try:
        redis_client = get_redis_client()

        pipeline = redis_client.pipeline()

        pipeline.set(
            cache_key,
            json.dumps(chunks, ensure_ascii=False),
            ex=RETRIEVAL_CACHE_TTL,
        )

        for video_id in video_ids:
            dependency_key = _retrieval_video_dependency_key(
                owner_id=owner_id,
                video_id=video_id,
            )

            pipeline.sadd(dependency_key, cache_key)

            pipeline.expire(
                dependency_key,
                RETRIEVAL_CACHE_TTL,
            )

        pipeline.execute()

    except (RedisError, TypeError, ValueError):
        logger.warning(
            "Retrieval cache write failed. Continuing without cache.",
            exc_info=True,
        )



def _retrieval_video_dependency_key(
    owner_id: UUID,
    video_id: UUID,
) -> str:
    return (
        f"{RETRIEVAL_CACHE_PREFIX}:"
        f"dependencies:{owner_id}:{video_id}"
    )


def invalidate_retrieval_cache_for_video(
    owner_id: UUID,
    video_id: UUID,
) -> None:
    """
    Invalidate every retrieval cache entry that depends
    on this owner's specified video.
    """

    try:
        redis_client = get_redis_client()

        dependency_key = _retrieval_video_dependency_key(
            owner_id=owner_id,
            video_id=video_id,
        )

        cache_keys = redis_client.smembers(dependency_key)

        if cache_keys:
            redis_client.delete(*cache_keys)

        redis_client.delete(dependency_key)

        logger.info(
            "Invalidated %d retrieval cache entries for video %s.",
            len(cache_keys),
            video_id,
        )

    except RedisError:
        logger.warning(
            "Retrieval cache invalidation failed for video %s.",
            video_id,
            exc_info=True,
        )



class RetrievalError(Exception):
    """Raised when relevant chunk retrieval fails."""


def retrieve_relevant_chunks(
    db: Session,
    chat: Chat,
    owner_id: UUID,
    question: str,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve candidate chunks from Qdrant and rerank them
    using FlashRank.

    Returns the most relevant transcript chunks.
    """

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20.")

    if chat.owner_id != owner_id:
        raise ValueError("Chat does not belong to this user.")

    try:
        # 1. Get videos associated with this chat.
        chat_videos = list_chat_videos(db, chat)

        completed_videos = [
            video
            for video in chat_videos
            if video.status == "completed"
            and video.owner_id == owner_id
        ]

        if not completed_videos:
            return []

        video_ids = [video.id for video in completed_videos]

        video_versions = {
    str(video.id): video.content_version
    for video in completed_videos
}

        # 2. Check whether the final retrieval result is cached.
        cache_key = _retrieval_cache_key(
    owner_id=owner_id,
    chat_id=chat.id,
    video_ids=video_ids,
    video_versions=video_versions,
    question=question,
    limit=limit,
)

        cached_chunks = _get_cached_chunks(cache_key)

        if cached_chunks is not None:
            logger.info(
                "Retrieval cache HIT for chat %s.",
                chat.id,
            )
            return cached_chunks

        logger.info(
            "Retrieval cache MISS for chat %s.",
            chat.id,
        )

        # 2. Convert the question into an embedding.
        query_vector = embed_texts([question])[0]

        # 3. Retrieve more candidates from Qdrant.
        candidate_chunks = search_chunks(
            query_vector=query_vector,
            owner_id=owner_id,
            video_ids=video_ids,
            limit=15,
        )

        if not candidate_chunks:
            return []

        # 4. Attach video metadata to retrieved chunks.
        video_lookup = {
            str(video.id): video
            for video in completed_videos
        }

        enriched_chunks = []

        for chunk in candidate_chunks:
            video = video_lookup.get(chunk.get("video_id"))

            if video is None:
                continue

            enriched_chunks.append({
                **chunk,
                "video_title": video.title,
                "youtube_video_id": video.youtube_video_id,
            })

        if not enriched_chunks:
            return []

        # 5. Rerank candidates using FlashRank.
        final_chunks = rerank_chunks(
            question=question,
            chunks=enriched_chunks,
            top_n=limit,
        )

        # 6. Cache the final reranked results.
        _cache_chunks(
    cache_key=cache_key,
    chunks=final_chunks,
    owner_id=owner_id,
    video_ids=video_ids,
)

        logger.info(
            "Retrieved %d candidates and selected %d reranked chunks.",
            len(enriched_chunks),
            len(final_chunks),
        )

        return final_chunks

    except Exception as exc:
        logger.exception(
            "Relevant chunk retrieval and reranking failed."
        )
        raise RetrievalError(
            "Unable to retrieve relevant video context."
        ) from exc



