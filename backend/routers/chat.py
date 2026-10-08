import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["CL-RAG Conversational Chat"])

class ChatQueryRequest(BaseModel):
    space_id: str
    question: str
    target_lang: Optional[str] = "en"
    conversation_id: Optional[str] = None

@router.post("")
async def ask_question(req: ChatQueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
        
    res = await rag_service.answer_question(
        space_id=req.space_id,
        question=req.question,
        target_lang=req.target_lang,
        conversation_id=req.conversation_id
    )
    return res

@router.get("/conversations")
def get_conversations(space_id: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if space_id:
            cursor.execute("SELECT * FROM conversations WHERE space_id = ? ORDER BY created_at DESC", (space_id,))
        else:
            cursor.execute("SELECT * FROM conversations ORDER BY created_at DESC")
        return cursor.fetchall()

@router.get("/conversations/{conv_id}/messages")
def get_messages(conv_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_id,))
        messages = cursor.fetchall()
        for m in messages:
            if m["citations_json"]:
                m["citations"] = json.loads(m["citations_json"])
        return messages
