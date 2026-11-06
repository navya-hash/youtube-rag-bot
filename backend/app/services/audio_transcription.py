
import logging
import os
from pathlib import Path
import subprocess
import tempfile

from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)

from app.services.transcript_errors import TranscriptIngestionError
from app.core.config import get_settings
logger = logging.getLogger(__name__)

MAX_VIDEO_DURATION_SECONDS = 3600
MAX_AUDIO_SIZE_BYTES = 24 * 1024 * 1024

def transcribe_audio(audio_path: Path, language: str = "en") -> dict:
    """Transcribe audio and return timestamped transcript segments."""

    api_key = get_settings().openai_api_key

    if not api_key:
        raise TranscriptIngestionError(
            "Transcription service is not configured.",
            "transcription_not_configured",
            503,
        )

    try:
        client = OpenAI(
            api_key=api_key,
            timeout=180.0,
            max_retries=2,
        )

        with audio_path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments = [
            {
                "text": segment.text.strip(),
                "start": float(segment.start),
                "duration": max(
                    0.0,
                    float(segment.end) - float(segment.start),
                ),
            }
            for segment in (response.segments or [])
            if segment.text.strip()
        ]

        if not segments:
            raise TranscriptIngestionError(
                "The transcription service returned no usable speech.",
                "empty_transcript",
                422,
            )

        return {
            "language": language,
            "is_generated": True,
            "segments": segments,
        }

    except TranscriptIngestionError:
        raise

    except AuthenticationError as exc:
        raise TranscriptIngestionError(
            "OpenAI API authentication failed. Check your API key.",
            "transcription_auth_failed",
            502,
        ) from exc

    except RateLimitError as exc:
        raise TranscriptIngestionError(
            "OpenAI API rate limit or quota exceeded.",
            "transcription_quota_exceeded",
            503,
        ) from exc

    except APITimeoutError as exc:
        raise TranscriptIngestionError(
            "The transcription request timed out.",
            "transcription_timeout",
            504,
        ) from exc

    except APIConnectionError as exc:
        raise TranscriptIngestionError(
            "Could not connect to OpenAI's transcription service.",
            "transcription_connection_failed",
            503,
        ) from exc

    except APIStatusError as exc:
        logger.warning(
            "OpenAI transcription request failed with status %s",
            exc.status_code,
        )
        raise TranscriptIngestionError(
            "OpenAI rejected the transcription request.",
            "transcription_request_failed",
            502,
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected transcription failure")
        raise TranscriptIngestionError(
            "Audio transcription failed unexpectedly.",
            "audio_transcription_failed",
            502,
        ) from exc






def download_audio(video_id: str, output_dir: Path) -> Path:
    """Download audio for a YouTube video using yt-dlp."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "audio.%(ext)s")

    command = [
        "python",
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--no-warnings",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "--match-filter",
        f"duration <= {MAX_VIDEO_DURATION_SECONDS}",
        "--max-filesize",
        "24M",
        "--output",
        output_template,
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise TranscriptIngestionError(
            "Audio download timed out.",
            "audio_download_timeout",
            504,
        ) from exc
    except subprocess.CalledProcessError as exc:
        logger.warning("yt-dlp audio download failed: %s", exc.stderr[-1000:])
        raise TranscriptIngestionError(
            "Could not download audio from this YouTube video.",
            "audio_download_failed",
            502,
        ) from exc

    audio_path = output_dir / "audio.mp3"

    if not audio_path.is_file():
        raise TranscriptIngestionError(
            "Audio download did not produce the expected MP3 file.",
            "audio_file_missing",
            502,
        )

    if audio_path.stat().st_size > MAX_AUDIO_SIZE_BYTES:
        audio_path.unlink(missing_ok=True)
        raise TranscriptIngestionError(
            "The downloaded audio exceeds the permitted size.",
            "audio_file_too_large",
            413,
        )

    if audio_path.stat().st_size == 0:
        raise TranscriptIngestionError(
            "The downloaded audio file is empty.",
            "empty_audio_file",
            502,
        )

    return audio_path


def transcribe_youtube_audio(video_id: str, language: str = "en") -> dict:
    """Download YouTube audio temporarily and transcribe it with OpenAI."""

    with tempfile.TemporaryDirectory(prefix="youtube-audio-") as temp_dir:
        audio_path = download_audio(video_id, Path(temp_dir))
        return transcribe_audio(audio_path, language)


# download_audio() invokes yt-dlp and saves the audio as an MP3.

# It checks that the download succeeded and that the file is not empty or oversized.

# transcribe_youtube_audio() creates a temporary directory, downloads the audio into it, and passes the file to your existing transcribe_audio().

# The temporary directory is cleaned up automatically after transcription finishes, including when an exception occurs.