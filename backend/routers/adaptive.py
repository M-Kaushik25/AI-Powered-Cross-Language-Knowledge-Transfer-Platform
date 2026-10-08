from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.services.adaptive_service import adaptive_service

router = APIRouter(prefix="/api/adaptive", tags=["Expertise-Adaptive Summarization"])

class AdaptiveRequest(BaseModel):
    source_text: str
    target_lang: str = "en"
    domain: Optional[str] = "cloud_computing"

@router.post("")
async def generate_adaptive_output(req: AdaptiveRequest):
    if not req.source_text.strip():
        raise HTTPException(status_code=400, detail="Source text cannot be empty")
        
    result = await adaptive_service.generate_adaptive_summaries(
        source_text=req.source_text,
        target_lang=req.target_lang,
        domain=req.domain
    )
    return result
