"""Async CRUD helpers for conversations and messages.

Every function takes an ``AsyncSession`` as its first argument, commits its
own transaction, and returns ``None`` (not raises) for not-found cases so
callers can decide how to respond.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Message


async def create_conversation(
    db: AsyncSession,
    title: str | None = None,
) -> Conversation:
    """Create and return a new conversation, optionally with a title."""
    conversation = Conversation(title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> Conversation | None:
    """Return a conversation with its messages eagerly loaded, or None."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> list[Message]:
    """Return all messages for a conversation ordered chronologically."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def list_conversations(db: AsyncSession) -> list[Conversation]:
    """Return all conversations ordered by most-recently updated first.

    Messages are NOT eagerly loaded — the sidebar only needs id, title, and
    updated_at.
    """
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> bool:
    """Delete a conversation and its messages.  Returns True if a row was deleted."""
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        return False
    await db.delete(conversation)
    await db.commit()
    return True


async def add_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    token_count: int | None = None,
) -> Message:
    """Append a message to a conversation and bump its ``updated_at``.

    Raises if the conversation does not exist (FK constraint), which the
    calling router should handle.
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        token_count=token_count,
    )
    db.add(message)

    # Bump the parent conversation's updated_at
    conversation = await db.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(message)
    return message


async def update_conversation_title(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    title: str,
) -> Conversation | None:
    """Update a conversation's title.  Returns None if not found."""
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        return None
    conversation.title = title
    await db.commit()
    await db.refresh(conversation)
    return conversation
