
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.multi_agent_service import multi_agent_service

router = APIRouter(prefix="/api/translate", tags=["Multi-Agent Translation"])

class TranslationRequest(BaseModel):
    source_text: str
    target_lang: str
    domain: str | None = "cloud_computing"
    job_id: str | None = None

@router.post("")
async def translate_text(req: TranslationRequest):
    if not req.source_text.strip():
        raise HTTPException(status_code=400, detail="Source text cannot be empty")

    result = await multi_agent_service.translate_document(
        source_text=req.source_text,
        target_lang=req.target_lang,
        domain=req.domain,
        job_id=req.job_id
    )
    return result
