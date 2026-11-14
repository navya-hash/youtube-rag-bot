
import json
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator


DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "evaluation_dataset.json"
)


class EvaluationSample(BaseModel):
    question_id: str
    chat_id: str
    video_id: str
    question: str = Field(min_length=1)
    relevant_chunk_ids: list[str] = Field(min_length=1)
    reference_answer: str = Field(min_length=1)

    @field_validator("chat_id", "video_id")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        try:
            UUID(value)
        except ValueError as exc:
            raise ValueError("Must be a valid UUID.") from exc
        return value

    @field_validator("question_id", "question", "reference_answer")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty.")
        return value.strip()

    @field_validator("relevant_chunk_ids")
    @classmethod
    def validate_chunk_ids(cls, value: list[str]) -> list[str]:
        if any(not chunk_id.strip() for chunk_id in value):
            raise ValueError("Chunk IDs cannot be empty.")

        if len(value) != len(set(value)):
            raise ValueError("Duplicate chunk IDs are not allowed.")

        return value


def load_evaluation_dataset(
    dataset_path: Path = DATASET_PATH,
) -> list[EvaluationSample]:
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {dataset_path}"
        )

    try:
        with dataset_path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        if not isinstance(raw_data, list):
            raise ValueError("Dataset must contain a JSON list.")

        samples = [
            EvaluationSample.model_validate(item)
            for item in raw_data
        ]

        question_ids = [sample.question_id for sample in samples]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Duplicate question IDs found.")

        if not samples:
            raise ValueError("Evaluation dataset is empty.")

        return samples

    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"Invalid evaluation dataset: {exc}"
        ) from exc
