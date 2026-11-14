
# import json
# from pathlib import Path
# from uuid import UUID

# from qdrant_client import models

# from app.services.vector_store import get_qdrant_client


# COLLECTION_NAME = "youtube_transcripts_multilingual"
# DATASET_PATH = Path("evaluation_dataset/english_rag_dataset.json")

# VIDEO_ID = "14d55b3a-b145-42e8-8d5e-0485bfffb348"
# OWNER_ID = "d3e52b69-1d19-4f1e-a532-6be37820d6e7"


# def main():
#     # 1. Load evaluation dataset
#     with DATASET_PATH.open("r", encoding="utf-8") as file:
#         samples = json.load(file)

#     print(f"Evaluation samples: {len(samples)}")

#     # 2. Validate sample-level UUIDs and associations
#     expected_chunk_ids = set()
#     errors = []

#     for sample in samples:
#         if sample["chat_id"] != "5dd1481c-9211-47c0-851d-af516d6e8b1a":
#             errors.append(f"{sample['question_id']}: Incorrect chat ID")

#         if sample["video_id"] != VIDEO_ID:
#             errors.append(f"{sample['question_id']}: Incorrect video ID")

#         for chunk_id in sample["relevant_chunk_ids"]:
#             try:
#                 UUID(chunk_id)
#             except (ValueError, TypeError, AttributeError):
#                 errors.append(
#                     f"{sample['question_id']}: Invalid UUID {chunk_id}"
#                 )
#                 continue

#             expected_chunk_ids.add(chunk_id)

#     # 3. Connect to Qdrant
#     client = get_qdrant_client()

#     if not client.collection_exists(COLLECTION_NAME):
#         print(f"ERROR: Collection {COLLECTION_NAME} does not exist.")
#         return

#     # 4. Retrieve all chunks belonging to this owner and video
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

#     existing_chunk_ids = set()
#     offset = None

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
#             existing_chunk_ids.add(str(point.id))

#         if next_offset is None:
#             break

#         offset = next_offset

#     # 5. Compare dataset UUIDs with Qdrant UUIDs
#     missing_ids = expected_chunk_ids - existing_chunk_ids

#     print("\n" + "=" * 60)
#     print("ENGLISH DATASET VALIDATION")
#     print("=" * 60)

#     print(f"Total evaluation samples: {len(samples)}")
#     print(f"Unique referenced UUIDs: {len(expected_chunk_ids)}")
#     print(f"English video chunks in Qdrant: {len(existing_chunk_ids)}")

#     if missing_ids:
#         print("\nFAIL: Referenced UUIDs missing from Qdrant:")
#         for chunk_id in sorted(missing_ids):
#             print(chunk_id)
#     else:
#         print("\nPASS: All referenced UUIDs exist in Qdrant.")

#     if errors:
#         print("\nFAIL: Dataset association or UUID errors:")
#         for error in errors:
#             print(error)
#     else:
#         print("PASS: All chat IDs, video IDs, and UUID formats are valid.")

#     print("\n" + "=" * 60)

#     if not missing_ids and not errors:
#         print("SUCCESS: Dataset passed all validation checks.")
#     else:
#         print("VALIDATION FAILED: Fix the errors before evaluation.")

#     print("=" * 60)


# if __name__ == "__main__":
#     main()
import json
from pathlib import Path

from app.services.vector_store import get_qdrant_client

COLLECTION_NAME = "youtube_transcripts_multilingual"
DATASET_PATH = Path("evaluation_dataset/english_rag_dataset.json")


def main():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        samples = json.load(file)

    # Collect every unique ground-truth chunk UUID.
    chunk_ids = sorted({
        chunk_id
        for sample in samples
        for chunk_id in sample["relevant_chunk_ids"]
    })

    client = get_qdrant_client()

    # Retrieve the actual transcript payloads from Qdrant.
    points = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=chunk_ids,
        with_payload=True,
        with_vectors=False,
    )

    chunks_by_id = {
        str(point.id): point.payload or {}
        for point in points
    }

    print(f"Evaluation samples: {len(samples)}")
    print(f"Unique referenced chunks: {len(chunk_ids)}")
    print(f"Chunks retrieved: {len(chunks_by_id)}")

    for sample in samples:
        print("\n" + "=" * 80)
        print(f"{sample['question_id']}: {sample['question']}")
        print("-" * 80)
        print(f"Reference answer: {sample['reference_answer']}")

        for chunk_id in sample["relevant_chunk_ids"]:
            payload = chunks_by_id.get(chunk_id)

            print("\n" + "-" * 60)
            print(f"Chunk UUID: {chunk_id}")

            if payload is None:
                print("ERROR: Chunk was not returned by Qdrant.")
                continue

            print(f"Chunk index: {payload.get('chunk_index')}")
            print(f"Start: {payload.get('start')} seconds")
            print(f"End: {payload.get('end')} seconds")
            print(f"Language: {payload.get('language')}")
            print(f"Text: {payload.get('text', '[No text field found]')}")

    print("\n" + "=" * 80)
    print("GROUND-TRUTH INSPECTION COMPLETE")


if __name__ == "__main__":
    main()