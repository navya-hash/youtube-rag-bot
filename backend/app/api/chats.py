
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import require_user
from app.db.session import get_db
from app.db.repository import (
    get_or_create_user,
    create_chat,
    list_chats,
    get_owned_chat,
    list_messages,
    save_message,
    update_chat_language,
)
from app.services.retrieval import (
    retrieve_relevant_chunks,
    RetrievalError,
)
from app.services.llm import (
    generate_answer,
    rewrite_question,
    LLMServiceError,
)
from app.core.languages import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chats", tags=["Chats"])


class CreateChatRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=200)
    output_language: str = Field(default=DEFAULT_LANGUAGE)

class UpdateChatLanguageRequest(BaseModel):
    output_language: str = Field(min_length=1, max_length=50)


class MessageRequest(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=50000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)


def resolve_user(db: Session, clerk_user_id: str):
    return get_or_create_user(db, clerk_user_id)


def validate_output_language(language: str) -> str:
    language = language.strip()

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported output language.",
                "supported_languages": SUPPORTED_LANGUAGES,
            },
        )

    return language
@router.post("")
def create_chat_endpoint(
    payload: CreateChatRequest,
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    user = resolve_user(db, clerk_user_id)
    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Chat title cannot be empty",
        )

    output_language = validate_output_language(
    payload.output_language
)

    chat = create_chat(
        db=db,
        owner_id=user.id,
        title=title,
        output_language=output_language,
    )

    return {
    "id": str(chat.id),
    "title": chat.title,
    "output_language": chat.output_language,
    "created_at": chat.created_at.isoformat(),
    "updated_at": chat.updated_at.isoformat(),
}


@router.get("")
def list_chats_endpoint(
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    user = resolve_user(db, clerk_user_id)

    return [
        {
            "id": str(chat.id),
            "title": chat.title,
            "output_language": chat.output_language,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
        }
        for chat in list_chats(db, user.id)
    ]


@router.get("/{chat_id}")
def get_chat_endpoint(
    chat_id: uuid.UUID,
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    user = resolve_user(db, clerk_user_id)
    chat = get_owned_chat(db, chat_id, user.id)

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    messages = list_messages(db, chat)

    return {
        "id": str(chat.id),
        "title": chat.title,
        "output_language": chat.output_language,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat(),
        "messages": [
    {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "citations": message.citations,
        "output_language": message.output_language,
        "created_at": message.created_at.isoformat(),
    }
    for message in messages
],
    }


@router.patch("/{chat_id}/language")
def update_chat_language_endpoint(
    chat_id: uuid.UUID,
    payload: UpdateChatLanguageRequest,
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    # 1. Authenticate user and verify chat ownership.
    user = resolve_user(db, clerk_user_id)
    chat = get_owned_chat(db, chat_id, user.id)

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    # 2. Validate the requested language.
    output_language = validate_output_language(
        payload.output_language
    )

    # 3. Update the existing chat.
    chat = update_chat_language(
        db=db,
        chat=chat,
        output_language=output_language,
    )

    return {
        "message": "Chat output language updated successfully.",
        "chat_id": str(chat.id),
        "output_language": chat.output_language,
        "updated_at": chat.updated_at.isoformat(),
    }

@router.post("/{chat_id}/messages")
def add_message_endpoint(
    chat_id: uuid.UUID,
    payload: MessageRequest,
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    user = resolve_user(db, clerk_user_id)
    chat = get_owned_chat(db, chat_id, user.id)

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    if payload.role not in {"user", "assistant"}:
        raise HTTPException(
            status_code=422,
            detail="role must be 'user' or 'assistant'",
        )

    content = payload.content.strip()

    if not content:
        raise HTTPException(
            status_code=422,
            detail="Message cannot be empty",
        )

    message = save_message(
        db=db,
        chat=chat,
        role=payload.role,
        content=content,
        output_language=chat.output_language,
    )

    return {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "output_language": message.output_language,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


@router.post("/{chat_id}/ask")
def ask_question_endpoint(
    chat_id: uuid.UUID,
    payload: AskRequest,
    clerk_user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    # 1. Authenticate user and verify chat ownership.
    user = resolve_user(db, clerk_user_id)
    chat = get_owned_chat(db, chat_id, user.id)

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty",
        )

    # 2. Fetch recent conversation history.
    previous_messages = list_messages(db, chat)

    conversation_history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in previous_messages[-10:]
        if message.role in {"user", "assistant"}
    ]

    # 3. Rewrite the question to resolve follow-up references.
    try:
        standalone_question = rewrite_question(
            question=question,
            conversation_history=conversation_history,
        )
    except LLMServiceError as exc:
        logger.exception(
            "Question rewriting failed for chat_id=%s",
            chat_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to process the follow-up question right now.",
        ) from exc

    # 4. Retrieve and rerank relevant chunks.
    try:
        retrieved_chunks = retrieve_relevant_chunks(
            db=db,
            chat=chat,
            owner_id=user.id,
            question=standalone_question,
            limit=5,
        )
    except RetrievalError as exc:
        logger.exception(
            "Context retrieval failed for chat_id=%s",
            chat_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve video context right now.",
        ) from exc

    # 5. Generate the answer using the original question.
    try:
        output_language = chat.output_language or "English"
        
        answer = generate_answer(
        question=question,
        context_chunks=retrieved_chunks,
        output_language=output_language,
        cache_scope=f"{user.id}:{chat.id}",
)
    except LLMServiceError as exc:
        logger.exception(
            "Answer generation failed for chat_id=%s",
            chat_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to generate an answer right now.",
        ) from exc

    # 6. Prepare source citations with retrieval and reranking scores.
    citations = [
        {
            "video_id": str(chunk["video_id"]),
            "youtube_video_id": chunk["youtube_video_id"],
            "video_title": chunk.get("video_title"),
            "start": chunk.get("start"),
            "end": chunk.get("end"),
            "text": chunk.get("text"),

            # Original Qdrant vector similarity score.
            "score": chunk.get("score"),

            # FlashRank reranking relevance score.
            "rerank_score": chunk.get("rerank_score"),
        }
        for chunk in retrieved_chunks
    ]

    # 7. Save original question and generated answer.
    user_message = save_message(
    db=db,
    chat=chat,
    role="user",
    content=question,
    output_language=chat.output_language,
)

    assistant_message = save_message(
    db=db,
    chat=chat,
    role="assistant",
    content=answer,
    citations=citations,
    output_language=chat.output_language,
)

    # 8. Return response.
    return {
        "chat_id": str(chat.id),
        "question": {
            "id": str(user_message.id),
            "content": user_message.content,
        },
        "answer": {
            "id": str(assistant_message.id),
            "content": assistant_message.content,
        },
        "output_language": chat.output_language,
        "standalone_question": standalone_question,
        "citations": citations,
    }


