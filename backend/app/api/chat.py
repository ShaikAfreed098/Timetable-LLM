"""
LLM Chat endpoint with Server-Sent Events streaming.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.core.auth import get_current_user
from app.core.llm_agent import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: Optional[List[ChatMessage]] = []


@router.post("")
@limiter.limit("20/minute")
def chat(
    request: Request,
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Chat endpoint. Streams the LLM response as Server-Sent Events.
    """
    messages = [{"role": m.role, "content": m.content} for m in (req.history or [])]
    messages.append({"role": "user", "content": req.message})

    def event_stream():
        try:
            for chunk in run_agent(messages, db, current_user.institution_id, stream=True):
                data = json.dumps({"content": chunk})
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
