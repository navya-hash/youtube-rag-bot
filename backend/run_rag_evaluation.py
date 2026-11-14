
import argparse
import json
import logging
from pathlib import Path
from uuid import UUID

from app.db.session import SessionLocal
from app.models import Chat, ChatVideo, Video

from app.services.evaluation_dataset import load_evaluation_dataset
from app.services.evaluation import (
    calculate_precision_at_k,
    calculate_recall_at_k,
)
from app.services.retrieval import retrieve_relevant_chunks
from app.services.llm import generate_answer
from app.services.generation_evaluation import (
    call_with_rate_limit_retry,
    evaluate_faithfulness,
    evaluate_answer_relevance,
    evaluate_answer_correctness,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOP_K = 5

OUTPUT_PATH = "rag_evaluation_results.json"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run YouTube RAG evaluation."
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to the evaluation dataset JSON file.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(OUTPUT_PATH),
        help="Path where the evaluation report will be saved.",
    )

    return parser.parse_args()


def evaluate_sample(db, sample):
    logger.info("Evaluating question: %s", sample.question_id)

    # 1. Fetch the chat
    chat = db.get(Chat, UUID(sample.chat_id))

    if not chat:
        raise ValueError(f"Chat not found: {sample.chat_id}")

    if not chat.owner_id:
        raise ValueError("Invalid chat owner.")

    # 2. Verify that the video belongs to this chat
    chat_video = (
        db.query(ChatVideo)
        .filter(
            ChatVideo.chat_id == chat.id,
            ChatVideo.video_id == UUID(sample.video_id),
        )
        .first()
    )

    if not chat_video:
        raise ValueError(
            f"Video {sample.video_id} is not associated with "
            f"chat {sample.chat_id}"
        )

    # 3. Verify video ownership
    video = db.get(Video, UUID(sample.video_id))

    if not video or video.owner_id != chat.owner_id:
        raise ValueError(
            "Video does not belong to this chat owner."
        )

    # 4. Retrieve relevant chunks
    retrieved_chunks = retrieve_relevant_chunks(
        db=db,
        chat=chat,
        owner_id=chat.owner_id,
        question=sample.question,
        limit=TOP_K,
    )

    retrieved_chunk_ids = [
        chunk["chunk_id"] for chunk in retrieved_chunks
    ]

    # 5. Retrieval evaluation
    relevant_chunk_ids = set(sample.relevant_chunk_ids)

    precision = calculate_precision_at_k(
        retrieved_chunk_ids,
        relevant_chunk_ids,
        TOP_K,
    )

    recall = calculate_recall_at_k(
        retrieved_chunk_ids,
        relevant_chunk_ids,
        TOP_K,
    )

    result = {
        "question_id": sample.question_id,
        "question": sample.question,
        "retrieved_chunks": len(retrieved_chunks),
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "precision_at_k": precision,
        "recall_at_k": recall,
        "generation_status": "success",
        "generation_error": None,
        "faithfulness": None,
        "answer_relevance": None,
        "answer_correctness": None,
        "generated_answer": None,
    }

    # 6. Generate answer and evaluate generation
    try:
        context_chunks = retrieved_chunks

        answer = call_with_rate_limit_retry(
            generate_answer,
            question=sample.question,
            context_chunks=context_chunks,
            output_language=chat.output_language,
            cache_scope={
                "owner_id": str(chat.owner_id),
                "chat_id": str(chat.id),
            },
        )

        result["generated_answer"] = answer

        # 7. Evaluate faithfulness
        faithfulness = evaluate_faithfulness(
            question=sample.question,
            context_chunks=context_chunks,
            answer=answer,
        )

        result["faithfulness"] = faithfulness["faithfulness_score"]

        # 8. Evaluate answer relevance
        relevance = evaluate_answer_relevance(
            question=sample.question,
            answer=answer,
        )

        result["answer_relevance"] = relevance["relevance_score"]

        # 9. Evaluate answer correctness
        correctness = evaluate_answer_correctness(
            question=sample.question,
            answer=answer,
            reference_answer=sample.reference_answer,
        )

        result["answer_correctness"] = correctness["correctness_score"]

    except Exception as exc:
        logger.exception(
            "Generation evaluation failed for %s",
            sample.question_id,
        )

        result["generation_status"] = "failed"
        result["generation_error"] = str(exc)

    return result


def main():
    args = parse_arguments()

    # Load selected dataset.
    # If no custom path is provided, use the existing default dataset.
    if args.dataset:
        samples = load_evaluation_dataset(args.dataset)
    else:
        samples = load_evaluation_dataset()

    results = []

    db = SessionLocal()

    try:
        for sample in samples:
            try:
                result = evaluate_sample(db, sample)
                results.append(result)

                print(f"\nCompleted: {sample.question_id}")

                print(
                    f"Precision@{TOP_K}: "
                    f"{result['precision_at_k']:.2%}"
                )

                print(
                    f"Recall@{TOP_K}: "
                    f"{result['recall_at_k']:.2%}"
                )

                if result["generation_status"] == "success":
                    print(
                        f"Faithfulness: "
                        f"{result['faithfulness']:.2%}"
                    )

                    print(
                        f"Answer Relevance: "
                        f"{result['answer_relevance']:.2%}"
                    )

                    print(
                        f"Answer Correctness: "
                        f"{result['answer_correctness']:.2%}"
                    )

                else:
                    print(
                        f"Generation evaluation: FAILED "
                        f"({result['generation_error']})"
                    )

            except Exception:
                logger.exception(
                    "Retrieval evaluation failed for %s",
                    sample.question_id,
                )

        # 10. Generate combined evaluation report
        if results:
            retrieval_precisions = [
                r["precision_at_k"]
                for r in results
                if r.get("precision_at_k") is not None
            ]

            retrieval_recalls = [
                r["recall_at_k"]
                for r in results
                if r.get("recall_at_k") is not None
            ]

            faithfulness_scores = [
                r["faithfulness"]
                for r in results
                if r.get("faithfulness") is not None
            ]

            relevance_scores = [
                r["answer_relevance"]
                for r in results
                if r.get("answer_relevance") is not None
            ]

            correctness_scores = [
                r["answer_correctness"]
                for r in results
                if r.get("answer_correctness") is not None
            ]

            average_metrics = {
                "precision_at_k": (
                    sum(retrieval_precisions) / len(retrieval_precisions)
                    if retrieval_precisions else 0.0
                ),
                "recall_at_k": (
                    sum(retrieval_recalls) / len(retrieval_recalls)
                    if retrieval_recalls else 0.0
                ),
                "faithfulness": (
                    sum(faithfulness_scores) / len(faithfulness_scores)
                    if faithfulness_scores else None
                ),
                "answer_relevance": (
                    sum(relevance_scores) / len(relevance_scores)
                    if relevance_scores else None
                ),
                "answer_correctness": (
                    sum(correctness_scores) / len(correctness_scores)
                    if correctness_scores else None
                ),
            }

            successful_retrieval_samples = len(results)

            successful_generation_samples = sum(
                1
                for r in results
                if r.get("generation_status") == "success"
            )

            report = {
                "total_samples": len(samples),
                "successful_samples": successful_retrieval_samples,
                "successful_generation_samples": successful_generation_samples,
                "top_k": TOP_K,
                "average_metrics": average_metrics,
                "results": results,
            }

            # Create output directory if necessary
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(
                args.output,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    report,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )

            print(
                f"\nEvaluation report saved to {args.output}"
            )

        else:
            print("\nNo evaluation samples completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()

# import json
# import logging
# from uuid import UUID

# from app.db.session import SessionLocal
# from app.models import Chat, ChatVideo, Video

# from app.services.evaluation_dataset import load_evaluation_dataset
# from app.services.evaluation import (
#     calculate_precision_at_k,
#     calculate_recall_at_k,
# )
# from app.services.retrieval import retrieve_relevant_chunks
# from app.services.llm import generate_answer
# from app.services.generation_evaluation import (
#     call_with_rate_limit_retry,
#     evaluate_faithfulness,
#     evaluate_answer_relevance,
#     evaluate_answer_correctness,
# )


# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# TOP_K = 5

# OUTPUT_PATH = "rag_evaluation_results.json"


# def evaluate_sample(db, sample):
#     logger.info("Evaluating question: %s", sample.question_id)

#     # 1. Fetch the chat
#     chat = db.get(Chat, UUID(sample.chat_id))

#     if not chat:
#         raise ValueError(f"Chat not found: {sample.chat_id}")

#     if not chat.owner_id:
#         raise ValueError("Invalid chat owner.")

#     # 2. Verify that the video belongs to this chat
#     chat_video = (
#         db.query(ChatVideo)
#         .filter(
#             ChatVideo.chat_id == chat.id,
#             ChatVideo.video_id == UUID(sample.video_id),
#         )
#         .first()
#     )

#     if not chat_video:
#         raise ValueError(
#             f"Video {sample.video_id} is not associated with "
#             f"chat {sample.chat_id}"
#         )

#     # 3. Verify video ownership
#     video = db.get(Video, UUID(sample.video_id))

#     if not video or video.owner_id != chat.owner_id:
#         raise ValueError(
#             "Video does not belong to this chat owner."
#         )

#     # 4. Retrieve relevant chunks
#     retrieved_chunks = retrieve_relevant_chunks(
#         db=db,
#         chat=chat,
#         owner_id=chat.owner_id,
#         question=sample.question,
#         limit=TOP_K,
#     )

#     retrieved_chunk_ids = [
#         chunk["chunk_id"] for chunk in retrieved_chunks
#     ]

#     # 5. Retrieval evaluation
#     relevant_chunk_ids = set(sample.relevant_chunk_ids)

#     precision = calculate_precision_at_k(
#         retrieved_chunk_ids,
#         relevant_chunk_ids,
#         TOP_K,
#     )

#     recall = calculate_recall_at_k(
#         retrieved_chunk_ids,
#         relevant_chunk_ids,
#         TOP_K,
#     )

#     result = {
#         "question_id": sample.question_id,
#         "question": sample.question,
#         "retrieved_chunks": len(retrieved_chunks),
#         "retrieved_chunk_ids": retrieved_chunk_ids,
#         "precision_at_k": precision,
#         "recall_at_k": recall,
#         "generation_status": "success",
#         "generation_error": None,
#         "faithfulness": None,
#         "answer_relevance": None,
#         "answer_correctness": None,
#         "generated_answer": None,
#     }

#     # 6. Generate answer and evaluate generation
#     try:
#         context_chunks = retrieved_chunks

#         answer = call_with_rate_limit_retry(
#             generate_answer,
#             question=sample.question,
#             context_chunks=context_chunks,
#             output_language=chat.output_language,
#             cache_scope={
#                 "owner_id": str(chat.owner_id),
#                 "chat_id": str(chat.id),
#             },
#         )
#         result["generated_answer"] = answer

#         # 7. Evaluate faithfulness
#         faithfulness = evaluate_faithfulness(
#             question=sample.question,
#             context_chunks=context_chunks,
#             answer=answer,
#         )
#         result["faithfulness"] = faithfulness["faithfulness_score"]

#         # 8. Evaluate answer relevance
#         relevance = evaluate_answer_relevance(
#             question=sample.question,
#             answer=answer,
#         )
#         result["answer_relevance"] = relevance["relevance_score"]

#         # 9. Evaluate answer correctness
#         correctness = evaluate_answer_correctness(
#             question=sample.question,
#             answer=answer,
#             reference_answer=sample.reference_answer,
#         )
#         result["answer_correctness"] = correctness["correctness_score"]

#     except Exception as exc:
#         logger.exception("Generation evaluation failed for %s", sample.question_id)
#         result["generation_status"] = "failed"
#         result["generation_error"] = str(exc)

#     return result


# def main():
#     samples = load_evaluation_dataset()
#     results = []

#     db = SessionLocal()

#     try:
#         for sample in samples:
#             try:
#                 result = evaluate_sample(db, sample)
#                 results.append(result)

#                 print(f"\nCompleted: {sample.question_id}")

#                 print(
#                     f"Precision@{TOP_K}: "
#                     f"{result['precision_at_k']:.2%}"
#                 )

#                 print(
#                     f"Recall@{TOP_K}: "
#                     f"{result['recall_at_k']:.2%}"
#                 )

#                 if result["generation_status"] == "success":
#                     print(
#                         f"Faithfulness: "
#                         f"{result['faithfulness']:.2%}"
#                     )

#                     print(
#                         f"Answer Relevance: "
#                         f"{result['answer_relevance']:.2%}"
#                     )

#                     print(
#                         f"Answer Correctness: "
#                         f"{result['answer_correctness']:.2%}"
#                     )
#                 else:
#                     print(
#                         f"Generation evaluation: FAILED "
#                         f"({result['generation_error']})"
#                     )

#             except Exception:
#                 logger.exception(
#                     "Retrieval evaluation failed for %s",
#                     sample.question_id,
#                 )

#         # 10. Generate combined evaluation report
#         if results:
#             retrieval_precisions = [
#                 r["precision_at_k"]
#                 for r in results
#                 if r.get("precision_at_k") is not None
#             ]
#             retrieval_recalls = [
#                 r["recall_at_k"]
#                 for r in results
#                 if r.get("recall_at_k") is not None
#             ]
#             faithfulness_scores = [
#                 r["faithfulness"]
#                 for r in results
#                 if r.get("faithfulness") is not None
#             ]
#             relevance_scores = [
#                 r["answer_relevance"]
#                 for r in results
#                 if r.get("answer_relevance") is not None
#             ]
#             correctness_scores = [
#                 r["answer_correctness"]
#                 for r in results
#                 if r.get("answer_correctness") is not None
#             ]

#             average_metrics = {
#                 "precision_at_k": (
#                     sum(retrieval_precisions) / len(retrieval_precisions)
#                     if retrieval_precisions else 0.0
#                 ),
#                 "recall_at_k": (
#                     sum(retrieval_recalls) / len(retrieval_recalls)
#                     if retrieval_recalls else 0.0
#                 ),
#                 "faithfulness": (
#                     sum(faithfulness_scores) / len(faithfulness_scores)
#                     if faithfulness_scores else None
#                 ),
#                 "answer_relevance": (
#                     sum(relevance_scores) / len(relevance_scores)
#                     if relevance_scores else None
#                 ),
#                 "answer_correctness": (
#                     sum(correctness_scores) / len(correctness_scores)
#                     if correctness_scores else None
#                 ),
#             }

#             successful_retrieval_samples = len(results)
#             successful_generation_samples = sum(
#                 1 for r in results if r.get("generation_status") == "success"
#             )

#             report = {
#                 "total_samples": len(samples),
#                 "successful_samples": successful_retrieval_samples,
#                 "successful_generation_samples": successful_generation_samples,
#                 "top_k": TOP_K,
#                 "average_metrics": average_metrics,
#                 "results": results,
#             }

#             with open(
#                 OUTPUT_PATH,
#                 "w",
#                 encoding="utf-8",
#             ) as file:
#                 json.dump(
#                     report,
#                     file,
#                     indent=4,
#                     ensure_ascii=False,
#                 )

#             print(
#                 f"\nEvaluation report saved to {OUTPUT_PATH}"
#             )
#         else:
#             print("\nNo evaluation samples completed successfully.")

#     finally:
#         db.close()


# if __name__ == "__main__":
#     main()
