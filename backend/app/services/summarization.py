
import json
import logging
import re
import uuid
from typing import Callable
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Video
from app.services.llm import get_groq_client, get_settings
from app.services.vector_store import get_all_video_chunks
from app.db.repository import save_video_summary


logger = logging.getLogger(__name__)

# Maximum approximate transcript characters sent in one map request.
MAX_GROUP_CHARS = 12000

# Number of intermediate summaries combined in one reduce request.
REDUCE_BATCH_SIZE = 8


class SummarizationError(Exception):
    """Raised when video summarization fails."""


def _get_chunk_payload(chunk: dict) -> dict:
    """Support both Qdrant point objects and flattened chunk dictionaries."""
    payload = chunk.get("payload")
    return payload if isinstance(payload, dict) else chunk


def _format_chunk(chunk: dict) -> str:
    """Format a transcript chunk with its timestamp information."""
    payload = _get_chunk_payload(chunk)

    text = str(payload.get("text", "")).strip()
    start = payload.get("start", 0)
    end = payload.get("end", 0)

    if not text:
        return ""

    return f"[{start}s - {end}s] {text}"


def _group_chunks(chunks: list[dict]) -> list[list[str]]:
    """Group ordered transcript chunks into manageable batches."""
    groups = []
    current_group = []
    current_length = 0

    for chunk in chunks:
        formatted = _format_chunk(chunk)

        if not formatted:
            continue

        if current_group and current_length + len(formatted) > MAX_GROUP_CHARS:
            groups.append(current_group)
            current_group = []
            current_length = 0

        current_group.append(formatted)
        current_length += len(formatted)

    if current_group:
        groups.append(current_group)

    return groups


def _call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Call the existing configured Groq client."""
    client = get_groq_client()
    settings = get_settings()

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content

    if not content:
        raise SummarizationError("The language model returned an empty response.")

    return content.strip()


def _parse_json_response(content: str) -> dict:
    """Parse JSON while handling common Markdown formatting mistakes."""
    cleaned = content.strip()

    # Remove optional Markdown code fences.
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SummarizationError(
            "The language model returned invalid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise SummarizationError("The model response must be a JSON object.")

    return result


def _summarize_group(
    group: list[str],
    group_number: int,
    language: str = "English",
) -> str:
    """Map step: summarize one section in the requested language."""

    transcript = "\n".join(group)

    system_prompt = f"""
You are an expert video-content analyst.

Your task is to summarize the provided transcript section accurately.

OUTPUT LANGUAGE:
Write your entire response in {language}.

Rules:
- Use only information present in the transcript.
- Preserve important concepts, explanations, examples, and conclusions.
- Retain timestamps when they help identify important moments.
- Do not invent facts or fill gaps with outside knowledge.
- Avoid unnecessary repetition.
- Return a concise but informative intermediate summary.
- Keep technical terms, programming terminology, and proper nouns
  accurate. Use their commonly accepted forms where appropriate.
- Do not switch to another language unless required for a proper noun
  or technical term.
"""

    user_prompt = f"""
Summarize transcript section {group_number}.

Write the summary in {language}.

TRANSCRIPT:
{transcript}
"""

    return _call_groq(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=1800,
    )


def _reduce_summaries(
    summaries: list[str],
    language: str = "English",
) -> str:
    """Reduce step: combine intermediate summaries."""

    combined = "\n\n".join(
        f"SECTION {index + 1}:\n{summary}"
        for index, summary in enumerate(summaries)
    )

    system_prompt = f"""
You are an expert at combining summaries of different sections of a video.

Create a unified summary from the supplied intermediate summaries.

OUTPUT LANGUAGE:
Write your entire response in {language}.

Rules:
- Preserve all important ideas across sections.
- Remove repetition and merge related explanations.
- Maintain the logical flow of the original video.
- Preserve important timestamps where available.
- Do not introduce information that is not present in the summaries.
- Maintain accurate technical terminology and proper nouns.
- Do not switch to another language unnecessarily.
- Ensure the final combined summary is coherent and informative.
"""

    user_prompt = f"""
Combine these section summaries into one unified summary.

Write the result in {language}.

SECTION SUMMARIES:
{combined}
"""

    return _call_groq(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2500,
    )

def _build_final_summary(
    reduced_summary: str,
    language: str = "English",
) -> dict:
    """Generate the final structured summary in the requested language."""

    system_prompt = f"""
You are an expert video summarization assistant.

OUTPUT LANGUAGE:
Generate every user-facing text value in {language}.

Return ONLY a valid JSON object with this exact structure:

{{
  "summary": "A detailed, coherent summary of the video.",
  "key_points": [
    "Important takeaway 1",
    "Important takeaway 2"
  ],
  "topics": [
    "Topic 1",
    "Topic 2"
  ]
}}

Rules:
- Use only information in the supplied material.
- The summary should explain the main ideas, not merely list keywords.
- Key points should be concise and useful.
- Topics should be short subject labels.
- Translate the summary, key points, and topics into {language}.
- Preserve technical terms, programming terminology, and proper nouns
  accurately where appropriate.
- Do not add information from outside the supplied material.
- Do not include Markdown code fences.
- Do not add any fields outside the requested structure.
- Return valid JSON with correctly escaped strings.
"""

    user_prompt = f"""
Create the final video summary from the following material.

All text values must be written in {language}.

MATERIAL:
{reduced_summary}
"""

    content = _call_groq(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=3500,
    )

    result = _parse_json_response(content)

    summary = result.get("summary")
    key_points = result.get("key_points")
    topics = result.get("topics")

    if not isinstance(summary, str) or not summary.strip():
        raise SummarizationError(
            "The final summary is missing or invalid."
        )

    if not isinstance(key_points, list) or not all(
        isinstance(item, str) and item.strip()
        for item in key_points
    ):
        raise SummarizationError(
            "The model returned invalid key points."
        )

    if not isinstance(topics, list) or not all(
        isinstance(item, str) and item.strip()
        for item in topics
    ):
        raise SummarizationError(
            "The model returned invalid topics."
        )

    return {
        "summary": summary.strip(),
        "key_points": key_points,
        "topics": topics,
    }


def summarize_video(
    db: Session,
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    language: str = "English",
    heartbeat: Callable[[], None] | None = None,
):
    """
    Generate and persist a complete summary for one user's video
    in the requested output language.
    """

    # 1. Verify video ownership.
    video_statement = select(Video).where(
        Video.id == video_id,
        Video.owner_id == owner_id,
    )
    video = db.scalar(video_statement)

    if not video:
        raise SummarizationError("Video not found or access denied.")

    if video.status != "completed":
        raise SummarizationError(
            "The video must finish ingestion before it can be summarized."
        )

    # 2. Retrieve ALL transcript chunks.
    chunks = get_all_video_chunks(
        owner_id=owner_id,
        video_id=video_id,
    )

    if not chunks:
        raise SummarizationError(
            "No transcript chunks were found for this video."
        )

    # 3. Group transcript chunks chronologically.
    groups = _group_chunks(chunks)

    if not groups:
        raise SummarizationError(
            "The transcript does not contain usable text."
        )

    logger.info(
        "Starting summarization for video %s in %s: %d chunks, %d groups",
        video_id,
        language,
        len(chunks),
        len(groups),
    )

    def send_heartbeat():
        if heartbeat:
            heartbeat()

    try:
        # 4. Map: summarize each transcript group.
        intermediate_summaries = []

        for index, group in enumerate(groups):
            send_heartbeat()

            summary = _summarize_group(
                group,
                index + 1,
                language=language,
            )

            intermediate_summaries.append(summary)

            send_heartbeat()

        # 5. Hierarchical reduce.
        while len(intermediate_summaries) > REDUCE_BATCH_SIZE:
            reduced_batches = []

            for index in range(
                0,
                len(intermediate_summaries),
                REDUCE_BATCH_SIZE,
            ):
                send_heartbeat()

                batch = intermediate_summaries[
                    index:index + REDUCE_BATCH_SIZE
                ]

                reduced_batches.append(
                    _reduce_summaries(
                        batch,
                        language=language,
                    )
                )

                send_heartbeat()

            intermediate_summaries = reduced_batches

        # 6. Final reduce and structured output.
        send_heartbeat()

        combined_summary = _reduce_summaries(
            intermediate_summaries,
            language=language,
        )

        send_heartbeat()

        final_result = _build_final_summary(
            combined_summary,
            language=language,
        )

        send_heartbeat()

        # 7. Persist language-specific summary in Neon.
        settings = get_settings()

        saved_summary = save_video_summary(
            db=db,
            video_id=video_id,
            owner_id=owner_id,
            summary=final_result["summary"],
            key_points=final_result["key_points"],
            topics=final_result["topics"],
            model_name=settings.groq_model,
            language=language,
        )

        logger.info(
            "Successfully summarized video %s in %s",
            video_id,
            language,
        )

        return {
            "id": str(saved_summary.id),
            "video_id": str(saved_summary.video_id),
            "summary": saved_summary.summary,
            "key_points": saved_summary.key_points,
            "topics": saved_summary.topics,
            "status": saved_summary.status,
            "model_name": saved_summary.model_name,
            "language": saved_summary.language,
        }

    except Exception:
        logger.exception(
            "Summarization failed for video %s in %s",
            video_id,
            language,
        )
        raise
