from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.services.auth_service import get_current_user, require_role
from backend.services.kg_service import kg_service

router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

class TermCreateUpdateRequest(BaseModel):
    source_term: str
    domain: str
    target_lang: str
    translation: str
    definition: str | None = None
    reviewer_notes: str | None = "Manual update via Knowledge Graph Studio"

class CandidateTermRequest(BaseModel):
    source_term: str
    domain: str = "cloud_computing"
    target_lang: str
    proposed_translation: str
    definition: str | None = None

class RollbackTermRequest(BaseModel):
    target_version: int
    reason: str | None = "Anti-poisoning rollback to verified prior state"

class ExtractRequest(BaseModel):
    text: str
    domain: str | None = "cloud_computing"

@router.get("/terms")
def list_terms(
    domain: str | None = None,
    search: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    terms = kg_service.get_all_terms(domain=domain, search=search)
    return {
        "count": len(terms),
        "domain_filter": domain or "all",
        "terms": terms
    }

@router.get("/terms/{term_id}")
def get_term_detail(
    term_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    term = kg_service.get_term_by_id(term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term node not found")
    return term

@router.get("/concepts")
def list_concepts(current_user: dict[str, Any] = Depends(get_current_user)):
    from backend.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM concepts ORDER BY canonical_name ASC")
        return cursor.fetchall()

@router.get("/relationships")
def list_relationships(current_user: dict[str, Any] = Depends(get_current_user)):
    from backend.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM term_relationships ORDER BY created_at DESC")
        return cursor.fetchall()

@router.post("/terms")
def create_or_update_term(
    req: TermCreateUpdateRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
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
    current_user: dict[str, Any] = Depends(get_current_user)
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
    current_user: dict[str, Any] = Depends(require_role(["ADMIN"]))
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
def extract_candidate_terms(
    req: ExtractRequest,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    candidates = kg_service.extract_candidate_terms(req.text, domain=req.domain)
    return {
        "domain": req.domain,
        "count": len(candidates),
        "candidates": candidates
    }

@router.get("/graph")
def export_graph_data(
    domain: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    return kg_service.export_graph_json(domain=domain)
