
# # # # # # # # from app.services.youtube import (
# # # # # # # #     extract_video_id,
# # # # # # # #     fetch_transcript,
# # # # # # # # )


# # # # # # # # url = input("Paste a YouTube URL: ").strip()

# # # # # # # # try:
# # # # # # # #     video_id = extract_video_id(url)
# # # # # # # #     print("Video ID:", video_id)

# # # # # # # #     segments = fetch_transcript(video_id)

# # # # # # # #     print("Number of segments:", len(segments))
# # # # # # # #     print("\nFirst five segments:")

# # # # # # # #     for segment in segments[:5]:
# # # # # # # #         print(segment)

# # # # # # # # except ValueError as exc:
# # # # # # # #     print("Error:", exc)
# # # # # # # # from app.core.config import get_settings

# # # # # # # # settings = get_settings()

# # # # # # # # assert settings.qdrant_url, "QDRANT_URL is missing"
# # # # # # # # assert settings.qdrant_api_key, "QDRANT_API_KEY is missing"
# # # # # # # # assert settings.openai_api_key, "OPENAI_API_KEY is missing"

# # # # # # # # print("Qdrant and OpenAI configuration loaded successfully.")
# # # # # # # # print(f"Collection: {settings.qdrant_collection_name}")
# # # # # # # # print(f"Embedding model: {settings.embedding_model}")


# # # # # # # # from app.services.embeddings import embed_texts


# # # # # # # # def main():
# # # # # # # #     texts = [
# # # # # # # #         "A transcript contains the words spoken in a video.",
# # # # # # # #         "RAG retrieves relevant chunks to answer a question.",
# # # # # # # #     ]

# # # # # # # #     vectors = embed_texts(texts)

# # # # # # # #     assert len(vectors) == len(texts)
# # # # # # # #     assert all(len(vector) == 384 for vector in vectors)
# # # # # # # #     assert all(all(isinstance(value, float) for value in vector)
# # # # # # # #                for vector in vectors)

# # # # # # # #     print("Embedding test passed!")
# # # # # # # #     print(f"Number of vectors: {len(vectors)}")
# # # # # # # #     print(f"Vector dimensions: {len(vectors[0])}")


# # # # # # # # if __name__ == "__main__":
# # # # # # # #     main()


# # # # # # # import os
# # # # # # # from pathlib import Path

# # # # # # # from dotenv import load_dotenv
# # # # # # # from sqlalchemy import create_engine, text

# # # # # # # load_dotenv(Path(__file__).resolve().parent / ".env")

# # # # # # # database_url = os.getenv("DATABASE_URL")

# # # # # # # if not database_url:
# # # # # # #     raise RuntimeError("DATABASE_URL is missing from backend/.env")

# # # # # # # engine = create_engine(
# # # # # # #     database_url,
# # # # # # #     pool_pre_ping=True,
# # # # # # #     connect_args={"connect_timeout": 10},
# # # # # # # )

# # # # # # # try:
# # # # # # #     with engine.connect() as connection:
# # # # # # #         result = connection.execute(
# # # # # # #             text("SELECT current_database(), version()")
# # # # # # #         )
# # # # # # #         database_name, version = result.one()

# # # # # # #         print("Neon connection successful!")
# # # # # # #         print(f"Database: {database_name}")
# # # # # # #         print(f"PostgreSQL: {version.split(',')[0]}")
# # # # # # # finally:
# # # # # # #     engine.dispose()


# # # # # # # from uuid import UUID

# # # # # # # from app.db.session import SessionLocal
# # # # # # # from app.models import Chat
# # # # # # # from app.services.retrieval import retrieve_relevant_chunks


# # # # # # # CHAT_ID = UUID("40325a38-ac49-4fda-9ed2-f4ea13aac530")


# # # # # # # def main():
# # # # # # #     db = SessionLocal()

# # # # # # #     try:
# # # # # # #         # Fetch the existing chat from Neon.
# # # # # # #         chat = db.get(Chat, CHAT_ID)

# # # # # # #         if chat is None:
# # # # # # #             print("Chat not found in Neon.")
# # # # # # #             return

# # # # # # #         # Test question.
# # # # # # #         question = "What are the main concepts explained in this video?"

# # # # # # #         print("\nQuestion:", question)
# # # # # # #         print("\nSearching relevant transcript chunks...\n")

# # # # # # #         results = retrieve_relevant_chunks(
# # # # # # #             db=db,
# # # # # # #             chat=chat,
# # # # # # #             owner_id=chat.owner_id,
# # # # # # #             question=question,
# # # # # # #             limit=5,
# # # # # # #         )

# # # # # # #         if not results:
# # # # # # #             print("No relevant chunks found.")
# # # # # # #             return

# # # # # # #         print(f"Retrieved {len(results)} chunks:\n")

# # # # # # #         for index, chunk in enumerate(results, start=1):
# # # # # # #             print(f"--- Chunk {index} ---")
# # # # # # #             print("Score:", chunk.get("score"))
# # # # # # #             print("Video:", chunk.get("youtube_video_id"))
# # # # # # #             print("Title:", chunk.get("video_title"))
# # # # # # #             print("Start:", chunk.get("start"), "seconds")
# # # # # # #             print("End:", chunk.get("end"), "seconds")
# # # # # # #             print("Text:", chunk.get("text"))
# # # # # # #             print()

# # # # # # #     finally:
# # # # # # #         db.close()


# # # # # # # if __name__ == "__main__":
# # # # # # #     main()

# # # # # # from app.services.llm import generate_answer

# # # # # # context_chunks = [
# # # # # #     {
# # # # # #         "youtube_video_id": "test123",
# # # # # #         "video_title": "Sample Video",
# # # # # #         "start": 10,
# # # # # #         "end": 30,
# # # # # #         "text": (
# # # # # #             "Machine learning allows computers to learn "
# # # # # #             "patterns from data without being explicitly "
# # # # # #             "programmed for every task."
# # # # # #         ),
# # # # # #     }
# # # # # # ]

# # # # # # question = "What is machine learning?"

# # # # # # answer = generate_answer(
# # # # # #     question=question,
# # # # # #     context_chunks=context_chunks,
# # # # # # )

# # # # # # print("\nGenerated Answer:\n")
# # # # # # print(answer)


# # # # # from app.services.llm import rewrite_question

# # # # # history = [
# # # # #     {
# # # # #         "role": "user",
# # # # #         "content": "What is machine learning?",
# # # # #     },
# # # # #     {
# # # # #         "role": "assistant",
# # # # #         "content": (
# # # # #             "Machine learning is a branch of AI that allows "
# # # # #             "computers to learn patterns from data."
# # # # #         ),
# # # # #     },
# # # # # ]

# # # # # question = "What are its advantages?"

# # # # # rewritten = rewrite_question(
# # # # #     question=question,
# # # # #     conversation_history=history,
# # # # # )

# # # # # print("Original question:", question)
# # # # # print("Rewritten question:", rewritten)

# # # # # assert rewritten.strip()
# # # # # print("Question rewriting test passed!")


# # # # from app.services.reranking import rerank_chunks

# # # # question = "Why is cooling important in data centres?"

# # # # chunks = [
# # # #     {
# # # #         "text": "Data centres use cooling systems to remove heat "
# # # #                 "generated by servers and networking equipment.",
# # # #         "video_title": "Data Centre Infrastructure",
# # # #         "start": 10,
# # # #         "end": 25,
# # # #     },
# # # #     {
# # # #         "text": "Data centres require reliable power supplies "
# # # #                 "to maintain continuous operation.",
# # # #         "video_title": "Data Centre Infrastructure",
# # # #         "start": 30,
# # # #         "end": 45,
# # # #     },
# # # #     {
# # # #         "text": "Cooling infrastructure prevents servers from "
# # # #                 "overheating and helps maintain optimal operating "
# # # #                 "temperatures.",
# # # #         "video_title": "Data Centre Infrastructure",
# # # #         "start": 50,
# # # #         "end": 65,
# # # #     },
# # # #     {
# # # #         "text": "Physical security protects data centre equipment "
# # # #                 "from unauthorized access.",
# # # #         "video_title": "Data Centre Infrastructure",
# # # #         "start": 70,
# # # #         "end": 85,
# # # #     },
# # # # ]

# # # # results = rerank_chunks(
# # # #     question=question,
# # # #     chunks=chunks,
# # # #     top_n=3,
# # # # )

# # # # print("\nReranked results:\n")

# # # # for index, chunk in enumerate(results, start=1):
# # # #     print(f"Rank: {index}")
# # # #     print(f"Score: {chunk['rerank_score']:.4f}")
# # # #     print(f"Content: {chunk['text']}")
# # # #     print("-" * 60)

# # # # assert len(results) == 3
# # # # assert results[0]["rerank_score"] >= results[-1]["rerank_score"]

# # # # print("Reranking test passed!")


# # # from uuid import UUID

# # # from app.services.vector_store import get_all_video_chunks

# # # OWNER_ID = UUID("89c8db86-796d-45fb-a27f-7810b90ca58c")
# # # VIDEO_ID = UUID("4f202a04-b391-4ec9-8171-ecf8a147ea29")


# # # chunks = get_all_video_chunks(
# # #     owner_id=OWNER_ID,
# # #     video_id=VIDEO_ID,
# # # )

# # # print("Total chunks:", len(chunks))

# # # for chunk in chunks:
# # #     print(
# # #         f"Chunk {chunk['chunk_index']} | "
# # #         f"{chunk['start']}s - {chunk['end']}s"
# # #     )
# # #     print(chunk["text"][:150])
# # #     print("-" * 60)

# # # if chunks:
# # #     indexes = [chunk["chunk_index"] for chunk in chunks]

# # #     assert indexes == sorted(indexes), "Chunks are not ordered!"

# # #     print("SUCCESS: All chunks retrieved in chronological order.")
# # # else:
# # #     print("No chunks found.")



# # import uuid

# # from app.db.session import SessionLocal
# # from app.services.summarization import summarize_video


# # VIDEO_ID = uuid.UUID("4f202a04-b391-4ec9-8171-ecf8a147ea29")

# # # Replace this with the owner_id belonging to this video in Neon.
# # OWNER_ID = uuid.UUID("89c8db86-796d-45fb-a27f-7810b90ca58c")


# # def main():
# #     db = SessionLocal()

# #     try:
# #         result = summarize_video(
# #             db=db,
# #             video_id=VIDEO_ID,
# #             owner_id=OWNER_ID,
# #         )

# #         print("\nSUMMARY GENERATED SUCCESSFULLY\n")
# #         print("Summary:")
# #         print(result["summary"])

# #         print("\nKey Points:")
# #         for point in result["key_points"]:
# #             print("-", point)

# #         print("\nTopics:")
# #         for topic in result["topics"]:
# #             print("-", topic)

# #         print("\nStatus:", result["status"])
# #         print("Summary ID:", result["id"])

# #     finally:
# #         db.close()


# # if __name__ == "__main__":
# #     main()


# from app.core.redis_client import get_redis_client

# redis_client = get_redis_client()

# try:
#     print("Redis connection:", redis_client.ping())

#     redis_client.set("youtube_rag:test", "working", ex=60)

#     print("Redis value:", redis_client.get("youtube_rag:test"))

#     redis_client.delete("youtube_rag:test")

# except Exception as exc:
#     print("Redis test failed:", exc)



from app.services.embeddings import (
    embed_texts,
    _embedding_cache_key,
)
from app.core.config import get_settings
from app.core.redis_client import get_redis_client

redis_client = get_redis_client()
settings = get_settings()

texts = [
    "What is machine learning?",
    "Explain neural networks.",
]

# Remove old entries so the first call is a guaranteed cache miss.
for text in texts:
    key = _embedding_cache_key(text, settings.embedding_model)
    redis_client.delete(key)

print("\nFirst call: expecting cache misses")
first_result = embed_texts(texts)

print("\nSecond call: expecting cache hits")
second_result = embed_texts(texts)

assert len(first_result) == len(second_result)
assert first_result == second_result

print("\nEmbedding cache test passed!")
print("Number of embeddings:", len(second_result))
print("Dimensions:", len(second_result[0]))
