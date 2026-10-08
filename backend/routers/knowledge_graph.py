from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.services.kg_service import kg_service

router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

class TermCreateUpdateRequest(BaseModel):
    source_term: str
    domain: str
    target_lang: str
    translation: str
    definition: Optional[str] = None
    reviewer_notes: Optional[str] = "Manual update via Knowledge Graph Studio"

class ExtractRequest(BaseModel):
    text: str
    domain: Optional[str] = "cloud_computing"

@router.get("/terms")
def list_terms(domain: Optional[str] = None, search: Optional[str] = None):
    terms = kg_service.get_all_terms(domain=domain, search=search)
    return {
        "count": len(terms),
        "domain_filter": domain or "all",
        "terms": terms
    }

@router.get("/terms/{term_id}")
def get_term_detail(term_id: str):
    term = kg_service.get_term_by_id(term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term node not found")
    return term

@router.post("/terms")
def create_or_update_term(req: TermCreateUpdateRequest):
    res = kg_service.apply_human_correction(
        source_term=req.source_term,
        target_lang=req.target_lang,
        corrected_translation=req.translation,
        domain=req.domain,
        reviewer_notes=req.reviewer_notes
    )
    return {
        "status": "SUCCESS",
        "message": f"Living Knowledge Graph updated for '{req.source_term}' (v{res['new_version']})",
        "data": res
    }

@router.post("/extract")
def extract_candidate_terms(req: ExtractRequest):
    candidates = kg_service.extract_candidate_terms(req.text, domain=req.domain)
    return {
        "domain": req.domain,
        "count": len(candidates),
        "candidates": candidates
    }

@router.get("/graph")
def export_graph_data(domain: Optional[str] = None):
    return kg_service.export_graph_json(domain=domain)
