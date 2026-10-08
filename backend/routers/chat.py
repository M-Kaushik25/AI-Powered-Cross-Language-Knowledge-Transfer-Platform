import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.services.auth_service import get_current_user
from backend.services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["CL-RAG Conversational Chat"])

class ChatQueryRequest(BaseModel):
    space_id: str
    question: str
    target_lang: str | None = "en"
    conversation_id: str | None = None

@router.post("")
async def ask_question(
    req: ChatQueryRequest,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if len(req.question) > 5000:
        raise HTTPException(status_code=413, detail="Question exceeds maximum allowed limit (5,000 characters)")

    tenant_id = current_user.get("tenant_id", "default_org")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM knowledge_spaces WHERE id = ? AND tenant_id = ?", (req.space_id, tenant_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Knowledge space '{req.space_id}' not found")
        if req.conversation_id:
            cursor.execute("SELECT id FROM conversations WHERE id = ?", (req.conversation_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Conversation '{req.conversation_id}' not found")

    res = await rag_service.answer_question(
        space_id=req.space_id,
        question=req.question,
        target_lang=req.target_lang,
        conversation_id=req.conversation_id
    )
    return res

@router.get("/conversations")
def get_conversations(
    space_id: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    tenant_id = current_user.get("tenant_id", "default_org")
    with get_db() as conn:
        cursor = conn.cursor()
        if space_id:
            cursor.execute("SELECT id FROM knowledge_spaces WHERE id = ? AND tenant_id = ?", (space_id, tenant_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Knowledge space '{space_id}' not found")
            cursor.execute("SELECT * FROM conversations WHERE space_id = ? ORDER BY created_at DESC", (space_id,))
        else:
            cursor.execute("""
                SELECT c.* FROM conversations c
                JOIN knowledge_spaces s ON c.space_id = s.id
                WHERE s.tenant_id = ?
                ORDER BY c.created_at DESC
            """, (tenant_id,))
        return cursor.fetchall()

@router.get("/conversations/{conv_id}/messages")
def get_messages(
    conv_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    tenant_id = current_user.get("tenant_id", "default_org")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id FROM conversations c
            JOIN knowledge_spaces s ON c.space_id = s.id
            WHERE c.id = ? AND s.tenant_id = ?
        """, (conv_id, tenant_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")
        cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_id,))
        messages = cursor.fetchall()
        for m in messages:
            if m["citations_json"]:
                m["citations"] = json.loads(m["citations_json"])
        return messages
