from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.services.kg_service import kg_service

router = APIRouter(prefix="/api/review", tags=["Review Queue"])

class ReviewActionRequest(BaseModel):
    corrected_translation: str
    reviewer_comment: Optional[str] = "Approved and updated during expert review"

@router.get("")
def list_review_items(status: Optional[str] = "PENDING"):
    with get_db() as conn:
        cursor = conn.cursor()
        if status and status != "ALL":
            cursor.execute("SELECT * FROM review_queue WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM review_queue ORDER BY created_at DESC")
        items = cursor.fetchall()
        
    return {
        "count": len(items),
        "status_filter": status,
        "items": items
    }

@router.post("/{item_id}/correct")
def correct_and_update_kg(item_id: str, req: ReviewActionRequest):
    """
    Submits a human correction for a flagged low-confidence segment/term:
    1. Updates the Living Terminology Knowledge Graph (self-evolution loop).
    2. Increments version and logs provenance.
    3. Resolves this queue entry.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM review_queue WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Review item not found")

    # Apply correction to Knowledge Graph
    kg_res = kg_service.apply_human_correction(
        source_term=item["term_text"],
        target_lang=item["target_lang"],
        corrected_translation=req.corrected_translation,
        domain=item["domain"],
        reviewer_notes=req.reviewer_comment or "Self-updating correction from Human Review Hub",
        term_id=item["term_id"]
    )

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE review_queue
            SET status = 'RESOLVED',
                resolved_at = ?,
                reviewer_comment = ?
            WHERE id = ?
        """, (now, req.reviewer_comment, item_id))

    return {
        "status": "SUCCESS",
        "message": f"Correction applied! Living Knowledge Graph updated for '{item['term_text']}' to version {kg_res['new_version']}.",
        "kg_update": kg_res
    }

@router.post("/{item_id}/dismiss")
def dismiss_review_item(item_id: str):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE review_queue
            SET status = 'DISMISSED',
                resolved_at = ?,
                reviewer_comment = 'Dismissed by reviewer without Knowledge Graph alteration'
            WHERE id = ?
        """, (now, item_id))
    return {"status": "SUCCESS", "message": "Item marked dismissed"}
