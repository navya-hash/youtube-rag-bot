import logging
from uuid import UUID

from app.db.session import SessionLocal
from app.models import Chat
from app.services.retrieval import retrieve_relevant_chunks
from app.services.llm import generate_answer
from app.services.generation_evaluation import (
    evaluate_answer_relevance,
    evaluate_faithfulness,
    evaluate_answer_correctness,
)

logging.basicConfig(level=logging.INFO)

CHAT_ID = "385eb5a1-e658-4d9f-b8cc-564da5970c93"
QUESTION = "What is RAG evals?"
TOP_K = 5

REFERENCE_ANSWER = """
RAG evaluation measures the performance of both retrieval
and generation components.

Retrieval evaluation checks whether relevant documents are
retrieved, using metrics such as Recall@K, MAP and NDCG.

Generation evaluation checks the quality of generated answers.
When a ground-truth answer is available, semantic similarity
can be used. Without ground truth, an LLM judge can evaluate
faithfulness and answer relevance.
"""
def main():
    db = SessionLocal()

    try:
        # Step 1: Fetch the chat
        chat = db.get(Chat, UUID(CHAT_ID))

        if chat is None:
            raise ValueError("Chat not found.")

        owner_id = chat.owner_id

        print("\nQuestion:", QUESTION)

        # Step 2: Retrieve actual context chunks
        context_chunks = retrieve_relevant_chunks(
            db=db,
            chat=chat,
            owner_id=owner_id,
            question=QUESTION,
            limit=TOP_K,
        )

        if not context_chunks:
            raise ValueError("No relevant chunks retrieved.")

        print("\nRetrieved chunks:", len(context_chunks))

        # Step 3: Generate the answer
        answer = generate_answer(
            question=QUESTION,
            context_chunks=context_chunks,
            output_language=chat.output_language or "English",
            cache_scope=None,
        )

        print("\n========== GENERATED ANSWER ==========")
        print(answer)

        # Step 4: Evaluate faithfulness
        evaluation = evaluate_faithfulness(
            question=QUESTION,
            context_chunks=context_chunks,
            answer=answer,
        )

        print("\n========== FAITHFULNESS EVALUATION ==========")
        print("Total claims:", evaluation["total_claims"])
        print("Supported claims:", evaluation["supported_claims"])
        print("Unsupported claims:", evaluation["unsupported_claims"])
        print(
            "Faithfulness score:",
            f'{evaluation["faithfulness_score"]:.2%}',
        )
        print("Reason:", evaluation["reason"])

        # Step 5: Evaluate answer relevance
        relevance = evaluate_answer_relevance(
            question=QUESTION,
            answer=answer,
        )

        print("\n========== ANSWER RELEVANCE EVALUATION ==========")
        print(
            "Relevance score:",
            f'{relevance["relevance_score"]:.2%}',
        )
        print("Reason:", relevance["reason"])


        # Step 6: Evaluate answer correctness
        correctness = evaluate_answer_correctness(
            question=QUESTION,
            answer=answer,
            reference_answer=REFERENCE_ANSWER,
        )

        print("\n========== ANSWER CORRECTNESS EVALUATION ==========")
        print(
            "Correctness score:",
            f'{correctness["correctness_score"]:.2%}',
        )
        print("Reason:", correctness["reason"])


    except Exception:
        logging.exception("Faithfulness test failed.")

    finally:
        db.close()


if __name__ == "__main__":
    main()

