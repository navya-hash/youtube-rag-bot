
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.guardrails.hallucination_detection import (
    verify_answer_claims,
    ClaimStatus,
)
from app.services.llm import LLMServiceError


def mock_groq_response(claims):
    """Create a mocked Groq response containing verification results."""

    client = MagicMock()

    response = MagicMock()
    response.choices[0].message.content = json.dumps({
        "claims": claims
    })

    client.chat.completions.create.return_value = response

    return client


def test_supported_claim():
    client = mock_groq_response([
        {
            "claim": "Python was created by Guido van Rossum.",
            "status": "supported",
            "evidence": (
                "The transcript identifies Guido van Rossum "
                "as Python's creator."
            ),
        }
    ])

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        result = verify_answer_claims(
            answer="Python was created by Guido van Rossum.",
            context_chunks=[
                {
                    "text": (
                        "Python was created by Guido van Rossum."
                    )
                }
            ],
        )

    assert len(result.claims) == 1
    assert result.claims[0].status == ClaimStatus.SUPPORTED
    assert result.is_fully_supported
    assert len(result.unsupported_claims) == 0


def test_unsupported_claim():
    client = mock_groq_response([
        {
            "claim": "Python is the fastest programming language.",
            "status": "unsupported",
            "evidence": "",
        }
    ])

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        result = verify_answer_claims(
            answer="Python is the fastest programming language.",
            context_chunks=[
                {
                    "text": (
                        "Python is a high-level programming language."
                    )
                }
            ],
        )

    assert len(result.claims) == 1
    assert result.claims[0].status == ClaimStatus.UNSUPPORTED
    assert not result.is_fully_supported
    assert len(result.unsupported_claims) == 1


def test_contradicted_claim():
    client = mock_groq_response([
        {
            "claim": "Python was released in 2000.",
            "status": "contradicted",
            "evidence": (
                "The transcript says Python was released in 1991."
            ),
        }
    ])

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        result = verify_answer_claims(
            answer="Python was released in 2000.",
            context_chunks=[
                {
                    "text": (
                        "Python was first released in 1991."
                    )
                }
            ],
        )

    assert len(result.claims) == 1
    assert result.claims[0].status == ClaimStatus.CONTRADICTED
    assert not result.is_fully_supported
    assert len(result.unsupported_claims) == 1


def test_empty_context():
    result = verify_answer_claims(
        answer="Python was created by Guido van Rossum.",
        context_chunks=[],
    )

    assert result.claims == []
    assert not result.is_fully_supported
    assert result.unsupported_claims == []


def test_classifier_failure():
    client = MagicMock()

    client.chat.completions.create.side_effect = Exception(
        "API unavailable"
    )

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        with pytest.raises(LLMServiceError):
            verify_answer_claims(
                answer="Python was created by Guido van Rossum.",
                context_chunks=[
                    {
                        "text": (
                            "Python was created by Guido van Rossum."
                        )
                    }
                ],
            )
