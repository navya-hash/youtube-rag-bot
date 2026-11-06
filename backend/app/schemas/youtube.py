

from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    url: HttpUrl
    chat_id: UUID
    language: str = Field(default="en", min_length=2, max_length=32)


class IngestResponse(BaseModel):
    video_id: UUID
    youtube_video_id: str
    chat_id: UUID
    status: str
    language: str | None = None
    is_generated: bool | None = None
    chunk_count: int = 0
    message: str


class ErrorResponse(BaseModel):
    detail: str

# from pydantic import BaseModel, Field


# class IngestRequest(BaseModel):
#     url: str
#     language: str = "en"


# class TranscriptSegment(BaseModel):
#     text: str
#     start: float
#     duration: float


# class TranscriptChunk(BaseModel):
#     chunk_id: str
#     video_id: str
#     chunk_index: int
#     text: str
#     start: float
#     end: float
#     duration: float
#     language: str
#     is_generated: bool


# class IngestResponse(BaseModel):
#     video_id: str
#     language: str
#     is_generated: bool
#     segment_count: int
#     transcript: list[TranscriptSegment]
#     chunk_count: int
#     chunks: list[TranscriptChunk]


# class ErrorResponse(BaseModel):
#     detail: str


# from pydantic import BaseModel, Field


# class IngestRequest(BaseModel):
#     url: str = Field(
#         min_length=1,
#         max_length=2048,
#         description="YouTube video URL",
#     )


# class TranscriptSegment(BaseModel):
#     text: str
#     start: float
#     duration: float


# class IngestResponse(BaseModel):
#     video_id: str
#     segment_count: int
#     transcript: list[TranscriptSegment]


# IngestRequest validates incoming JSON.

# Field places basic limits on the URL's length.

# TranscriptSegment describes one caption segment.

# IngestResponse ensures the API returns a predictable structure.
