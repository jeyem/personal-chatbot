import enum
from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, object_session, relationship

from app.db import Base


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    def search(cls, session: Session, embedding: list[float], top_k: int = 5) -> list["Chunk"]:
        return list(
            session.execute(
                select(cls).order_by(cls.embedding.cosine_distance(embedding)).limit(top_k)
            )
            .scalars()
            .all()
        )


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    # browser fingerprint hash — identifies the visitor without login
    user_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat",
        order_by="Message.created_at",
        lazy="noload",
    )

    def recent_messages(self, limit: int = 50) -> list["Message"]:
        session = object_session(self)
        if session is None:
            raise RuntimeError("Chat is not attached to a session.")
        result = session.execute(
            select(Message)
            .where(Message.chat_id == self.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @classmethod
    def get_chat_by_user(cls, session: Session, user_hash: str) -> "Chat":
        chat_obj = session.execute(
            select(cls).where(cls.user_hash == user_hash)
        ).scalar_one_or_none()

        if not chat_obj:
            chat_obj = cls(user_hash=user_hash)
            session.add(chat_obj)
            session.flush()

        return chat_obj


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("chats.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped["Chat"] = relationship(back_populates="messages")
