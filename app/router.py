from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_session
from app.middlewares import _is_rate_limited
from app.models import Chat, Chunk, Message, MessageRole
from app.state import get_config
from services.embed import embed
from services.llm import ask

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    user_hash: str


class MessageOut(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    chat_id: str
    message: MessageOut


def _verify_user_hash(user_hash: str) -> bool:
    if len(user_hash) != 64:
        return False
    try:
        int(user_hash, 16)
        return True
    except ValueError:
        return False


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    cfg = get_config()

    if not _verify_user_hash(req.user_hash):
        raise HTTPException(status_code=400, detail="Invalid user hash.")

    with get_session() as session:
        chat_obj = Chat.get_chat_by_user(session, req.user_hash)

        limited, reason = _is_rate_limited(f"hash:{req.user_hash}")
        if limited:
            raise HTTPException(status_code=429, detail=reason)

        user_msg = Message(
            chat_id=chat_obj.id,
            role=MessageRole.USER,
            content=req.message,
        )
        session.add(user_msg)
        session.flush()

        history = chat_obj.recent_messages(limit=10)
        query_embedding = embed(req.message)
        chunks = Chunk.search(session, query_embedding, top_k=cfg.EMBEDDINGS.top_k)
        chunk_contents = [c.content for c in chunks]

        answer = await ask(chunk_contents, history, req.message)

        assistant_msg = Message(
            chat_id=chat_obj.id,
            role=MessageRole.ASSISTANT,
            content=answer,
        )
        session.add(assistant_msg)

        return ChatResponse(
            chat_id=chat_obj.id,
            message=MessageOut(role=MessageRole.ASSISTANT, content=answer),
        )
