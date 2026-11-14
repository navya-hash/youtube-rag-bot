
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm import (
    generate_answer,
    LLMServiceError,
)
from app.services.guardrails.toxicity_detection import ToxicityLevel
from app.services.guardrails.hallucination_detection import (
    HallucinationResult,
    ClaimVerification,
    ClaimStatus,
)


SAMPLE_QUESTION = "Who created Python?"

SAMPLE_ANSWER = "Python was created by Guido van Rossum."

SAMPLE_CONTEXT = [
    {
        "text": "Python was created by Guido van Rossum.",
        "youtube_video_id": "test_video",
        "video_title": "Introduction to Python",
        "start": 10,
        "end": 20,
    }
]


def mock_groq_client(answer=SAMPLE_ANSWER):
    """Create a mocked Groq client."""

    client = MagicMock()

    client.chat.completions.create.return_value.choices[
        0
    ].message.content = answer

    return client


def supported_verification():
    """Return a successful hallucination verification result."""

    return HallucinationResult(
        claims=[
            ClaimVerification(
                claim=SAMPLE_ANSWER,
                status=ClaimStatus.SUPPORTED,
                evidence="Python was created by Guido van Rossum.",
            )
        ]
    )


def unsupported_verification():
    """Return a verification result containing an unsupported claim."""

    return HallucinationResult(
        claims=[
            ClaimVerification(
                claim="Python is the fastest programming language.",
                status=ClaimStatus.UNSUPPORTED,
                evidence="",
            )
        ]
    )


def safe_toxicity_result():
    result = MagicMock()
    result.classification = ToxicityLevel.SAFE
    return result


def toxic_toxicity_result():
    result = MagicMock()
    result.classification = ToxicityLevel.TOXIC
    return result


def test_successful_answer_passes_all_guardrails_and_is_cached():
    client = mock_groq_client()

    with (
        patch(
            "app.services.llm.get_groq_client",
            return_value=client,
        ),
        patch(
            "app.services.llm.get_settings",
            return_value=SimpleNamespace(
                groq_model="test-model"
            ),
        ),
        patch(
            "app.services.llm.mask_sensitive_information",
            side_effect=lambda text: text,
        ),
        patch(
            "app.services.llm.detect_toxicity",
            return_value=safe_toxicity_result(),
        ),
        patch(
            "app.services.guardrails.hallucination_detection.verify_answer_claims",
            return_value=supported_verification(),
        ) as mock_verifier,
        patch(
            "app.services.llm._answer_cache_key",
            return_value="test-cache-key",
        ),
        patch(
            "app.services.llm._get_cached_answer",
            return_value=None,
        ),
        patch(
            "app.services.llm._cache_answer",
        ) as mock_cache,
    ):
        answer = generate_answer(
            question=SAMPLE_QUESTION,
            context_chunks=SAMPLE_CONTEXT,
            cache_scope="test-user:test-chat",
        )

    assert answer == SAMPLE_ANSWER

    mock_verifier.assert_called_once()
    mock_cache.assert_called_once_with(
        "test-cache-key",
        SAMPLE_ANSWER,
    )


def test_toxic_answer_returns_safe_fallback():
    client = mock_groq_client()

    with (
        patch(
            "app.services.llm.get_groq_client",
            return_value=client,
        ),
        patch(
            "app.services.llm.get_settings",
            return_value=SimpleNamespace(
                groq_model="test-model"
            ),
        ),
        patch(
            "app.services.llm.mask_sensitive_information",
            side_effect=lambda text: text,
        ),
        patch(
            "app.services.llm.detect_toxicity",
            return_value=toxic_toxicity_result(),
        ),
        patch(
            "app.services.guardrails.hallucination_detection.verify_answer_claims",
        ) as mock_verifier,
        patch(
            "app.services.llm._answer_cache_key",
            return_value="test-cache-key",
        ),
        patch(
            "app.services.llm._get_cached_answer",
            return_value=None,
        ),
        patch(
            "app.services.llm._cache_answer",
        ) as mock_cache,
    ):
        answer = generate_answer(
            question=SAMPLE_QUESTION,
            context_chunks=SAMPLE_CONTEXT,
            cache_scope="test-user:test-chat",
        )

    assert "couldn't generate a safe response" in answer.lower()

    mock_verifier.assert_not_called()
    mock_cache.assert_not_called()


def test_unsupported_claim_returns_hallucination_fallback():
    client = mock_groq_client()

    with (
        patch(
            "app.services.llm.get_groq_client",
            return_value=client,
        ),
        patch(
            "app.services.llm.get_settings",
            return_value=SimpleNamespace(
                groq_model="test-model"
            ),
        ),
        patch(
            "app.services.llm.mask_sensitive_information",
            side_effect=lambda text: text,
        ),
        patch(
            "app.services.llm.detect_toxicity",
            return_value=safe_toxicity_result(),
        ),
        patch(
            "app.services.guardrails.hallucination_detection.verify_answer_claims",
            return_value=unsupported_verification(),
        ),
        patch(
            "app.services.llm._answer_cache_key",
            return_value="test-cache-key",
        ),
        patch(
            "app.services.llm._get_cached_answer",
            return_value=None,
        ),
        patch(
            "app.services.llm._cache_answer",
        ) as mock_cache,
    ):
        answer = generate_answer(
            question=SAMPLE_QUESTION,
            context_chunks=SAMPLE_CONTEXT,
            cache_scope="test-user:test-chat",
        )

    assert "couldn't verify all the factual claims" in answer.lower()

    mock_cache.assert_not_called()


def test_hallucination_verifier_failure_raises_llm_service_error():
    client = mock_groq_client()

    with (
        patch(
            "app.services.llm.get_groq_client",
            return_value=client,
        ),
        patch(
            "app.services.llm.get_settings",
            return_value=SimpleNamespace(
                groq_model="test-model"
            ),
        ),
        patch(
            "app.services.llm.mask_sensitive_information",
            side_effect=lambda text: text,
        ),
        patch(
            "app.services.llm.detect_toxicity",
            return_value=safe_toxicity_result(),
        ),
        patch(
            "app.services.guardrails.hallucination_detection.verify_answer_claims",
            side_effect=LLMServiceError(
                "Unable to verify answer claims."
            ),
        ),
        patch(
            "app.services.llm._answer_cache_key",
            return_value="test-cache-key",
        ),
        patch(
            "app.services.llm._get_cached_answer",
            return_value=None,
        ),
        patch(
            "app.services.llm._cache_answer",
        ) as mock_cache,
    ):
        with pytest.raises(LLMServiceError):
            generate_answer(
                question=SAMPLE_QUESTION,
                context_chunks=SAMPLE_CONTEXT,
                cache_scope="test-user:test-chat",
            )

    mock_cache.assert_not_called()


def test_empty_context_returns_fallback_without_calling_groq():
    with (
        patch(
            "app.services.llm.get_groq_client",
        ) as mock_client,
        patch(
            "app.services.llm.detect_toxicity",
        ) as mock_toxicity,
    ):
        answer = generate_answer(
            question=SAMPLE_QUESTION,
            context_chunks=[],
        )

    assert "couldn't find relevant information" in answer.lower()

    mock_client.assert_not_called()
    mock_toxicity.assert_not_called()
