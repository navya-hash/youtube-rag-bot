import json
import unittest
from unittest.mock import MagicMock, patch

from app.services.evaluation import (
    calculate_precision_at_k,
    calculate_recall_at_k,
)
from app.services.generation_evaluation import (
    call_with_rate_limit_retry,
    evaluate_faithfulness,
    extract_retry_delay,
    is_rate_limit_error,
)
from groq import RateLimitError


class TestPrecisionRecallMetrics(unittest.TestCase):
    def test_precision_at_k_standard(self):
        retrieved = ["a", "b", "c", "d", "e"]
        relevant = {"a", "c", "x"}
        self.assertAlmostEqual(calculate_precision_at_k(retrieved, relevant, 5), 2 / 5)

    def test_precision_at_k_fewer_than_k(self):
        # Only 2 chunks retrieved, 1 relevant, but k=5
        retrieved = ["a", "b"]
        relevant = {"a", "x"}
        # Precision@5 must be 1 / 5 = 0.2, not 1 / 2 = 0.5
        self.assertAlmostEqual(calculate_precision_at_k(retrieved, relevant, 5), 1 / 5)

    def test_precision_at_k_empty_retrieved(self):
        self.assertEqual(calculate_precision_at_k([], {"a"}, 5), 0.0)

    def test_precision_at_k_invalid_k(self):
        with self.assertRaises(ValueError):
            calculate_precision_at_k(["a"], {"a"}, 0)
        with self.assertRaises(ValueError):
            calculate_precision_at_k(["a"], {"a"}, -1)

    def test_recall_at_k_standard(self):
        retrieved = ["a", "b", "c", "d", "e"]
        relevant = {"a", "c", "x", "y"}
        self.assertAlmostEqual(calculate_recall_at_k(retrieved, relevant, 5), 2 / 4)


class TestFaithfulnessScoreValidation(unittest.TestCase):
    def _mock_groq_response(self, content: str):
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    @patch("app.services.generation_evaluation.get_groq_client")
    def test_faithfulness_five_sevenths_rounded_0_71(self, mock_get_client):
        # 5/7 with reported score 0.71 (formerly caused ValueError: Faithfulness score does not match claim counts)
        content = json.dumps({
            "total_claims": 7,
            "supported_claims": 5,
            "unsupported_claims": 2,
            "faithfulness_score": 0.71,
            "reason": "5 of 7 claims supported.",
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(content)
        mock_get_client.return_value = mock_client

        res = evaluate_faithfulness("q", [{"text": "ctx"}], "ans")
        self.assertAlmostEqual(res["faithfulness_score"], 5 / 7)
        self.assertEqual(res["total_claims"], 7)
        self.assertEqual(res["supported_claims"], 5)
        self.assertEqual(res["unsupported_claims"], 2)

    @patch("app.services.generation_evaluation.get_groq_client")
    def test_faithfulness_one_third_rounded_0_33(self, mock_get_client):
        # 1/3 with reported score 0.33
        content = json.dumps({
            "total_claims": 3,
            "supported_claims": 1,
            "unsupported_claims": 2,
            "faithfulness_score": 0.33,
            "reason": "1 of 3 claims supported.",
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(content)
        mock_get_client.return_value = mock_client

        res = evaluate_faithfulness("q", [{"text": "ctx"}], "ans")
        self.assertAlmostEqual(res["faithfulness_score"], 1 / 3)

    @patch("app.services.generation_evaluation.get_groq_client")
    def test_faithfulness_zero_total_claims(self, mock_get_client):
        # Zero claims must be handled explicitly and score = 1.0
        content = json.dumps({
            "total_claims": 0,
            "supported_claims": 0,
            "unsupported_claims": 0,
            "faithfulness_score": 1.0,
            "reason": "No factual claims made.",
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_groq_response(content)
        mock_get_client.return_value = mock_client

        res = evaluate_faithfulness("q", [{"text": "ctx"}], "ans")
        self.assertEqual(res["faithfulness_score"], 1.0)

    @patch("app.services.generation_evaluation.get_groq_client")
    def test_faithfulness_invalid_claim_counts(self, mock_get_client):
        # Sum mismatch: 3 + 1 != 5
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        invalid_cases = [
            {"total_claims": 5, "supported_claims": 3, "unsupported_claims": 1, "reason": "err"},
            {"total_claims": -1, "supported_claims": 0, "unsupported_claims": -1, "reason": "err"},
            {"total_claims": True, "supported_claims": 1, "unsupported_claims": 0, "reason": "err"},
            {"total_claims": 0, "supported_claims": 1, "unsupported_claims": 0, "reason": "err"},
        ]
        for case in invalid_cases:
            mock_client.chat.completions.create.return_value = self._mock_groq_response(json.dumps(case))
            with self.assertRaises(ValueError):
                evaluate_faithfulness("q", [{"text": "ctx"}], "ans")


class TestGroqRateLimitRetry(unittest.TestCase):
    def test_extract_retry_delay_from_message(self):
        exc = Exception("Rate limit reached on TPM. Please try again in 6.96s.")
        delay = extract_retry_delay(exc)
        self.assertAlmostEqual(delay, 7.96)

    def test_extract_retry_delay_from_header(self):
        exc = MagicMock(spec=Exception)
        response = MagicMock()
        response.headers = {"retry-after": "12.5"}
        exc.response = response
        self.assertAlmostEqual(extract_retry_delay(exc), 12.5)

    def test_is_rate_limit_error(self):
        self.assertTrue(is_rate_limit_error(Exception("429 Too Many Requests")))
        self.assertTrue(is_rate_limit_error(Exception("Rate limit reached on tokens per minute")))
        self.assertFalse(is_rate_limit_error(ValueError("Bad input")))

    @patch("app.services.generation_evaluation.time.sleep", return_value=None)
    def test_retry_eventual_success(self, mock_sleep):
        mock_target = MagicMock()
        mock_429 = Exception("Rate limit exceeded. Please try again in 2s.")
        mock_target.side_effect = [mock_429, mock_429, "Success!"]

        result = call_with_rate_limit_retry(mock_target, max_retries=3, base_delay=1.0)
        self.assertEqual(result, "Success!")
        self.assertEqual(mock_target.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("app.services.generation_evaluation.time.sleep", return_value=None)
    def test_retry_exhaustion_raises(self, mock_sleep):
        mock_target = MagicMock()
        mock_429 = Exception("Rate limit exceeded. Please try again in 1s.")
        mock_target.side_effect = mock_429

        with self.assertRaises(Exception):
            call_with_rate_limit_retry(mock_target, max_retries=2, base_delay=0.1)
        self.assertEqual(mock_target.call_count, 3)


class TestOrchestrationMetricsPreservation(unittest.TestCase):
    def test_aggregate_metrics_excluding_missing_generation(self):
        results = [
            {
                "question_id": "q1",
                "precision_at_k": 0.2,
                "recall_at_k": 0.5,
                "generation_status": "success",
                "faithfulness": 0.8,
                "answer_relevance": 0.9,
                "answer_correctness": 0.85,
            },
            {
                "question_id": "q2",
                "precision_at_k": 0.4,
                "recall_at_k": 0.5,
                "generation_status": "failed",
                "generation_error": "Groq 429",
                "faithfulness": None,
                "answer_relevance": None,
                "answer_correctness": None,
            },
        ]

        retrieval_precisions = [r["precision_at_k"] for r in results if r.get("precision_at_k") is not None]
        retrieval_recalls = [r["recall_at_k"] for r in results if r.get("recall_at_k") is not None]
        faithfulness_scores = [r["faithfulness"] for r in results if r.get("faithfulness") is not None]
        relevance_scores = [r["answer_relevance"] for r in results if r.get("answer_relevance") is not None]
        correctness_scores = [r["answer_correctness"] for r in results if r.get("answer_correctness") is not None]

        avg_precision = sum(retrieval_precisions) / len(retrieval_precisions)
        avg_recall = sum(retrieval_recalls) / len(retrieval_recalls)
        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        avg_correctness = sum(correctness_scores) / len(correctness_scores)

        # Retrieval averages over 2 samples
        self.assertAlmostEqual(avg_precision, 0.3)
        self.assertAlmostEqual(avg_recall, 0.5)

        # Generation averages over ONLY 1 successful sample (not diluted to 0.4!)
        self.assertAlmostEqual(avg_faithfulness, 0.8)
        self.assertAlmostEqual(avg_relevance, 0.9)
        self.assertAlmostEqual(avg_correctness, 0.85)

    @patch("app.services.generation_evaluation.time.sleep", return_value=None)
    @patch("run_rag_evaluation.generate_answer")
    @patch("run_rag_evaluation.retrieve_relevant_chunks")
    def test_evaluate_sample_preserves_retrieval_on_generation_failure(
        self, mock_retrieve, mock_generate, mock_sleep
    ):
        from run_rag_evaluation import evaluate_sample

        mock_db = MagicMock()
        mock_chat = MagicMock()
        mock_chat.id = "5dcc866a-09ea-4278-a065-285d5bb7ced2"
        mock_chat.owner_id = "d3e52b69-1d19-4f1e-a532-6be37820d6e7"
        mock_chat.output_language = "English"

        mock_video = MagicMock()
        mock_video.owner_id = mock_chat.owner_id

        mock_db.get.side_effect = lambda model, uid: mock_chat if "Chat" in str(model) else mock_video
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

        # Mock retrieval of 5 chunks with 1 matching relevant ID
        mock_retrieve.return_value = [
            {"chunk_id": "chunk-1"},
            {"chunk_id": "chunk-2"},
            {"chunk_id": "chunk-3"},
            {"chunk_id": "chunk-4"},
            {"chunk_id": "chunk-5"},
        ]

        # Simulate generation evaluation error (e.g. non-retryable failure or final error)
        mock_generate.side_effect = ValueError("LLM generation failed.")

        mock_sample = MagicMock()
        mock_sample.question_id = "test-q"
        mock_sample.question = "Test question?"
        mock_sample.chat_id = "5dcc866a-09ea-4278-a065-285d5bb7ced2"
        mock_sample.video_id = "0dea0eb3-0f05-4394-b4d6-d7137f7ce59b"
        mock_sample.relevant_chunk_ids = ["chunk-1", "other-chunk"]
        mock_sample.reference_answer = "Ref answer"

        result = evaluate_sample(mock_db, mock_sample)

        # Precision@5 = 1 / 5 = 0.2, Recall@5 = 1 / 2 = 0.5
        self.assertAlmostEqual(result["precision_at_k"], 0.2)
        self.assertAlmostEqual(result["recall_at_k"], 0.5)
        self.assertEqual(result["retrieved_chunks"], 5)
        self.assertEqual(result["retrieved_chunk_ids"], ["chunk-1", "chunk-2", "chunk-3", "chunk-4", "chunk-5"])

        # Generation status must be failed and generation error recorded
        self.assertEqual(result["generation_status"], "failed")
        self.assertIn("LLM generation failed", result["generation_error"])
        self.assertIsNone(result["faithfulness"])
        self.assertIsNone(result["answer_relevance"])
        self.assertIsNone(result["answer_correctness"])


if __name__ == "__main__":
    unittest.main()
