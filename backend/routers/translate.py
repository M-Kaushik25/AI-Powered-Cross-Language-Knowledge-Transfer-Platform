
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.services.auth_service import get_current_user
from backend.services.multi_agent_service import LLMProviderError, multi_agent_service

router = APIRouter(prefix="/api/translate", tags=["Multi-Agent Translation"])

class TranslationRequest(BaseModel):
    source_text: str
    target_lang: str
    source_lang: str | None = "en"
    domain: str | None = "cloud_computing"
    job_id: str | None = None
    mode: str | None = None  # 'live', 'offline', 'auto'

@router.post("")
async def translate_text(
    req: TranslationRequest,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    if not req.source_text.strip():
        raise HTTPException(status_code=400, detail="Source text cannot be empty")
    if len(req.source_text) > 20000:
        raise HTTPException(status_code=413, detail="Source text exceeds maximum allowed limit (20,000 characters)")

    tenant_id = current_user.get("tenant_id", "default_org")
    try:
        result = await multi_agent_service.translate_document(
            source_text=req.source_text,
            target_lang=req.target_lang,
            source_lang=req.source_lang or "en",
            domain=req.domain or "cloud_computing",
            job_id=req.job_id,
            tenant_id=tenant_id,
            mode=req.mode
        )
        return result
    except LLMProviderError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider failure in live mode: {e}"
        )
