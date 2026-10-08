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

class ApproveTermRequest(BaseModel):
    notes: str | None = "Approved by expert reviewer"

class TermRelationRequest(BaseModel):
    source_term_id: str
    target_term_id: str
    relation: str = "synonym"
    confidence: float = 1.0

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
    terms = kg_service.get_all_terms(domain=domain, search=search, tenant_id=current_user.get("tenant_id", "default_org"))
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
    try:
        res = kg_service.propose_term_translation(
            source_term=req.source_term,
            domain=req.domain,
            target_lang=req.target_lang,
            translation=req.translation,
            definition=req.definition,
            reviewer_notes=req.reviewer_notes or "Expert term proposal",
            user_id=current_user["id"],
            user_role=current_user["role"],
            tenant_id=current_user.get("tenant_id", "default_org")
        )
        return {
            "status": "SUCCESS",
            "term_status": res["status"],
            "term_id": res["term_id"],
            "message": res["message"],
            "data": res
        }
    except ValueError as e:
        err_msg = str(e)
        if "Validation failed" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)

@router.post("/terms/{term_id}/approve")
def approve_term_proposal(
    term_id: str,
    req: ApproveTermRequest | None = None,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
):
    notes = req.notes if req else "Approved by expert reviewer"
    try:
        res = kg_service.approve_term(
            term_id=term_id,
            reviewer_id=current_user["id"],
            reviewer_role=current_user["role"],
            notes=notes or "",
            tenant_id=current_user.get("tenant_id", "default_org")
        )
        return res
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)

@router.post("/relations")
def add_relationship(
    req: TermRelationRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
):
    rel_id = kg_service.add_term_relation(
        source_term_id=req.source_term_id,
        target_term_id=req.target_term_id,
        relation=req.relation,
        tenant_id=current_user.get("tenant_id", "default_org"),
        confidence=req.confidence
    )
    return {"relation_id": rel_id, "status": "CREATED"}

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
        err_msg = str(e)
        if "Validation failed" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)

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
    candidates = kg_service.extract_candidate_terms(req.text, domain=req.domain or "cloud_computing")
    return {
        "domain": req.domain,
        "count": len(candidates),
        "candidates": candidates
    }

@router.get("/graph")
@router.get("/export")
def export_graph_data(
    domain: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    return kg_service.export_graph_json(domain=domain, tenant_id=current_user.get("tenant_id", "default_org"))

@router.get("/export/csv")
def export_csv_data(
    domain: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    from fastapi.responses import Response
    csv_str = kg_service.export_csv(domain=domain, tenant_id=current_user.get("tenant_id", "default_org"))
    return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=terms.csv"})

@router.get("/export/tbx")
def export_tbx_data(
    domain: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    from fastapi.responses import Response
    tbx_str = kg_service.export_tbx(domain=domain, tenant_id=current_user.get("tenant_id", "default_org"))
    return Response(content=tbx_str, media_type="application/x-tbx+xml", headers={"Content-Disposition": "attachment; filename=terms.tbx"})
