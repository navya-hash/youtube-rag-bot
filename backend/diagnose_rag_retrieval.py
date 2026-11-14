
import argparse
import json
import logging
from pathlib import Path
from statistics import mean
from uuid import UUID

from qdrant_client import models
from flashrank import RerankRequest

from app.db.session import SessionLocal
from app.models import Chat, ChatVideo, Video
from app.db.repository import list_chat_videos
from app.core.config import get_settings
from app.services.embeddings import embed_texts
from app.services.evaluation_dataset import load_evaluation_dataset
from app.services.reranking import get_ranker
from app.services.vector_store import get_qdrant_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CANDIDATE_K = 15
FINAL_K = 5

DEFAULT_DATASET = Path(
    "evaluation_dataset/english_rag_dataset.json"
)

DEFAULT_OUTPUT = Path(
    "rag_retrieval_diagnostics_english.json"
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Diagnose Qdrant retrieval and FlashRank reranking."
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def validate_sample(db, sample):
    """Validate chat, video association, and ownership."""

    chat = db.get(Chat, UUID(sample.chat_id))

    if not chat:
        raise ValueError(f"Chat not found: {sample.chat_id}")

    if not chat.owner_id:
        raise ValueError("Chat owner is missing.")

    video_id = UUID(sample.video_id)

    chat_video = (
        db.query(ChatVideo)
        .filter(
            ChatVideo.chat_id == chat.id,
            ChatVideo.video_id == video_id,
        )
        .first()
    )

    if not chat_video:
        raise ValueError(
            f"Video {sample.video_id} is not associated "
            f"with chat {sample.chat_id}"
        )

    video = db.get(Video, video_id)

    if not video or video.owner_id != chat.owner_id:
        raise ValueError(
            f"Video ownership validation failed: {sample.video_id}"
        )

    completed_videos = [
        item
        for item in list_chat_videos(db, chat)
        if item.status == "completed"
        and item.owner_id == chat.owner_id
    ]

    if not completed_videos:
        raise ValueError(
            f"No completed videos found for chat {chat.id}"
        )

    return chat, [item.id for item in completed_videos]


def retrieve_qdrant_candidates(
    question,
    owner_id,
    video_ids,
):
    """Retrieve the initial 15 candidates directly from Qdrant."""

    query_vector = embed_texts([question])[0]

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
        limit=CANDIDATE_K,
        with_payload=True,
    )

    return [
        {
            "chunk_id": str(point.id),
            "score": float(point.score),
            **(point.payload or {}),
        }
        for point in response.points
    ]


def rerank_all_candidates(question, candidates):
    """Run the production FlashRank model and retain all rankings."""

    passages = [
        {
            "id": index,
            "text": chunk.get("text", ""),
            "meta": chunk,
        }
        for index, chunk in enumerate(candidates)
        if chunk.get("text", "").strip()
    ]

    if not passages:
        return []

    ranker = get_ranker()

    request = RerankRequest(
        query=question,
        passages=passages,
    )

    results = ranker.rerank(request)

    reranked = []

    for rank, result in enumerate(results, start=1):
        chunk = result["meta"]

        reranked.append({
            **chunk,
            "rerank_score": float(result["score"]),
            "rerank_rank": rank,
        })

    return reranked


def summarize_sample(sample, candidates, reranked):
    """Compare Qdrant and FlashRank rankings with ground truth."""

    relevant_ids = set(sample.relevant_chunk_ids)

    candidate_ids = [
        chunk["chunk_id"] for chunk in candidates
    ]

    reranked_ids = [
        chunk["chunk_id"] for chunk in reranked
    ]

    candidate_relevant = set(candidate_ids) & relevant_ids
    final_ids = reranked_ids[:FINAL_K]
    final_relevant = set(final_ids) & relevant_ids

    candidate_ranks = {
        chunk_id: rank
        for rank, chunk_id in enumerate(candidate_ids, start=1)
    }

    reranked_ranks = {
        chunk_id: rank
        for rank, chunk_id in enumerate(reranked_ids, start=1)
    }

    candidate_lookup = {
        chunk["chunk_id"]: chunk for chunk in candidates
    }

    reranked_lookup = {
        chunk["chunk_id"]: chunk for chunk in reranked
    }

    relevant_chunk_analysis = []

    for chunk_id in sorted(relevant_ids):
        candidate = candidate_lookup.get(chunk_id)
        reranked_chunk = reranked_lookup.get(chunk_id)

        relevant_chunk_analysis.append({
            "chunk_id": chunk_id,
            "found_in_qdrant": candidate is not None,
            "qdrant_rank": candidate_ranks.get(chunk_id),
            "qdrant_score": (
                candidate["score"] if candidate else None
            ),
            "found_by_flashrank": reranked_chunk is not None,
            "flashrank_rank": reranked_ranks.get(chunk_id),
            "flashrank_score": (
                reranked_chunk["rerank_score"]
                if reranked_chunk else None
            ),
            "in_final_top_5": chunk_id in final_ids,
        })

    candidate_recall = (
        len(candidate_relevant) / len(relevant_ids)
        if relevant_ids else 0.0
    )

    final_recall = (
        len(final_relevant) / len(relevant_ids)
        if relevant_ids else 0.0
    )

    precision_at_5 = len(final_relevant) / FINAL_K

    def format_chunk(chunk, rank):
        return {
            "rank": rank,
            "chunk_id": chunk["chunk_id"],
            "qdrant_score": chunk.get("score"),
            "rerank_score": chunk.get("rerank_score"),
            "chunk_index": chunk.get("chunk_index"),
            "start": chunk.get("start"),
            "end": chunk.get("end"),
            "language": chunk.get("language"),
            "is_relevant": chunk["chunk_id"] in relevant_ids,
            "text_preview": chunk.get("text", "")[:250],
        }

    return {
        "question_id": sample.question_id,
        "question": sample.question,
        "relevant_chunk_count": len(relevant_ids),
        "qdrant_candidate_count": len(candidates),
        "flashrank_result_count": len(reranked),
        "candidate_recall_at_15": candidate_recall,
        "final_recall_at_5": final_recall,
        "final_precision_at_5": precision_at_5,
        "relevant_chunks": relevant_chunk_analysis,
        "qdrant_candidates": [
            format_chunk(chunk, rank)
            for rank, chunk in enumerate(candidates, start=1)
        ],
        "flashrank_rankings": [
            format_chunk(chunk, chunk["rerank_rank"])
            for chunk in reranked
        ],
        "final_top_5_ids": final_ids,
        "relevant_chunks_lost_after_reranking": [
            chunk_id
            for chunk_id in candidate_relevant
            if chunk_id not in final_ids
        ],
    }


def main():
    args = parse_arguments()

    samples = load_evaluation_dataset(args.dataset)

    logger.info("Loaded %d evaluation samples.", len(samples))
    logger.info("Qdrant candidate limit: %d", CANDIDATE_K)
    logger.info("Final result limit: %d", FINAL_K)

    db = SessionLocal()

    results = []

    try:
        for index, sample in enumerate(samples, start=1):
            logger.info(
                "[%d/%d] Diagnosing %s",
                index,
                len(samples),
                sample.question_id,
            )

            try:
                chat, video_ids = validate_sample(db, sample)

                candidates = retrieve_qdrant_candidates(
                    question=sample.question,
                    owner_id=chat.owner_id,
                    video_ids=video_ids,
                )

                reranked = rerank_all_candidates(
                    question=sample.question,
                    candidates=candidates,
                )

                result = summarize_sample(
                    sample=sample,
                    candidates=candidates,
                    reranked=reranked,
                )

                results.append(result)

                logger.info(
                    "%s | Candidate Recall@15: %.3f | "
                    "Final Recall@5: %.3f | Precision@5: %.3f",
                    sample.question_id,
                    result["candidate_recall_at_15"],
                    result["final_recall_at_5"],
                    result["final_precision_at_5"],
                )

            except Exception:
                logger.exception(
                    "Diagnostic failed for %s",
                    sample.question_id,
                )
                raise

    finally:
        db.close()

    report = {
        "total_samples": len(results),
        "candidate_k": CANDIDATE_K,
        "final_k": FINAL_K,
        "average_metrics": {
            "candidate_recall_at_15": mean(
                r["candidate_recall_at_15"] for r in results
            ),
            "final_recall_at_5": mean(
                r["final_recall_at_5"] for r in results
            ),
            "final_precision_at_5": mean(
                r["final_precision_at_5"] for r in results
            ),
        },
        "results": results,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Diagnostic report saved to: %s", args.output)

    print("\n" + "=" * 60)
    print("RETRIEVAL DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Samples: {report['total_samples']}")
    print(
        "Average Candidate Recall@15: "
        f"{report['average_metrics']['candidate_recall_at_15']:.4f}"
    )
    print(
        "Average Final Recall@5: "
        f"{report['average_metrics']['final_recall_at_5']:.4f}"
    )
    print(
        "Average Final Precision@5: "
        f"{report['average_metrics']['final_precision_at_5']:.4f}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
