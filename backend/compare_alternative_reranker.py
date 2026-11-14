
import json
import logging
from pathlib import Path

from flashrank import Ranker, RerankRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INPUT_FILE = Path("rag_retrieval_diagnostics_english.json")

TOP_K = 5
ALTERNATIVE_MODEL = "ms-marco-MiniLM-L-12-v2"
CACHE_DIR = "cache/flashrank_minilm"


def get_chunk_id(item):
    if isinstance(item, str):
        return item

    return item.get("chunk_id") or item.get("id")


def calculate_metrics(ranked_chunks, relevant_ids):
    retrieved_ids = {
        get_chunk_id(chunk)
        for chunk in ranked_chunks[:TOP_K]
    }

    hits = len(retrieved_ids & relevant_ids)

    precision = hits / TOP_K
    recall = hits / len(relevant_ids) if relevant_ids else 0.0

    return precision, recall



def rerank_with_alternative_model(ranker, question, candidates):
    if not candidates:
        raise ValueError(f"No candidates provided for question '{question}'.")

    passages = []

    for index, chunk in enumerate(candidates):
        chunk_id = get_chunk_id(chunk)
        if not chunk_id:
            raise ValueError(
                f"Candidate at index {index} is missing 'chunk_id' for question '{question}'."
            )

        # In rag_retrieval_diagnostics_english.json, transcript text is stored in 'text_preview'.
        text = chunk.get("text_preview") or chunk.get("text")
        if not text and "payload" in chunk and isinstance(chunk["payload"], dict):
            text = chunk["payload"].get("text") or chunk["payload"].get("text_preview")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Missing transcript text for candidate chunk '{chunk_id}' in question '{question}'. "
                f"Available candidate keys: {list(chunk.keys())}"
            )

        passages.append({
            "id": index,
            "text": text,
            "meta": chunk,
        })

    if not passages:
        raise ValueError(f"No valid passages found to rerank for question '{question}'.")

    request = RerankRequest(
        query=question,
        passages=passages,
    )

    results = ranker.rerank(request)

    if not results:
        raise ValueError(f"Alternative reranker returned 0 results for question '{question}'.")

    reranked = []
    for rank, result in enumerate(results, start=1):
        meta = result.get("meta") or {}
        chunk_id = get_chunk_id(meta)
        if not chunk_id:
            raise ValueError(
                f"Alternative reranker lost original chunk_id at rank {rank} for question '{question}'."
            )

        reranked.append({
            **meta,
            "rerank_score": float(result["score"]),
            "rerank_rank": rank,
        })

    if len(reranked) != len(candidates):
        raise ValueError(
            f"Reranker returned {len(reranked)} results, expected {len(candidates)}."
        )

    return reranked



def average(metrics, index):
    return sum(item[index] for item in metrics) / len(metrics)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Diagnostic file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        report = json.load(file)

    samples = report["results"]

    if not samples:
        raise ValueError("No evaluation samples found.")

    logger.info("Loading alternative model: %s", ALTERNATIVE_MODEL)

    ranker = Ranker(
        model_name=ALTERNATIVE_MODEL,
        cache_dir=CACHE_DIR,
    )

    qdrant_metrics = []
    current_flashrank_metrics = []
    alternative_metrics = []

    print(f"\nQuestions evaluated: {len(samples)}")
    print(f"Alternative model: {ALTERNATIVE_MODEL}")
    print(f"Top K: {TOP_K}\n")

    for sample in samples:
        question_id = sample["question_id"]
        question = sample["question"]

        relevant_ids = {
            get_chunk_id(item)
            for item in sample["relevant_chunks"]
        }

        qdrant_candidates = sample["qdrant_candidates"]

        qdrant_top5 = qdrant_candidates[:TOP_K]
        current_top5 = sample["flashrank_rankings"][:TOP_K]

        alternative_rankings = rerank_with_alternative_model(
            ranker,
            question,
            qdrant_candidates,
        )
        alternative_top5 = alternative_rankings[:TOP_K]

        # Debug the first question's returned metadata and IDs.
        if question_id == "q1":
            print("\n--- DEBUG: ALTERNATIVE RERANKER ---")

            print("Relevant IDs:")
            print([
                get_chunk_id(item)
                for item in sample["relevant_chunks"]
            ])

            print("\nFirst Qdrant candidate ID:")
            print(get_chunk_id(qdrant_candidates[0]))

            print("\nFirst alternative result:")
            print({
                "keys": list(alternative_top5[0].keys())
                if alternative_top5 else [],
                "chunk_id": get_chunk_id(alternative_top5[0])
                if alternative_top5 else None,
                "rerank_score": alternative_top5[0].get("rerank_score")
                if alternative_top5 else None,
            })

            print("\nFirst alternative result metadata:")
            if alternative_top5:
                print(alternative_top5[0])

            print("--- END DEBUG ---\n")

        q_p, q_r = calculate_metrics(
            qdrant_top5, relevant_ids
        )

        current_p, current_r = calculate_metrics(
            current_top5, relevant_ids
        )

        alt_p, alt_r = calculate_metrics(
            alternative_top5, relevant_ids
        )

        qdrant_metrics.append((q_p, q_r))
        current_flashrank_metrics.append((current_p, current_r))
        alternative_metrics.append((alt_p, alt_r))

        print(
            f"{question_id}: "
            f"Qdrant P={q_p:.2f}, R={q_r:.2f} | "
            f"Current FlashRank P={current_p:.2f}, R={current_r:.2f} | "
            f"Alternative P={alt_p:.2f}, R={alt_r:.2f}"
        )

    print("\n" + "=" * 75)
    print("FINAL RETRIEVAL COMPARISON")
    print("=" * 75)

    methods = [
        ("Qdrant-only", qdrant_metrics),
        ("Qdrant + Current FlashRank", current_flashrank_metrics),
        ("Qdrant + Alternative FlashRank", alternative_metrics),
    ]

    for name, metrics in methods:
        print(f"\n{name}")
        print(f"Average Precision@{TOP_K}: {average(metrics, 0):.4f}")
        print(f"Average Recall@{TOP_K}:    {average(metrics, 1):.4f}")

    print("\nAlternative model change vs current FlashRank:")
    print(
        "Precision: "
        f"{average(alternative_metrics, 0) - average(current_flashrank_metrics, 0):+.4f}"
    )
    print(
        "Recall:    "
        f"{average(alternative_metrics, 1) - average(current_flashrank_metrics, 1):+.4f}"
    )


if __name__ == "__main__":
    main()
