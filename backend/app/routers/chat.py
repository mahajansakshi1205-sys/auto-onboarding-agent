from typing import List, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.module9_chat.service import chat

router = APIRouter(prefix="/repos", tags=["chat"])


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Turn] = []


@router.post("/{repo_id}/chat")
def chat_repo(repo_id: int, body: ChatRequest):
    try:
        history = [t.model_dump() for t in body.history]
        return chat(repo_id, body.message, history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")