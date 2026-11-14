
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.guardrails.toxicity_detection import (
    detect_toxicity,
    ToxicityLevel,
)
from app.services.llm import LLMServiceError


def mock_groq_response(classification, reason):
    """Create a mocked Groq response."""

    client = MagicMock()

    response = MagicMock()
    response.choices[0].message.content = json.dumps({
        "classification": classification,
        "reason": reason,
    })

    client.chat.completions.create.return_value = response

    return client


def test_safe_answer():
    client = mock_groq_response(
        "safe",
        "The answer contains educational information.",
    )

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        result = detect_toxicity(
            "Python is a popular programming language."
        )

    assert result.classification == ToxicityLevel.SAFE
    assert result.reason == "The answer contains educational information."


def test_toxic_answer():
    client = mock_groq_response(
        "toxic",
        "The answer contains abusive language.",
    )

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        result = detect_toxicity(
            "An answer containing abusive language."
        )

    assert result.classification == ToxicityLevel.TOXIC
    assert result.reason == "The answer contains abusive language."


def test_harmful_answer():
    client = mock_groq_response(
        "harmful",
        "Encourages serious physical harm.",
    )

    with patch(
        "app.services.llm.get_groq_client",
        return_value=client,
    ):
        result = detect_toxicity(
            "An answer encouraging serious physical harm."
        )

    assert result.classification == ToxicityLevel.HARMFUL
    assert result.reason == "Encourages serious physical harm."


def test_empty_answer():
    with pytest.raises(ValueError):
        detect_toxicity("   ")


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
            detect_toxicity(
                "Python is a programming language."
            )
