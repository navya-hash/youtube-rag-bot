

import hashlib
import json
import logging
from functools import lru_cache

from fastembed import TextEmbedding
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

EMBEDDING_CACHE_PREFIX = "youtube_rag:embedding:v1"
EMBEDDING_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


class EmbeddingServiceError(Exception):
    """Raised when local embedding generation fails."""


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    """Load and cache the model once per process."""
    settings = get_settings()

    try:
        return TextEmbedding(model_name=settings.embedding_model)
    except Exception as exc:
        logger.exception("Failed to initialize the embedding model.")
        raise EmbeddingServiceError(
            "Could not initialize the local embedding model."
        ) from exc


def _embedding_cache_key(text: str, model_name: str) -> str:
    """Create a deterministic Redis key for an embedding."""
    content = f"{model_name}:{text}"

    digest = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    return f"{EMBEDDING_CACHE_PREFIX}:{digest}"


def _get_cached_embedding(cache_key: str) -> list[float] | None:
    """Retrieve an embedding from Redis."""
    try:
        redis_client = get_redis_client()
        cached_value = redis_client.get(cache_key)

        if cached_value is None:
            return None

        embedding = json.loads(cached_value)

        if not isinstance(embedding, list) or not all(
            isinstance(value, (int, float)) for value in embedding
        ):
            logger.warning("Invalid embedding cache entry: %s", cache_key)
            redis_client.delete(cache_key)
            return None

        return [float(value) for value in embedding]

    except (RedisError, ValueError, TypeError):
        logger.warning(
            "Embedding cache read failed. Falling back to FastEmbed.",
            exc_info=True,
        )
        return None


def _cache_embedding(cache_key: str, embedding: list[float]) -> None:
    """Store an embedding in Redis."""
    try:
        redis_client = get_redis_client()

        redis_client.set(
            cache_key,
            json.dumps(embedding),
            ex=EMBEDDING_CACHE_TTL,
        )

    except (RedisError, TypeError, ValueError):
        logger.warning(
            "Embedding cache write failed. Continuing without cache.",
            exc_info=True,
        )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using FastEmbed with Redis result caching.

    Preserves input order and falls back to local embedding generation
    whenever Redis is unavailable.
    """
    cleaned_texts = [text.strip() for text in texts]

    if not cleaned_texts:
        return []

    if any(not text for text in cleaned_texts):
        raise ValueError("Embedding inputs cannot contain empty text.")

    settings = get_settings()
    model_name = settings.embedding_model

    results: list[list[float] | None] = [None] * len(cleaned_texts)
    missing_indices: list[int] = []
    missing_texts: list[str] = []
    missing_keys: list[str] = []

    # 1. Look up each embedding in Redis.
    for index, text in enumerate(cleaned_texts):
        cache_key = _embedding_cache_key(text, model_name)
        cached_embedding = _get_cached_embedding(cache_key)

        if cached_embedding is not None:
            results[index] = cached_embedding
        else:
            missing_indices.append(index)
            missing_texts.append(text)
            missing_keys.append(cache_key)

    # 2. Generate only missing embeddings.
    if missing_texts:
        try:
            model = get_embedding_model()
            embeddings = model.embed(missing_texts)

            generated_vectors = [
                vector.tolist() for vector in embeddings
            ]

            if len(generated_vectors) != len(missing_texts):
                raise EmbeddingServiceError(
                    "Embedding model returned an unexpected number of vectors."
                )

            # 3. Store generated embeddings in Redis.
            for index, cache_key, vector in zip(
                missing_indices,
                missing_keys,
                generated_vectors,
            ):
                results[index] = vector
                _cache_embedding(cache_key, vector)

        except EmbeddingServiceError:
            raise

        except Exception as exc:
            logger.exception("Local embedding generation failed.")
            raise EmbeddingServiceError(
                "Could not generate local text embeddings."
            ) from exc

    logger.info(
        "Embedding request completed: %d total, %d cache hits, %d generated.",
        len(cleaned_texts),
        len(cleaned_texts) - len(missing_texts),
        len(missing_texts),
    )

    return [vector for vector in results if vector is not None]


#  import logging
# from functools import lru_cache

# from fastembed import TextEmbedding

# from app.core.config import get_settings

# logger = logging.getLogger(__name__)


# class EmbeddingServiceError(Exception):
#     """Raised when local embedding generation fails."""

# # lru_cache(maxsize=1) ensures the model is loaded only once per process.
# @lru_cache(maxsize=1)
# def get_embedding_model() -> TextEmbedding:
#     """Load and cache the embedding model once per process."""
#     settings = get_settings()

#     try:
#         return TextEmbedding(model_name=settings.embedding_model)
#     except Exception as exc:
#         logger.exception("Failed to initialize the embedding model.")
#         raise EmbeddingServiceError(
#             "Could not initialize the local embedding model."
#         ) from exc


# def embed_texts(texts: list[str]) -> list[list[float]]:
#     """
#     Generate local embeddings while preserving input order.
#     No external embedding API call is required.
#     """
#     cleaned_texts = [text.strip() for text in texts]

#     if not cleaned_texts:
#         return []

#     if any(not text for text in cleaned_texts):
#         raise ValueError("Embedding inputs cannot contain empty text.")

#     try:
#         model = get_embedding_model()
#         embeddings = model.embed(cleaned_texts)

#         vectors = [vector.tolist() for vector in embeddings]

#         if len(vectors) != len(cleaned_texts):
#             raise EmbeddingServiceError(
#                 "Embedding model returned an unexpected number of vectors."
#             )

#         return vectors

#     except EmbeddingServiceError:
#         raise
#     except Exception as exc:
#         logger.exception("Local embedding generation failed.")
#         raise EmbeddingServiceError(
#             "Could not generate local text embeddings."
#         ) from exc

