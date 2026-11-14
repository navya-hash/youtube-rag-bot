
import json
import logging
import re
import time
from typing import Any, Callable

from groq import RateLimitError

from app.core.config import get_settings
from app.services.llm import get_groq_client

logger = logging.getLogger(__name__)


def is_rate_limit_error(exc: Exception) -> bool:
    """Check whether an exception represents a 429 rate limit error."""
    if isinstance(exc, RateLimitError):
        return True
    if getattr(exc, "status_code", None) == 429:
        return True
    cause = getattr(exc, "__cause__", None)
    if cause and is_rate_limit_error(cause):
        return True
    msg = str(exc).lower()
    return "rate limit" in msg or "429" in msg or "too many requests" in msg


def extract_retry_delay(exc: Exception, default_delay: float = 5.0) -> float:
    """Extract recommended retry delay from response headers or message."""
    response = getattr(exc, "response", None)
    if response and hasattr(response, "headers"):
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except (ValueError, TypeError):
                pass

    cause = getattr(exc, "__cause__", None)
    if cause:
        return extract_retry_delay(cause, default_delay)

    msg = str(exc)
    match = re.search(r"try again in ([\d\.]+)s", msg, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1)) + 1.0
        except (ValueError, TypeError):
            pass

    return default_delay


def call_with_rate_limit_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    **kwargs: Any,
) -> Any:
    """Execute a callable with bounded exponential backoff on Groq 429 rate limit errors."""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if not is_rate_limit_error(exc) or attempt >= max_retries:
                if is_rate_limit_error(exc):
                    logger.error(
                        "Groq rate limit retries exhausted for %s after %d attempts: %s",
                        getattr(func, "__name__", str(func)),
                        max_retries,
                        exc,
                    )
                raise
            delay = extract_retry_delay(exc, base_delay * (2 ** attempt))
            delay = min(max(delay, base_delay), max_delay)
            logger.warning(
                "Groq rate limit (429) during %s (attempt %d/%d). Sleeping for %.2f seconds before retry...",
                getattr(func, "__name__", str(func)),
                attempt + 1,
                max_retries,
                delay,
            )
            time.sleep(delay)


def evaluate_faithfulness(
    question: str,
    context_chunks: list[dict],
    answer: str,
) -> dict:
    """
    Evaluate whether the generated answer is supported
    by the retrieved transcript context.
    """

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not answer.strip():
        raise ValueError("Answer cannot be empty.")

    if not context_chunks:
        raise ValueError("Context chunks cannot be empty.")

    context = "\n\n".join(
        chunk.get("text", "")
        for chunk in context_chunks
        if chunk.get("text")
    )

    if not context.strip():
        raise ValueError("Retrieved context contains no text.")

    system_prompt = """
You are an expert RAG evaluation judge.

Your task is to evaluate the faithfulness of a generated answer.

Faithfulness means whether the factual claims in the answer
are supported by the provided context.

Instructions:
1. Break the answer into individual factual claims.
2. Check each claim against the provided context.
3. A claim is supported only if the context provides evidence
   for it.
4. Do not use your external knowledge.
5. Do not treat unsupported claims as correct just because
   they sound reasonable.
6. Ignore stylistic differences and judge factual grounding.
7. If a claim is only partially supported, classify it as
   unsupported.

Return ONLY valid JSON in this format:

{
    "total_claims": 4,
    "supported_claims": 3,
    "unsupported_claims": 1,
    "faithfulness_score": 0.75,
    "reason": "One claim was not supported by the context."
}
"""

    user_prompt = f"""
Question:
{question}

Retrieved context:
{context}

Generated answer:
{answer}

Evaluate the faithfulness of the generated answer.
"""

    try:
        settings = get_settings()
        client = get_groq_client()

        completion = call_with_rate_limit_retry(
            client.chat.completions.create,
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_completion_tokens=2048,
        )

        choice = completion.choices[0]
        raw_response = choice.message.content

        if not raw_response or not raw_response.strip():
            logger.error(
                "Evaluation model returned an empty response. "
                "finish_reason=%s, usage=%s",
                choice.finish_reason,
                completion.usage,
            )
            raise ValueError("Evaluation model returned an empty response.")

        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.strip("`")
            if clean_json.startswith("json"):
                clean_json = clean_json[4:]
            clean_json = clean_json.strip()

        try:
            result = json.loads(clean_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON response from evaluation model: {exc}") from exc

        if not isinstance(result, dict):
            raise ValueError("Evaluation result must be a JSON object.")

        if (
            "total_claims" not in result
            or "supported_claims" not in result
            or "unsupported_claims" not in result
        ):
            raise ValueError("Evaluation model returned invalid scores.")

        total = result["total_claims"]
        supported = result["supported_claims"]
        unsupported = result["unsupported_claims"]
        score = result.get("faithfulness_score")

        if (
            not isinstance(total, int)
            or isinstance(total, bool)
            or not isinstance(supported, int)
            or isinstance(supported, bool)
            or not isinstance(unsupported, int)
            or isinstance(unsupported, bool)
            or total < 0
            or supported < 0
            or unsupported < 0
            or supported + unsupported != total
        ):
            raise ValueError("Evaluation model returned invalid scores.")

        # Explicitly handle zero total claims and calculate authoritative faithfulness score
        if total == 0:
            authoritative_score = 1.0
        else:
            authoritative_score = supported / total

        # If reported score is present, validate that it is a valid numeric score in [0, 1]
        if score is not None:
            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not (0 <= score <= 1)
            ):
                raise ValueError("Evaluation model returned invalid scores.")

        if not isinstance(result.get("reason"), str):
            raise ValueError("Evaluation reason must be a string.")

        result["faithfulness_score"] = authoritative_score
        return result

    except Exception:
        logger.exception("Faithfulness evaluation failed.")
        raise



def evaluate_answer_relevance(
    question: str,
    answer: str,
) -> dict:
    """Evaluate how relevant the generated answer is to the question."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not answer.strip():
        raise ValueError("Answer cannot be empty.")

    system_prompt = """
You are an expert RAG evaluation judge.

Evaluate how relevant the generated answer is to the user's question.

Consider:
1. Does the answer directly address the question?
2. Does it cover the important aspects of the question?
3. Does it contain unnecessary or unrelated information?

Do not evaluate factual correctness or faithfulness.
Evaluate relevance only.

Return ONLY valid JSON:

{
    "relevance_score": 0.9,
    "reason": "The answer directly addresses the question."
}

The relevance_score must be between 0 and 1.
"""

    user_prompt = f"""
Question:
{question}

Generated answer:
{answer}

Evaluate the answer relevance.
"""

    try:
        settings = get_settings()
        client = get_groq_client()

        completion = call_with_rate_limit_retry(
            client.chat.completions.create,
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_completion_tokens=2048,
        )

        choice = completion.choices[0]
        raw_response = choice.message.content

        if not raw_response or not raw_response.strip():
            logger.error(
                "Empty relevance response. Finish reason: %s, Usage: %s",
                choice.finish_reason,
                completion.usage,
            )
            raise ValueError("Evaluation model returned an empty response.")

        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.strip("`")
            if clean_json.startswith("json"):
                clean_json = clean_json[4:]
            clean_json = clean_json.strip()

        result = json.loads(clean_json)

        score = result["relevance_score"]

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 1
        ):
            raise ValueError("Invalid relevance score.")

        if not isinstance(result.get("reason"), str):
            raise ValueError("Evaluation reason must be a string.")

        return result

    except Exception:
        logger.exception("Answer relevance evaluation failed.")
        raise



def evaluate_answer_correctness(
    question: str,
    answer: str,
    reference_answer: str,
) -> dict:
    """Evaluate generated answer against a trusted reference answer."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not answer.strip():
        raise ValueError("Generated answer cannot be empty.")

    if not reference_answer.strip():
        raise ValueError("Reference answer cannot be empty.")

    system_prompt = """
You are an expert answer correctness evaluator.

Compare the generated answer with the trusted reference answer.

Evaluate:
1. Factual alignment with the reference answer.
2. Whether the important information in the reference is covered.
3. Whether the generated answer contains contradictory claims.
4. Whether additional information is reasonable and consistent
   with the reference.

Do not require exact wording.
Semantically equivalent answers should receive high scores.

Return ONLY valid JSON:

{
    "correctness_score": 0.9,
    "reason": "The generated answer correctly covers the main points."
}

The correctness_score must be between 0 and 1.
"""

    user_prompt = f"""
Question:
{question}

Reference answer:
{reference_answer}

Generated answer:
{answer}

Evaluate answer correctness.
"""

    try:
        settings = get_settings()
        client = get_groq_client()

        completion = call_with_rate_limit_retry(
            client.chat.completions.create,
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_completion_tokens=2048,
        )

        choice = completion.choices[0]
        raw_response = choice.message.content

        if not raw_response or not raw_response.strip():
            logger.error(
                "Empty correctness response. Finish reason: %s, Usage: %s",
                choice.finish_reason,
                completion.usage,
            )
            raise ValueError("Evaluation model returned an empty response.")

        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.strip("`")
            if clean_json.startswith("json"):
                clean_json = clean_json[4:]
            clean_json = clean_json.strip()

        result = json.loads(clean_json)

        score = result["correctness_score"]

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 1
        ):
            raise ValueError("Invalid correctness score.")

        if not isinstance(result.get("reason"), str):
            raise ValueError("Evaluation reason must be a string.")

        return result

    except Exception:
        logger.exception("Answer correctness evaluation failed.")
        raise


