
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_transcript(
    segments: list[dict],
    video_id: str,
    youtube_video_id: str,
    language: str,
    is_generated: bool,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[dict]:

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be non-negative and smaller than chunk_size."
        )

    clean_segments = []

    for segment in segments:
        text = str(segment.get("text", "")).strip()

        if not text:
            continue

        try:
            start = float(segment["start"])
            duration = float(segment["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Each segment needs valid start and duration values."
            ) from exc

        if start < 0 or duration < 0:
            raise ValueError("Segment timestamps cannot be negative.")

        clean_segments.append(
            {
                "text": text,
                "start": start,
                "end": start + duration,
            }
        )

    if not clean_segments:
        return []

    # Combine transcript segments and track their character positions.
    parts = []
    segment_ranges = []
    cursor = 0

    for segment in clean_segments:
        if parts:
            parts.append(" ")
            cursor += 1

        text = segment["text"]
        char_start = cursor
        char_end = char_start + len(text)

        parts.append(text)

        segment_ranges.append(
            {
                "char_start": char_start,
                "char_end": char_end,
                "start": segment["start"],
                "end": segment["end"],
            }
        )

        cursor = char_end

    full_text = "".join(parts)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
        add_start_index=True,
    )

    documents = splitter.create_documents([full_text])
    chunks = []

    for document in documents:
        raw_text = document.page_content
        char_start = document.metadata["start_index"]
        char_end = char_start + len(raw_text)

        overlapping_segments = []

        for segment in segment_ranges:
            overlap_start = max(char_start, segment["char_start"])
            overlap_end = min(char_end, segment["char_end"])

            if overlap_start >= overlap_end:
                continue

            overlapping_text = full_text[overlap_start:overlap_end]

            if any(char.isalnum() for char in overlapping_text):
                overlapping_segments.append(segment)

        if not overlapping_segments:
            continue

        text = raw_text.strip()

        if not text:
            continue

        video_start = min(s["start"] for s in overlapping_segments)
        video_end = max(s["end"] for s in overlapping_segments)
        chunk_index = len(chunks)

        # Generate a deterministic ID using the internal Neon video ID.
        chunk_id = str(
            uuid5(
                NAMESPACE_URL,
                f"youtube-rag:{video_id}:{language}:{chunk_index}:{text}",
            )
        )

        chunks.append(
            {
                "chunk_id": chunk_id,
                "video_id": video_id,
                "youtube_video_id": youtube_video_id,
                "chunk_index": chunk_index,
                "text": text,
                "start": video_start,
                "end": video_end,
                "duration": max(0.0, video_end - video_start),
                "language": language,
                "is_generated": is_generated,
            }
        )

    return chunks



# from uuid import NAMESPACE_URL, uuid5

# from langchain_text_splitters import RecursiveCharacterTextSplitter


# def chunk_transcript(
#     segments: list[dict],
#     video_id: str,
#     language: str,
#     is_generated: bool,
#     chunk_size: int = 800,
#     chunk_overlap: int = 120,
# ) -> list[dict]:
#     if chunk_size <= 0:
#         raise ValueError("chunk_size must be greater than zero.")

#     if chunk_overlap < 0 or chunk_overlap >= chunk_size:
#         raise ValueError(
#             "chunk_overlap must be non-negative and smaller than chunk_size."
#         )

#     clean_segments = []

#     for segment in segments:
#         text = str(segment.get("text", "")).strip()
#         if not text:
#             continue

#         try:
#             start = float(segment["start"])
#             duration = float(segment["duration"])
#         except (KeyError, TypeError, ValueError) as exc:
#             raise ValueError(
#                 "Each segment needs valid start and duration values."
#             ) from exc

#         if start < 0 or duration < 0:
#             raise ValueError("Segment timestamps cannot be negative.")

#         clean_segments.append(
#             {
#                 "text": text,
#                 "start": start,
#                 "end": start + duration,
#             }
#         )

#     if not clean_segments:
#         return []

#     # Join segments and record the character positions belonging
#     # to each original timestamped segment.
#     parts = []
#     segment_ranges = []
#     cursor = 0

#     for segment in clean_segments:
#         if parts:
#             parts.append(" ")
#             cursor += 1

#         text = segment["text"]
#         char_start = cursor
#         char_end = char_start + len(text)

#         parts.append(text)
#         segment_ranges.append(
#             {
#                 "char_start": char_start,
#                 "char_end": char_end,
#                 "start": segment["start"],
#                 "end": segment["end"],
#             }
#         )
#         cursor = char_end

#     full_text = "".join(parts)

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=chunk_size,
#         chunk_overlap=chunk_overlap,
#         # Avoid using punctuation as a standalone separator.
#         separators=["\n\n", "\n", " ", ""],
#         add_start_index=True,
#     )

#     documents = splitter.create_documents([full_text])
#     chunks = []

#     for document in documents:
#         raw_text = document.page_content
#         char_start = document.metadata["start_index"]
#         char_end = char_start + len(raw_text)

#         # Map the chunk to original segments that contribute
#         # actual letters or digits, not just boundary punctuation.
#         overlapping_segments = []

#         for segment in segment_ranges:
#             overlap_start = max(char_start, segment["char_start"])
#             overlap_end = min(char_end, segment["char_end"])

#             if overlap_start >= overlap_end:
#                 continue

#             overlapping_text = full_text[overlap_start:overlap_end]

#             if any(char.isalnum() for char in overlapping_text):
#                 overlapping_segments.append(segment)

#         if not overlapping_segments:
#             continue

#         text = raw_text.strip()
#         if not text:
#             continue

#         video_start = min(s["start"] for s in overlapping_segments)
#         video_end = max(s["end"] for s in overlapping_segments)
#         chunk_index = len(chunks)

#         chunk_id = str(
#             uuid5(
#                 NAMESPACE_URL,
#                 f"youtube-rag:{video_id}:{language}:{chunk_index}:{text}",
#             )
#         )

#         chunks.append(
#             {
#                 "chunk_id": chunk_id,
#                 "video_id": video_id,
#                 "chunk_index": chunk_index,
#                 "text": text,
#                 "start": video_start,
#                 "end": video_end,
#                 "duration": max(0.0, video_end - video_start),
#                 "language": language,
#                 "is_generated": is_generated,
#             }
#         )

#     return chunks
