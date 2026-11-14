
from functools import lru_cache
from uuid import UUID

from qdrant_client import QdrantClient, models

from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()

    if not settings.qdrant_url:
        raise RuntimeError("QDRANT_URL is not configured.")

    if not settings.qdrant_api_key:
        raise RuntimeError("QDRANT_API_KEY is not configured.")

    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=30,
    )

def ensure_payload_indexes(collection_name: str | None = None) -> None:
    """
    Create payload indexes required for secure filtered searches.
    """
    settings = get_settings()
    client = get_qdrant_client()
    target_collection = collection_name or settings.qdrant_collection_name

    for field_name in ("owner_id", "video_id"):
        client.create_payload_index(
            collection_name=target_collection,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        )

def ensure_collection(
    vector_size: int | None = None,
    collection_name: str | None = None,
) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    target_collection = collection_name or settings.qdrant_collection_name
    target_size = vector_size if vector_size is not None else settings.embedding_dimension

    if client.collection_exists(target_collection):
        info = client.get_collection(target_collection)
        existing_size = info.config.params.vectors.size

        if existing_size != target_size:
            raise RuntimeError(
                f"Collection '{target_collection}' uses vector size "
                f"{existing_size}, but the embedding model produces "
                f"{target_size}. Use a new collection or migrate it."
            )
    else:
        client.create_collection(
            collection_name=target_collection,
            vectors_config=models.VectorParams(
                size=target_size,
                distance=models.Distance.COSINE,
            ),
        )

    # Create indexes for filtered retrieval.
    ensure_payload_indexes(collection_name=target_collection)




def upsert_chunks(
    chunks: list[dict],
    vectors: list[list[float]],
    owner_id: UUID,
) -> int:
    """
    Store transcript chunks and their embeddings in Qdrant.

    Each point is associated with an application user and
    an internal Neon video record.
    """
    if len(chunks) != len(vectors):
        raise ValueError(
            "The number of chunks must match the number of vectors."
        )

    if not chunks:
        return 0

    settings = get_settings()
    client = get_qdrant_client()

    points = []

    for chunk, vector in zip(chunks, vectors):
        if not vector:
            raise ValueError("Embedding vectors cannot be empty.")

        if not chunk.get("chunk_id"):
            raise ValueError("Every chunk must have a chunk_id.")

        if not chunk.get("video_id"):
            raise ValueError("Every chunk must have an internal video_id.")

        if not chunk.get("youtube_video_id"):
            raise ValueError("Every chunk must have a youtube_video_id.")

        points.append(
            models.PointStruct(
                id=chunk["chunk_id"],
                vector=vector,
                payload={
                    "owner_id": str(owner_id),
                    "video_id": str(chunk["video_id"]),
                    "youtube_video_id": chunk["youtube_video_id"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "duration": chunk["duration"],
                    "language": chunk["language"],
                    "is_generated": chunk["is_generated"],
                },
            )
        )

    client.upsert(
        collection_name=settings.qdrant_collection_name,
        points=points,
        wait=True,
    )

    return len(points)


def delete_video_chunks(
    owner_id: UUID,
    video_id: UUID,
) -> None:
    """
    Delete all transcript chunks for one video belonging
    to the specified owner.
    """

    settings = get_settings()
    client = get_qdrant_client()

    delete_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=str(owner_id)),
            ),
            models.FieldCondition(
                key="video_id",
                match=models.MatchValue(value=str(video_id)),
            ),
        ]
    )

    try:
        client.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=models.FilterSelector(
                filter=delete_filter,
            ),
            wait=True,
        )

        logger.info(
            "Deleted Qdrant chunks for video_id=%s, owner_id=%s.",
            video_id,
            owner_id,
        )

    except Exception as exc:
        logger.exception(
            "Failed to delete Qdrant chunks for video_id=%s.",
            video_id,
        )
        raise RuntimeError(
            "Unable to delete existing video chunks."
        ) from exc


def delete_obsolete_video_chunks(
    owner_id: UUID,
    video_id: UUID,
    keep_chunk_ids: list[str],
) -> int:
    """
    Delete obsolete transcript chunks while preserving
    the newly uploaded chunk IDs for this video and owner.
    """

    settings = get_settings()
    client = get_qdrant_client()

    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=str(owner_id)),
            ),
            models.FieldCondition(
                key="video_id",
                match=models.MatchValue(value=str(video_id)),
            ),
        ]
    )

    keep_ids = {str(chunk_id) for chunk_id in keep_chunk_ids}
    obsolete_ids = []
    offset = None

    try:
        # Find every existing chunk belonging to this video.
        while True:
            points, next_offset = client.scroll(
                collection_name=settings.qdrant_collection_name,
                scroll_filter=scroll_filter,
                limit=256,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            for point in points:
                if str(point.id) not in keep_ids:
                    obsolete_ids.append(point.id)

            if next_offset is None:
                break

            offset = next_offset

        # Delete obsolete points in batches.
        for start in range(0, len(obsolete_ids), 1000):
            batch = obsolete_ids[start:start + 1000]

            client.delete(
                collection_name=settings.qdrant_collection_name,
                points_selector=models.PointIdsList(
                    points=batch,
                ),
                wait=True,
            )

        logger.info(
            "Deleted %d obsolete chunks for video_id=%s.",
            len(obsolete_ids),
            video_id,
        )

        return len(obsolete_ids)

    except Exception as exc:
        logger.exception(
            "Failed to delete obsolete chunks for video_id=%s.",
            video_id,
        )
        raise RuntimeError(
            "Unable to remove obsolete transcript chunks."
        ) from exc  

def search_chunks(
    query_vector: list[float],
    owner_id: UUID,
    video_ids: list[UUID],
    limit: int = 5,
) -> list[dict]:
    """
    Search only the specified user's videos attached to a chat.
    """
    if not query_vector:
        raise ValueError("Query vector cannot be empty.")

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")

    if not video_ids:
        return []

    settings = get_settings()
    client = get_qdrant_client()

    search_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=str(owner_id)),
            ),
            models.FieldCondition(
                key="video_id",
                match=models.MatchAny(
                    any=[str(video_id) for video_id in video_ids]
                ),
            ),
        ]
    )

    response = client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_vector,
        query_filter=search_filter,
        limit=limit,
        with_payload=True,
    )

    return [
    {
        "chunk_id": str(point.id),
        "score": point.score,
        **(point.payload or {}),
    }
    for point in response.points
]


# get_all_video_chunks() bridges our Qdrant vector database and summarization pipeline by securely retrieving every transcript chunk of a selected video in chronological order.

def get_all_video_chunks(
    owner_id: UUID,
    video_id: UUID,
    batch_size: int = 256,
) -> list[dict]:
    """
    Fetch every transcript chunk for one video belonging
    to the specified owner.

    Uses Qdrant scroll pagination rather than vector search.
    Results are returned in chronological chunk order.
    """

    if not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be between 1 and 1000.")

    settings = get_settings()
    client = get_qdrant_client()

    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=str(owner_id)),
            ),
            models.FieldCondition(
                key="video_id",
                match=models.MatchValue(value=str(video_id)),
            ),
        ]
    )

    all_chunks = []
    offset = None

    try:
        while True:
            points, next_offset = client.scroll(
                collection_name=settings.qdrant_collection_name,
                scroll_filter=scroll_filter,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}

                all_chunks.append({
                    "chunk_id": str(point.id),
                    **payload,
                })

            if next_offset is None:
                break

            offset = next_offset

        # Qdrant scroll order is not guaranteed to match
        # the original transcript order.
        all_chunks.sort(
            key=lambda chunk: (
                chunk.get("chunk_index", 0),
                chunk.get("start", 0),
            )
        )

        logger.info(
            "Fetched %d transcript chunks for video %s.",
            len(all_chunks),
            video_id,
        )

        return all_chunks

    except Exception as exc:
        logger.exception(
            "Failed to fetch all transcript chunks for video %s.",
            video_id,
        )
        raise RuntimeError(
            "Unable to fetch the complete video transcript."
        ) from exc
