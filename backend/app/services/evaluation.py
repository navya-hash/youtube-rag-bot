def calculate_precision_at_k(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    retrieved = retrieved_chunk_ids[:k]

    if not retrieved:
        return 0.0

    relevant_retrieved = sum(
        1 for chunk_id in retrieved
        if chunk_id in relevant_chunk_ids
    )

    return relevant_retrieved / k


def calculate_recall_at_k(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    if not relevant_chunk_ids:
        return 0.0

    retrieved = retrieved_chunk_ids[:k]

    relevant_retrieved = sum(
        1 for chunk_id in retrieved
        if chunk_id in relevant_chunk_ids
    )

    return relevant_retrieved / len(relevant_chunk_ids)