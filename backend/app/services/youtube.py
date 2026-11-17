
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

from app.services.transcript_errors import TranscriptIngestionError
import logging

from app.services.audio_transcription import transcribe_youtube_audio
import time
import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)


VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    """Extract a video ID from supported YouTube URL formats."""

    if not url or not url.strip():
        raise TranscriptIngestionError(
            "Please provide a YouTube URL.",
            "invalid_url",
            422,
        )

    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    video_id = None

    if host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
    }:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]

        elif parsed.path.startswith(("/shorts/", "/live/", "/embed/")):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 2:
                video_id = parts[1]

    elif host == "youtu.be":
        parts = parsed.path.strip("/").split("/")
        if parts:
            video_id = parts[0]

    if not video_id or not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise TranscriptIngestionError(
            "Invalid or unsupported YouTube URL.",
            "invalid_url",
            422,
        )

    return video_id

# urlparse() separates a URL into its host, path and query parameters.

# # parse_qs() reads query parameters such as v=abcdefghijk.

# # YouTube IDs are typically 11 characters; the regular expression validates their format
def fetch_transcript(
    video_id: str,
    language: str = "en",
) -> dict:
    """
    Fetch captions, preferring the requested language,
    then English, then the first available caption track.
    """

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise TranscriptIngestionError(
            "Invalid YouTube video ID.",
            "invalid_video_id",
            422,
        )

    if not re.fullmatch(r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*", language):
        raise TranscriptIngestionError(
            "Invalid language code.",
            "invalid_language",
            422,
        )

    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)

        try:
            selected = transcript_list.find_transcript([language])
        except Exception as exc:
            if type(exc).__name__ != "NoTranscriptFound":
                raise

            if language.lower() != "en":
                try:
                    selected = transcript_list.find_transcript(["en"])
                except Exception as fallback_exc:
                    if type(fallback_exc).__name__ != "NoTranscriptFound":
                        raise
                    selected = next(iter(transcript_list))
            else:
                selected = next(iter(transcript_list))

        fetched = selected.fetch()
        raw_segments = fetched.to_raw_data()

        segments = [
            {
                "text": item["text"].strip(),
                "start": float(item["start"]),
                "duration": float(item["duration"]),
            }
            for item in raw_segments
            if item.get("text", "").strip()
        ]

        if not segments:
            raise TranscriptIngestionError(
                "The video transcript is empty.",
                "empty_transcript",
                422,
            )

        return {
            "language": getattr(fetched, "language_code", language),
            "is_generated": getattr(selected, "is_generated", None),
            "segments": segments,
        }

    except TranscriptIngestionError:
        raise

    except Exception as exc:
        error_type = type(exc).__name__

        # Map known upstream failures into stable application errors.
        if error_type in {"VideoUnavailable", "InvalidVideoId"}:
            raise TranscriptIngestionError(
                "This YouTube video is unavailable or invalid.",
                "video_unavailable",
                404,
            ) from exc

        if error_type in {"TranscriptsDisabled", "NoTranscriptFound"}:
            raise TranscriptIngestionError(
                "No usable captions are available for this video.",
                "captions_unavailable",
                422,
            ) from exc

        if error_type in {
            "RequestBlocked",
            "IpBlocked",
            "YouTubeRequestFailed",
            "PoTokenRequired",
        }:
            raise TranscriptIngestionError(
                "YouTube temporarily blocked or rejected the transcript request.",
                "transcript_upstream_unavailable",
                503,
            ) from exc

        # Preserve the original exception for server-side debugging.
        raise TranscriptIngestionError(
            "The transcript service failed unexpectedly.",
            "transcript_service_error",
            502,
        ) from exc



def fetch_transcript_from_supadata(
    video_id: str,
    language: str = "en",
) -> dict:
    """Fetch and normalize a YouTube transcript using Supadata."""

    settings = get_settings()
    api_key = settings.supadata_api_key

    if not api_key:
        raise TranscriptIngestionError(
            "Supadata API key is not configured.",
            "supadata_not_configured",
            503,
        )

    url = f"https://www.youtube.com/watch?v={video_id}"

    headers = {
        "x-api-key": api_key,
        "Accept": "application/json",
    }

    params = {
        "url": url,
        "lang": language,
        "mode": "auto",
        "text": "false",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                "https://api.supadata.ai/v1/transcript",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            result = response.json()

            # Long videos may return a job ID instead
            # of the transcript immediately.
            job_id = result.get("jobId")

            if job_id:
                for attempt in range(45):
                    time.sleep(2)

                    job_response = client.get(
                        f"https://api.supadata.ai/v1/transcript/{job_id}",
                        headers=headers,
                    )
                    job_response.raise_for_status()

                    result = job_response.json()
                    status = result.get("status")

                    if status == "completed":
                        result = (
                            result.get("result")
                            or result.get("data")
                            or result
                        )
                        break

                    if status == "failed":
                        raise TranscriptIngestionError(
                            "Supadata could not process this video.",
                            "supadata_job_failed",
                            502,
                        )

                else:
                    raise TranscriptIngestionError(
                        "Supadata transcript processing timed out.",
                        "supadata_timeout",
                        504,
                    )

            # Handle the transcript response.
            content = result.get("content")
            transcript_language = result.get("lang", language)

            if isinstance(content, str):
                content = [{
                    "text": content,
                    "offset": 0,
                    "duration": 0,
                }]

            if not isinstance(content, list) or not content:
                raise TranscriptIngestionError(
                    "Supadata returned an empty transcript.",
                    "empty_transcript",
                    422,
                )

            segments = []

            for item in content:
                text = item.get("text", "").strip()

                if not text:
                    continue

                segments.append({
                    "text": text,
                    "start": float(item.get("offset", 0)) / 1000,
                    "duration": float(item.get("duration", 0)) / 1000,
                })

            if not segments:
                raise TranscriptIngestionError(
                    "Supadata returned no usable transcript segments.",
                    "empty_transcript",
                    422,
                )

            logger.info(
                "Supadata transcript retrieved for video %s. "
                "Language: %s, segments: %s",
                video_id,
                transcript_language,
                len(segments),
            )

            return {
                "language": transcript_language,
                "is_generated": None,
                "segments": segments,
            }

    except TranscriptIngestionError:
        raise

    except httpx.HTTPStatusError as exc:
        logger.exception(
            "Supadata HTTP error for video %s: %s",
            video_id,
            exc.response.status_code,
        )
        raise TranscriptIngestionError(
            "Supadata could not retrieve this video's transcript.",
            "supadata_api_error",
            502,
        ) from exc

    except (httpx.RequestError, ValueError, KeyError) as exc:
        logger.exception(
            "Supadata request or response error for video %s",
            video_id,
        )
        raise TranscriptIngestionError(
            "Supadata transcript service is temporarily unavailable.",
            "supadata_service_error",
            502,
        ) from exc



def fetch_transcript_with_fallback(
    video_id: str,
    language: str = "en",
) -> dict:
    """
    Try Supadata first, then YouTube captions,
    and finally OpenAI Whisper.
    """

    # First: Supadata
    try:
        return fetch_transcript_from_supadata(
            video_id,
            language,
        )

    except TranscriptIngestionError as exc:
        logger.warning(
            "Supadata failed for video %s (%s). "
            "Trying YouTube Transcript API.",
            video_id,
            exc.code,
        )

    # Second: Existing YouTube Transcript API
    try:
        return fetch_transcript(
            video_id,
            language,
        )

    except TranscriptIngestionError as exc:
        fallback_codes = {
            "captions_unavailable",
            "transcript_upstream_unavailable",
            "transcript_service_error",
        }

        if exc.code not in fallback_codes:
            raise

        logger.warning(
            "YouTube captions unavailable for video %s (%s). "
            "Trying OpenAI Whisper.",
            video_id,
            exc.code,
        )

    # Third: Existing Whisper fallback
    return transcribe_youtube_audio(
        video_id,
        language,
    )
