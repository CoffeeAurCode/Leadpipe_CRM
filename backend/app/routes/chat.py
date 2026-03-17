"""
Chat API route — POST /chat
Accepts a conversation history and returns the assistant's next reply.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from supabase import Client
from app.db.session import get_db
from app.ai import chatbot

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=10000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.post("")
async def chat_endpoint(request: ChatRequest, db: Client = Depends(get_db)):
    # Guard: last user message must not exceed 2000 characters
    user_messages = [m for m in request.messages if m.role == "user"]
    if user_messages and len(user_messages[-1].content) > 2000:
        raise HTTPException(status_code=400, detail="Message too long. Maximum 2000 characters.")

    try:
        messages = [m.model_dump() for m in request.messages]
        reply = chatbot.run_chat(messages, db)
        return {"reply": reply}
    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Chat service error.")
