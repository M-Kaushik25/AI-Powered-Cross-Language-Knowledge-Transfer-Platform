from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.services.kg_service import kg_service
from backend.services.auth_service import get_current_user, require_role

router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

class TermCreateUpdateRequest(BaseModel):
    source_term: str
    domain: str
    target_lang: str
    translation: str
    definition: Optional[str] = None
    reviewer_notes: Optional[str] = "Manual update via Knowledge Graph Studio"

class CandidateTermRequest(BaseModel):
    source_term: str
    domain: str = "cloud_computing"
    target_lang: str
    proposed_translation: str
    definition: Optional[str] = None

class RollbackTermRequest(BaseModel):
    target_version: int
    reason: Optional[str] = "Anti-poisoning rollback to verified prior state"

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
def create_or_update_term(
    req: TermCreateUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
):
    res = kg_service.apply_human_correction(
        source_term=req.source_term,
        target_lang=req.target_lang,
        corrected_translation=req.translation,
        domain=req.domain,
        reviewer_notes=req.reviewer_notes,
        reviewer_id=current_user["id"],
        reviewer_role=current_user["role"]
    )
    return {
        "status": "SUCCESS",
        "message": f"Living Knowledge Graph updated for '{req.source_term}' (v{res['new_version']})",
        "data": res
    }

@router.post("/candidates")
def submit_candidate_term(
    req: CandidateTermRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        res = kg_service.stage_candidate_term(
            source_term=req.source_term,
            domain=req.domain,
            target_lang=req.target_lang,
            proposed_translation=req.proposed_translation,
            user_id=current_user["id"],
            definition=req.definition
        )
        return {
            "status": "SUCCESS",
            "message": f"Candidate term '{req.source_term}' submitted for reviewer evaluation.",
            "data": res
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/terms/{term_id}/rollback")
def rollback_term_version(
    term_id: str,
    req: RollbackTermRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    try:
        res = kg_service.rollback_term(
            term_id=term_id,
            target_version=req.target_version,
            reviewer_id=current_user["id"],
            reason=req.reason
        )
        return {
            "status": "SUCCESS",
            "message": f"Term successfully rolled back to version {req.target_version}.",
            "data": res
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
