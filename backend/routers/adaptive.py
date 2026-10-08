
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.services.adaptive_service import adaptive_service
from backend.services.auth_service import get_current_user

router = APIRouter(prefix="/api/adaptive", tags=["Expertise-Adaptive Summarization"])

class AdaptiveRequest(BaseModel):
    source_text: str
    target_lang: str = "en"
    domain: str | None = "cloud_computing"

@router.post("")
async def generate_adaptive_output(
    req: AdaptiveRequest,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    if not req.source_text.strip():
        raise HTTPException(status_code=400, detail="Source text cannot be empty")
    if len(req.source_text) > 20000:
        raise HTTPException(status_code=413, detail="Source text exceeds maximum allowed limit (20,000 characters)")

    result = await adaptive_service.generate_adaptive_summaries(
        source_text=req.source_text,
        target_lang=req.target_lang,
        domain=req.domain
    )
    return result
