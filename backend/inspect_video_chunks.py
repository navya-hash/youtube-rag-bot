# from qdrant_client import models

# from app.services.vector_store import get_qdrant_client

# COLLECTION_NAME = "youtube_transcripts_multilingual"
# VIDEO_ID = "14d55b3a-b145-42e8-8d5e-0485bfffb348"
# OWNER_ID = "d3e52b69-1d19-4f1e-a532-6be37820d6e7"


# def main():
#     client = get_qdrant_client()

#     if not client.collection_exists(COLLECTION_NAME):
#         print(f"Error: Collection '{COLLECTION_NAME}' does not exist in Qdrant.")
#         return

#     # Filter strictly by owner_id and video_id
#     scroll_filter = models.Filter(
#         must=[
#             models.FieldCondition(
#                 key="owner_id",
#                 match=models.MatchValue(value=OWNER_ID),
#             ),
#             models.FieldCondition(
#                 key="video_id",
#                 match=models.MatchValue(value=VIDEO_ID),
#             ),
#         ]
#     )

#     all_chunks = []
#     offset = None

#     # Paginated Qdrant scrolling
#     while True:
#         points, next_offset = client.scroll(
#             collection_name=COLLECTION_NAME,
#             scroll_filter=scroll_filter,
#             limit=100,
#             offset=offset,
#             with_payload=True,
#             with_vectors=False,
#         )

#         for point in points:
#             payload = point.payload or {}
#             all_chunks.append({
#                 "chunk_id": str(point.id),
#                 **payload,
#             })

#         if next_offset is None:
#             break
#         offset = next_offset

#     # Order strictly by chunk_index
#     all_chunks.sort(
#         key=lambda chunk: (
#             chunk.get("chunk_index", 0),
#             chunk.get("start", 0),
#         )
#     )

#     print("=" * 80)
#     print(f"COLLECTION:             {COLLECTION_NAME}")
#     print(f"VIDEO ID:               {VIDEO_ID}")
#     print(f"OWNER ID:               {OWNER_ID}")
#     print(f"TOTAL CHUNKS RETRIEVED: {len(all_chunks)}")
#     print("=" * 80)

#     if not all_chunks:
#         print("No chunks found in this collection for the specified video and owner.")
#         return

#     for index, chunk in enumerate(all_chunks, start=1):
#         print(f"\n--- Chunk {index} (Index: {chunk.get('chunk_index')}) ---")
#         print(f"Chunk ID:        {chunk.get('chunk_id')}")
#         print(f"Chunk Index:     {chunk.get('chunk_index')}")
#         print(f"Timestamps:      {chunk.get('start')}s - {chunk.get('end')}s")
#         print(f"Language:        {chunk.get('language')}")
#         print("Full Transcript Text:")
#         print(chunk.get("text", ""))

#     print("\n" + "=" * 80)
#     print(f"SUCCESS: Successfully retrieved and displayed all {len(all_chunks)} chunks.")
#     print("=" * 80)


# if __name__ == "__main__":
#     main()


from uuid import UUID

from qdrant_client import models

from app.services.vector_store import get_qdrant_client


COLLECTION_NAME = "youtube_transcripts_multilingual"
VIDEO_ID = "14d55b3a-b145-42e8-8d5e-0485bfffb348"
OWNER_ID = "d3e52b69-1d19-4f1e-a532-6be37820d6e7"

EXPECTED_CHUNK_COUNT = 27


def validate_chunks(all_chunks):
    """Validate retrieved Qdrant chunks."""

    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)

    # 1. Chunk count
    actual_count = len(all_chunks)

    print(f"\nExpected chunks: {EXPECTED_CHUNK_COUNT}")
    print(f"Actual chunks:   {actual_count}")

    if actual_count == EXPECTED_CHUNK_COUNT:
        print("PASS: Chunk count matches.")
    else:
        print("WARNING: Chunk count mismatch.")

    # 2. UUID uniqueness and validity
    chunk_ids = [chunk["chunk_id"] for chunk in all_chunks]

    unique_ids = set(chunk_ids)

    print(f"\nTotal UUIDs:  {len(chunk_ids)}")
    print(f"Unique UUIDs: {len(unique_ids)}")

    if len(chunk_ids) == len(unique_ids):
        print("PASS: No duplicate chunk UUIDs.")
    else:
        print("WARNING: Duplicate chunk UUIDs found.")

    invalid_uuids = []

    for chunk_id in chunk_ids:
        try:
            UUID(chunk_id)
        except (ValueError, TypeError, AttributeError):
            invalid_uuids.append(chunk_id)

    if invalid_uuids:
        print("WARNING: Invalid UUIDs:", invalid_uuids)
    else:
        print("PASS: All chunk IDs are valid UUIDs.")

    # 3. Timestamp validation
    invalid_timestamps = []

    for chunk in all_chunks:
        start = chunk.get("start")
        end = chunk.get("end")

        if (
            not isinstance(start, (int, float))
            or isinstance(start, bool)
            or not isinstance(end, (int, float))
            or isinstance(end, bool)
            or start >= end
        ):
            invalid_timestamps.append(chunk["chunk_id"])

    if invalid_timestamps:
        print("\nWARNING: Invalid timestamps found:")
        for chunk_id in invalid_timestamps:
            print(chunk_id)
    else:
        print("\nPASS: All timestamps are valid.")

    # 4. Language metadata
    languages = {
        chunk.get("language")
        for chunk in all_chunks
    }

    print("\nLanguages found:", languages)

    if languages == {"en"}:
        print("PASS: All chunks have English language metadata.")
    else:
        print("WARNING: Unexpected or missing language metadata.")

    # 5. Empty text validation
    empty_chunks = [
        chunk["chunk_id"]
        for chunk in all_chunks
        if not isinstance(chunk.get("text"), str)
        or not chunk.get("text", "").strip()
    ]

    if empty_chunks:
        print("\nWARNING: Empty or missing transcript text:")
        for chunk_id in empty_chunks:
            print(chunk_id)
    else:
        print("\nPASS: All chunks contain transcript text.")

    # 6. Owner and video payload validation
    incorrect_owner = [
        chunk["chunk_id"]
        for chunk in all_chunks
        if chunk.get("owner_id") != OWNER_ID
    ]

    incorrect_video = [
        chunk["chunk_id"]
        for chunk in all_chunks
        if chunk.get("video_id") != VIDEO_ID
    ]

    if incorrect_owner:
        print("\nWARNING: Incorrect owner IDs found:", incorrect_owner)
    else:
        print("\nPASS: All chunks belong to the expected owner.")

    if incorrect_video:
        print("\nWARNING: Incorrect video IDs found:", incorrect_video)
    else:
        print("PASS: All chunks belong to the expected video.")

    print("\n" + "=" * 80)
    print("END OF VALIDATION REPORT")
    print("=" * 80)


def main():
    client = get_qdrant_client()

    # Check collection existence
    if not client.collection_exists(COLLECTION_NAME):
        print(
            f"ERROR: Collection '{COLLECTION_NAME}' "
            "does not exist in Qdrant."
        )
        return

    # Strict owner and video filter
    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=OWNER_ID),
            ),
            models.FieldCondition(
                key="video_id",
                match=models.MatchValue(value=VIDEO_ID),
            ),
        ]
    )

    all_chunks = []
    offset = None

    # Paginated Qdrant scrolling
    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=100,
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

    # Sort chronologically by chunk index
    all_chunks.sort(
        key=lambda chunk: (
            chunk.get("chunk_index", 0),
            chunk.get("start", 0),
        )
    )

    # Display metadata
    print("\n" + "=" * 80)
    print(f"COLLECTION:       {COLLECTION_NAME}")
    print(f"VIDEO ID:         {VIDEO_ID}")
    print(f"OWNER ID:         {OWNER_ID}")
    print(f"TOTAL CHUNKS:     {len(all_chunks)}")
    print("=" * 80)

    if not all_chunks:
        print("No chunks found for the specified video and owner.")
        return

    # Display every chunk
    for index, chunk in enumerate(all_chunks, start=1):
        print(f"\n{'-' * 80}")
        print(
            f"CHUNK {index} "
            f"(Index: {chunk.get('chunk_index')})"
        )
        print(f"Chunk UUID:  {chunk.get('chunk_id')}")
        print(f"Start:       {chunk.get('start')} seconds")
        print(f"End:         {chunk.get('end')} seconds")
        print(f"Language:    {chunk.get('language')}")
        print("\nTranscript Text:")
        print(chunk.get("text", "[MISSING TEXT]"))

    # Run validation
    validate_chunks(all_chunks)

    print("\nInspection completed.")


if __name__ == "__main__":
    main()
