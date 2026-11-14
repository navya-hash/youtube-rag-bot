
import json
from pathlib import Path

DIAGNOSTICS_FILE = Path("rag_retrieval_diagnostics_english.json")
K = 5


def get_chunk_id(item):
    if isinstance(item, str):
        return item
    return item.get("chunk_id") or item.get("id")


def calculate_metrics(retrieved, relevant):
    retrieved_ids = {
        get_chunk_id(item)
        for item in retrieved[:K]
    }
    hits = len(retrieved_ids & relevant)

    precision = hits / K
    recall = hits / len(relevant) if relevant else 0.0

    return precision, recall


def main():
    with DIAGNOSTICS_FILE.open("r", encoding="utf-8") as file:
        report = json.load(file)

    results = report["results"]

    qdrant_metrics = []
    flashrank_metrics = []

    print(f"Questions evaluated: {len(results)}")
    print(f"Comparing top {K} chunks\n")

    for sample in results:
        relevant = {
            get_chunk_id(item)
            for item in sample["relevant_chunks"]
        }

        qdrant_p, qdrant_r = calculate_metrics(
            sample["qdrant_candidates"], relevant
        )

        flashrank_p, flashrank_r = calculate_metrics(
            sample["flashrank_rankings"], relevant
        )

        qdrant_metrics.append((qdrant_p, qdrant_r))
        flashrank_metrics.append((flashrank_p, flashrank_r))

        print(
            f'{sample["question_id"]}: '
            f'Qdrant P={qdrant_p:.2f}, R={qdrant_r:.2f} | '
            f'FlashRank P={flashrank_p:.2f}, R={flashrank_r:.2f}'
        )

    def average(metrics, index):
        return sum(item[index] for item in metrics) / len(metrics)

    print("\n" + "=" * 60)
    print("FINAL COMPARISON")
    print("=" * 60)

    for name, metrics in [
        ("Qdrant-only", qdrant_metrics),
        ("Qdrant + FlashRank", flashrank_metrics),
    ]:
        print(f"\n{name}")
        print(f"Average Precision@{K}: {average(metrics, 0):.4f}")
        print(f"Average Recall@{K}:    {average(metrics, 1):.4f}")

    print("\nFlashRank change:")
    print(
        "Precision: "
        f"{average(flashrank_metrics, 0) - average(qdrant_metrics, 0):+.4f}"
    )
    print(
        "Recall:    "
        f"{average(flashrank_metrics, 1) - average(qdrant_metrics, 1):+.4f}"
    )


if __name__ == "__main__":
    main()
