import logging
import sys

from qdrant_client import models

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Video
from app.services.embeddings import embed_texts
from app.services.vector_store import (
    ensure_collection,
    get_qdrant_client,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YOUTUBE_VIDEO_ID = "Ty8gcCKuwNI"
LEGACY_COLLECTION = "youtube_transcripts"


def main():
    settings = get_settings()
    target_collection = settings.qdrant_multilingual_collection_name
    expected_dimension = settings.embedding_dimension

    logger.info("Target collection: %s", target_collection)
    logger.info("Configured embedding model: %s", settings.embedding_model)
    logger.info("Expected embedding dimension: %d", expected_dimension)

    db = SessionLocal()
    try:
        # 1. Fetch the existing video record from PostgreSQL
        video = (
            db.query(Video)
            .filter(Video.youtube_video_id == YOUTUBE_VIDEO_ID)
            .first()
        )

        if not video:
            logger.error("Video record for %s not found in database.", YOUTUBE_VIDEO_ID)
            sys.exit(1)

        logger.info(
            "Found video in database: id=%s, owner_id=%s, status=%s",
            video.id,
            video.owner_id,
            video.status,
        )

        # 2. Read existing chunks from legacy Qdrant collection
        client = get_qdrant_client()

        if not client.collection_exists(LEGACY_COLLECTION):
            logger.error("Legacy collection '%s' does not exist in Qdrant.", LEGACY_COLLECTION)
            sys.exit(1)

        scroll_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="owner_id",
                    match=models.MatchValue(value=str(video.owner_id)),
                ),
                models.FieldCondition(
                    key="video_id",
                    match=models.MatchValue(value=str(video.id)),
                ),
            ]
        )

        source_points = []
        offset = None

        while True:
            points, next_offset = client.scroll(
                collection_name=LEGACY_COLLECTION,
                scroll_filter=scroll_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            source_points.extend(points)
            if next_offset is None:
                break
            offset = next_offset

        if not source_points:
            logger.error(
                "No transcript chunks found in '%s' for video_id=%s.",
                LEGACY_COLLECTION,
                video.id,
            )
            sys.exit(1)

        # Sort chronologically by chunk_index
        source_points.sort(
            key=lambda p: (
                (p.payload or {}).get("chunk_index", 0),
                (p.payload or {}).get("start", 0),
            )
        )

        logger.info(
            "Retrieved %d source chunks from '%s'.",
            len(source_points),
            LEGACY_COLLECTION,
        )

        # 3. Extract texts and generate fresh multilingual embeddings
        texts = [(p.payload or {}).get("text", "") for p in source_points]
        if any(not text.strip() for text in texts):
            logger.error("One or more source chunks contain empty text.")
            sys.exit(1)

        logger.info("Generating multilingual embeddings for %d chunks...", len(texts))
        vectors = embed_texts(texts)

        if len(vectors) != len(source_points):
            logger.error(
                "Vector count mismatch: generated %d vectors for %d chunks.",
                len(vectors),
                len(source_points),
            )
            sys.exit(1)

        # 4. Verify embedding dimensions
        for idx, vector in enumerate(vectors):
            if len(vector) != expected_dimension:
                logger.error(
                    "Dimension mismatch at chunk %d: expected %d, got %d.",
                    idx,
                    expected_dimension,
                    len(vector),
                )
                sys.exit(1)

        logger.info(
            "All %d vectors verified with dimension %d.",
            len(vectors),
            expected_dimension,
        )

        # 5. Ensure the target collection and payload indexes exist
        logger.info("Ensuring target collection '%s' exists...", target_collection)
        ensure_collection(
            vector_size=expected_dimension,
            collection_name=target_collection,
        )

        # 6. Build points preserving original chunk IDs and complete payload metadata
        target_points = []
        for point, vector in zip(source_points, vectors):
            payload = dict(point.payload or {})
            target_points.append(
                models.PointStruct(
                    id=str(point.id),
                    vector=vector,
                    payload=payload,
                )
            )

        # 7. Upsert points into target collection (idempotent overwrite)
        logger.info(
            "Upserting %d points into '%s'...",
            len(target_points),
            target_collection,
        )
        client.upsert(
            collection_name=target_collection,
            points=target_points,
            wait=True,
        )

        # 8. Verify the final target collection count for this owner_id and video_id
        count_response = client.count(
            collection_name=target_collection,
            count_filter=scroll_filter,
            exact=True,
        )
        target_count = count_response.count

        # 9. Print clean summary
        print("\n" + "=" * 60)
        print("REPROCESS & RE-EMBEDDING SUMMARY")
        print("=" * 60)
        print(f"YouTube Video ID:           {YOUTUBE_VIDEO_ID}")
        print(f"Database Video ID:          {video.id}")
        print(f"Owner ID:                   {video.owner_id}")
        print(f"Source Collection:          {LEGACY_COLLECTION}")
        print(f"Target Collection:          {target_collection}")
        print(f"Embedding Model:            {settings.embedding_model}")
        print(f"Embedding Dimension:        {expected_dimension}")
        print(f"Source Chunks Retrieved:    {len(source_points)}")
        print(f"Embeddings Generated:       {len(vectors)}")
        print(f"Points Upserted:            {len(target_points)}")
        print(f"Target Collection Count:    {target_count}")
        print("=" * 60)

        if target_count == len(source_points):
            print("SUCCESS: Video chunks successfully migrated to multilingual collection.")
        else:
            print(
                f"WARNING: Target count ({target_count}) does not match source count ({len(source_points)})."
            )

    except Exception:
        logger.exception("Reprocessing video failed unexpectedly.")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()

