"""Streaming chat endpoint — POST /chat.

Accepts a user message (with optional conversation_id), streams the NVIDIA
response as SSE events, and persists both user and assistant messages.

SSE event names (consumed by the frontend in Phase 04):
    conversation_id  — new conversation UUID (only sent when one is created)
    token            — incremental text chunk from the model
    done             — final event after streaming completes
    error            — sent on NVIDIA API failures mid-stream
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory

from app import crud
from app.database import get_db
from app.nvidia_client import (
    NvidiaAPIError,
    NvidiaRateLimitError,
    NvidiaTimeoutError,
    get_full_completion,
    stream_chat_completion,
)
from app.schemas import ChatRequest

from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent.parent / "system.md"


def get_system_prompt() -> str:
    """Load system prompt from system.md if present, fallback to default."""
    if SYSTEM_PROMPT_PATH.is_file():
        try:
            content = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception as exc:
            logger.warning("Failed to read system.md: %s", exc)
    return "You are a helpful assistant."


def _sse(event: str, data: str) -> str:
    """Format a single SSE frame.

    Per the SSE spec, multi-line data must be split so each line
    gets its own ``data: `` prefix.
    """
    lines = data.split("\n")
    data_section = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{data_section}\n\n"


async def generate_title(conversation_id: uuid.UUID, first_user_message: str) -> None:
    """Generate a conversation title in the background and update it."""
    prompt = f"Summarize the following message in 4 words or fewer, as a conversation title, no punctuation: {first_user_message}"
    messages = [{"role": "user", "content": prompt}]
    try:
        title = await get_full_completion(messages)
        title = title.strip().strip('"').strip()
        # Open a new session since the request session is already closed
        async with async_session_factory() as db:
            await crud.update_conversation_title(db, conversation_id, title)
    except Exception as exc:
        logger.error("Failed to generate title for conversation %s: %s", conversation_id, exc)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream an LLM response for a user message.

    If ``conversation_id`` is ``None``, a new conversation is created and its
    UUID is sent as the first SSE event.  The NVIDIA response is streamed
    chunk-by-chunk as ``token`` events, followed by a final ``done`` event.
    """
    conversation_id = request.conversation_id

    # ── Resolve or create conversation ────────────────────────────────
    if conversation_id is None:
        conversation = await crud.create_conversation(db)
        conversation_id = conversation.id
        send_conversation_id = True
    else:
        conversation = await crud.get_conversation(db, conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        send_conversation_id = False

    # ── Persist the user message ──────────────────────────────────────
    await crud.add_message(db, conversation_id, role="user", content=request.message)

    # ── Build the messages list for NVIDIA ────────────────────────────
    # Reload conversation with messages to include the one we just added
    conversation = await crud.get_conversation(db, conversation_id)
    nvidia_messages: list[dict[str, str]] = [
        {"role": "system", "content": get_system_prompt()},
    ]
    if conversation and conversation.messages:
        for msg in conversation.messages:
            nvidia_messages.append({"role": msg.role, "content": msg.content})

    # ── SSE generator ─────────────────────────────────────────────────
    async def event_generator():
        """Yield SSE frames: optionally conversation_id, then tokens, then done/error."""
        if send_conversation_id:
            yield _sse("conversation_id", str(conversation_id))

        full_text_parts: list[str] = []
        usage: dict = {}
        errored = False

        try:
            async for chunk in stream_chat_completion(
                nvidia_messages, usage_out=usage,
            ):
                full_text_parts.append(chunk)
                yield _sse("token", chunk)
        except NvidiaRateLimitError as exc:
            errored = True
            logger.error("NVIDIA rate limit: %s", exc)
            error_payload = json.dumps({
                "message": "You're sending messages too quickly — try again in a moment.",
                "truncated": True,
                "retry_after": exc.retry_after,
            })
            yield _sse("error", error_payload)
        except (NvidiaAPIError, NvidiaTimeoutError) as exc:
            errored = True
            logger.error("NVIDIA streaming error: %s", exc)
            error_payload = json.dumps({
                "message": str(exc),
                "truncated": True,
            })
            yield _sse("error", error_payload)

        # Persist the assistant message (full or partial)
        full_text = "".join(full_text_parts)
        if full_text:
            token_count = usage.get("completion_tokens")
            await crud.add_message(
                db,
                conversation_id,  # type: ignore[arg-type]
                role="assistant",
                content=full_text,
                token_count=token_count,
            )

        if not errored:
            done_data = json.dumps({"usage": usage}) if usage else "{}"
            yield _sse("done", done_data)

            # Check if this is the first assistant message (new conversation)
            # nvidia_messages has length 2: system + the new user message.
            if len(nvidia_messages) == 2:
                background_tasks.add_task(generate_title, conversation_id, request.message)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
