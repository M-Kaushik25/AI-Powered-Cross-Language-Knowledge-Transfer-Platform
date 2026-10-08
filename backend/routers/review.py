from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.services.auth_service import require_role
from backend.services.kg_service import kg_service

router = APIRouter(prefix="/api/review", tags=["Review Queue"])

class ReviewActionRequest(BaseModel):
    corrected_translation: str
    reviewer_comment: str | None = "Approved and updated during expert review"

@router.get("")
def list_review_items(
    status: str | None = "PENDING",
    current_user: dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
):
    tenant_id = current_user.get("tenant_id", "default_org")
    with get_db() as conn:
        cursor = conn.cursor()
        if status and status != "ALL":
            cursor.execute("""
                SELECT * FROM review_queue
                WHERE status = ? AND (tenant_id = ? OR tenant_id = 'default_org')
                ORDER BY created_at DESC
            """, (status, tenant_id))
        else:
            cursor.execute("""
                SELECT * FROM review_queue
                WHERE tenant_id = ? OR tenant_id = 'default_org'
                ORDER BY created_at DESC
            """, (tenant_id,))
        items = cursor.fetchall()

    return {
        "count": len(items),
        "status_filter": status,
        "items": items
    }

@router.post("/{item_id}/correct")
def correct_and_update_kg(
    item_id: str,
    req: ReviewActionRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
):
    """
    Submits a human correction for a flagged low-confidence segment/term:
    1. Updates the Living Terminology Knowledge Graph (self-evolution loop).
    2. Increments version and logs provenance with authenticated reviewer identity.
    3. Resolves this queue entry.
    """
    tenant_id = current_user.get("tenant_id", "default_org")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM review_queue WHERE id = ? AND (tenant_id = ? OR tenant_id = 'default_org')", (item_id, tenant_id))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Review item not found")

    # Apply correction to Knowledge Graph with authenticated reviewer metadata
    kg_res = kg_service.apply_human_correction(
        source_term=item["term_text"],
        target_lang=item["target_lang"],
        corrected_translation=req.corrected_translation,
        domain=item["domain"],
        reviewer_notes=req.reviewer_comment or "Self-updating correction from Human Review Hub",
        term_id=item["term_id"],
        reviewer_id=current_user["id"],
        reviewer_role=current_user["role"]
    )

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE review_queue
            SET status = 'RESOLVED',
                reviewed_by = ?,
                resolved_at = ?,
                reviewer_comment = ?
            WHERE id = ?
        """, (current_user["id"], now, req.reviewer_comment, item_id))

    return {
        "status": "SUCCESS",
        "message": f"Correction applied! Living Knowledge Graph updated for '{item['term_text']}' to version {kg_res['new_version']}.",
        "kg_update": kg_res
    }

@router.post("/{item_id}/dismiss")
def dismiss_review_item(
    item_id: str,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN", "REVIEWER"]))
):
    tenant_id = current_user.get("tenant_id", "default_org")
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM review_queue WHERE id = ? AND (tenant_id = ? OR tenant_id = 'default_org')", (item_id, tenant_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Review item not found")

        cursor.execute("""
            UPDATE review_queue
            SET status = 'DISMISSED',
                reviewed_by = ?,
                resolved_at = ?,
                reviewer_comment = 'Dismissed by reviewer without Knowledge Graph alteration'
            WHERE id = ?
        """, (current_user["id"], now, item_id))
    return {"status": "SUCCESS", "message": "Item marked dismissed"}
