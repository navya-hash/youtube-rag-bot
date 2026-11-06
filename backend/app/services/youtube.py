
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

from app.services.transcript_errors import TranscriptIngestionError
import logging

from app.services.audio_transcription import transcribe_youtube_audio



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



def fetch_transcript_with_fallback(
    video_id: str,
    language: str = "en",
) -> dict:
    """Fetch captions first, then use OpenAI when captions cannot be obtained."""

    try:
        return fetch_transcript(video_id, language)

    except TranscriptIngestionError as exc:
        # Never use the fallback for invalid input or unavailable videos.
        fallback_codes = {
            "captions_unavailable",
            "transcript_upstream_unavailable",
            "transcript_service_error",
        }

        if exc.code not in fallback_codes:
            raise

        logger.warning(
            "Captions unavailable for video %s (%s). "
            "Trying OpenAI transcription.",
            video_id,
            exc.code,
        )

        return transcribe_youtube_audio(video_id, language)


# import re
# from urllib.parse import parse_qs, urlparse

# from youtube_transcript_api import (
#     YouTubeTranscriptApi,
# )
# from youtube_transcript_api._errors import (
#     NoTranscriptFound,
#     TranscriptsDisabled,
#     VideoUnavailable,
# )

# VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


# def extract_video_id(url: str) -> str:
#     """Extract and validate the 11-character YouTube video ID."""

#     if not url or not url.strip():
#         raise ValueError("Please provide a YouTube URL.")

#     parsed = urlparse(url.strip())
#     host = (parsed.hostname or "").lower()
#     video_id = None

#     # Standard watch URL: youtube.com/watch?v=VIDEO_ID
#     if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
#         if parsed.path == "/watch":
#             video_id = parse_qs(parsed.query).get("v", [None])[0]

#         # Shorts and live URLs
#         elif parsed.path.startswith("/shorts/"):
#             video_id = parsed.path.split("/")[2]

#         elif parsed.path.startswith("/live/"):
#             video_id = parsed.path.split("/")[2]

#         elif parsed.path.startswith("/embed/"):
#             video_id = parsed.path.split("/")[2]

#     # Short URL: youtu.be/VIDEO_ID
#     elif host == "youtu.be":
#         video_id = parsed.path.strip("/").split("/")[0]

#     if not video_id or not VIDEO_ID_PATTERN.fullmatch(video_id):
#         raise ValueError("Invalid or unsupported YouTube URL.")

#     return video_id

# # urlparse() separates a URL into its host, path and query parameters.

# # parse_qs() reads query parameters such as v=abcdefghijk.

# # YouTube IDs are typically 11 characters; the regular expression validates their format.

# def fetch_transcript(video_id: str) -> list[dict]:
#     """
#     Fetch captions and return normalized transcript segments.

#     Each segment contains text, start time, and duration.
#     """
#     api = YouTubeTranscriptApi()

#     try:
#         transcript = api.fetch(video_id, languages=["en"])
#         segments = transcript.to_raw_data()

#     except NoTranscriptFound:
#         raise ValueError(
#             "No English captions were found for this video."
#         ) from None

#     except TranscriptsDisabled:
#         raise ValueError(
#             "Captions are disabled for this video."
#         ) from None

#     except VideoUnavailable:
#         raise ValueError(
#             "This YouTube video is unavailable."
#         ) from None

#     normalized = []

#     for segment in segments:
#         text = segment.get("text", "").strip()

#         if not text:
#             continue

#         normalized.append({
#             "text": text,
#             "start": float(segment["start"]),
#             "duration": float(segment["duration"]),
#         })

#     if not normalized:
#         raise ValueError("The transcript is empty.")

#     return normalized