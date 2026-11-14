import logging
import sys
from uuid import UUID

from app.db.session import SessionLocal
from app.models import Chat, Video
from app.services.retrieval import retrieve_relevant_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHAT_ID = "5dcc866a-09ea-4278-a065-285d5bb7ced2"
EXPECTED_YOUTUBE_VIDEO_ID = "Ty8gcCKuwNI"
LIMIT = 5

QUESTIONS = [
    ("English", "What is Retrieval Augmented Generation (RAG)?"),
    ("Hindi", "RAG क्या है और यह कैसे काम करता है?"),
    ("Punjabi", "RAG ਕੀ ਹੈ ਅਤੇ ਇਹ ਕਿਵੇਂ ਕੰਮ ਕਰਦਾ ਹੈ?"),
]


def main():
    db = SessionLocal()
    try:
        # 1. Fetch chat from database
        chat = db.get(Chat, UUID(CHAT_ID))
        if not chat:
            print(f"Error: Chat not found for ID: {CHAT_ID}", file=sys.stderr)
            sys.exit(1)

        owner_id = chat.owner_id
        if not owner_id:
            print(f"Error: Chat {CHAT_ID} has no owner_id.", file=sys.stderr)
            sys.exit(1)

        # 2. Fetch expected video from database
        video = (
            db.query(Video)
            .filter(Video.youtube_video_id == EXPECTED_YOUTUBE_VIDEO_ID)
            .first()
        )
        if not video:
            print(
                f"Error: Video {EXPECTED_YOUTUBE_VIDEO_ID} not found in database.",
                file=sys.stderr,
            )
            sys.exit(1)

        expected_video_id = str(video.id)

        print("=" * 80)
        print("MULTILINGUAL RETRIEVAL TEST")
        print("=" * 80)
        print(f"Chat ID:            {chat.id}")
        print(f"Owner ID:           {owner_id}")
        print(f"Target YouTube ID:  {EXPECTED_YOUTUBE_VIDEO_ID}")
        print(f"Target Database ID: {expected_video_id}")
        print("=" * 80)

        all_passed = True

        for lang, question in QUESTIONS:
            print(f"\n[{lang}] Query: \"{question}\"")
            print("-" * 80)

            # Retrieve chunks using the production retrieval service
            chunks = retrieve_relevant_chunks(
                db=db,
                chat=chat,
                owner_id=owner_id,
                question=question,
                limit=LIMIT,
            )

            if not chunks:
                print(f"WARNING: No chunks retrieved for question: {question}")
                all_passed = False
                continue

            print(f"Retrieved {len(chunks)} chunks:")

            for i, chunk in enumerate(chunks, start=1):
                chunk_id = chunk.get("chunk_id")
                retrieved_vid = str(chunk.get("video_id"))
                yt_vid = chunk.get("youtube_video_id")
                rerank_score = chunk.get("rerank_score")
                text = chunk.get("text", "")
                snippet = text[:200].replace("\n", " ") + (
                    "..." if len(text) > 200 else ""
                )

                # Verify ownership and video matching
                matches_video = (retrieved_vid == expected_video_id) or (
                    yt_vid == EXPECTED_YOUTUBE_VIDEO_ID
                )
                if not matches_video:
                    all_passed = False

                score_str = (
                    f"{rerank_score:.4f}" if rerank_score is not None else "N/A"
                )

                print(f"  {i}. Chunk ID: {chunk_id}")
                print(
                    f"     Video ID: {retrieved_vid} (YouTube: {yt_vid}) "
                    f"{'[OK]' if matches_video else '[MISMATCH]'}"
                )
                print(f"     Timestamps: {chunk.get('start')}s - {chunk.get('end')}s")
                print(f"     Rerank Score: {score_str}")
                print(f"     Text Preview: {snippet}")

        print("\n" + "=" * 80)
        if all_passed:
            print("STATUS: All queries successfully retrieved grounded chunks for the expected video.")
        else:
            print("STATUS: Issues detected during retrieval (missing chunks or video mismatch).")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()

