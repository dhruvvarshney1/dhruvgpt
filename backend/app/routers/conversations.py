"""Conversation management endpoints (list, get, delete)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import ConversationDetail, ConversationSummary, MessageOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSummary]:
    """Return all conversations ordered by most-recently updated first.

    Messages are not included — the sidebar only needs id, title, and
    updated_at.
    """
    conversations = await crud.list_conversations(db)
    return [ConversationSummary.model_validate(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    """Return a single conversation with all its messages."""
    conversation = await crud.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        messages=[MessageOut.model_validate(m) for m in conversation.messages],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a conversation and all its messages."""
    deleted = await crud.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
