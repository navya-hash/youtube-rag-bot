
import logging
from functools import lru_cache

from flashrank import Ranker, RerankRequest

logger = logging.getLogger(__name__)


class RerankingError(Exception):
    """Raised when reranking fails."""


@lru_cache(maxsize=1)
def get_ranker() -> Ranker:
    """
    Load and cache the FlashRank model.

    The model is downloaded on first use and reused
    for subsequent requests.
    """
    try:
        return Ranker(
            model_name="ms-marco-TinyBERT-L-2-v2",
            cache_dir="cache/flashrank",
        )
    except Exception as exc:
        logger.exception("Failed to initialize FlashRank.")
        raise RerankingError(
            "Unable to initialize the reranking model."
        ) from exc

def rerank_chunks(
    question: str,
    chunks: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Rerank retrieved transcript chunks by relevance
    to the user's question.
    """

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    if not 1 <= top_n <= 20:
        raise ValueError("top_n must be between 1 and 20.")

    if not chunks:
        return []

    try:
        ranker = get_ranker()

        passages = [
            {
                "id": index,
                "text": chunk.get("text", ""),
                "meta": chunk,
            }
            for index, chunk in enumerate(chunks)
            if chunk.get("text", "").strip()
        ]

        if not passages:
            return []

        rerank_request = RerankRequest(
            query=question,
            passages=passages,
        )

        results = ranker.rerank(rerank_request)

        # FlashRank returns results in descending relevance order.
        reranked_chunks = []

        for result in results[:top_n]:
            chunk = result["meta"]

            reranked_chunks.append({
                **chunk,
                "rerank_score": float(result["score"]),
            })

        return reranked_chunks

    except Exception as exc:
        logger.exception("Chunk reranking failed.")
        raise RerankingError(
            "Unable to rerank retrieved chunks."
        ) from exc
