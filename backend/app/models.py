"""SQLAlchemy ORM models for conversations and messages."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    """A single chat conversation containing zero or more messages."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_conversations_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id!s} title={self.title!r}>"


class Message(Base):
    """A single message within a conversation (user or assistant)."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    token_count: Mapped[int | None] = mapped_column(nullable=True)

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_messages_role",
        ),
        Index("ix_messages_conversation_id", "conversation_id"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.id!s} role={self.role!r}>"
