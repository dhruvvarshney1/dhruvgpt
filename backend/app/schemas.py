"""Pydantic v2 schemas for API request/response validation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageOut(BaseModel):
    """A single message within a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """Lightweight conversation representation for the sidebar list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    """Full conversation with all messages included."""

    messages: list[MessageOut] = []


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    conversation_id: uuid.UUID | None = None
    message: str = Field(..., min_length=1)
    model: str | None = None  # ponytail: optional override, backend default if omitted


class ConversationCreateResponse(BaseModel):
    """Returned when a new conversation is created as a side effect of chat."""

    id: uuid.UUID
