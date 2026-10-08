import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.database import get_db
from backend.services.auth_service import get_optional_user
from backend.services.rag_service import rag_service

router = APIRouter(prefix="/api/documents", tags=["Documents & Knowledge Spaces"])

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx", "json", "csv"}

class SpaceCreateRequest(BaseModel):
    name: str
    description: str | None = None
    domain: str | None = "cloud_computing"
    default_lang: str | None = "en"

class DirectDocumentIngestRequest(BaseModel):
    space_id: str
    filename: str
    content: str
    domain: str | None = "cloud_computing"

@router.get("/spaces")
def list_spaces():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_spaces ORDER BY created_at DESC")
        spaces = cursor.fetchall()

        # Attach doc count
        for s in spaces:
            cursor.execute("SELECT COUNT(*) as doc_count FROM documents WHERE space_id = ?", (s["id"],))
            s["doc_count"] = cursor.fetchone()["doc_count"]

    return spaces

@router.get("/spaces/{space_id}")
def get_space(space_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_spaces WHERE id = ?", (space_id,))
        space = cursor.fetchone()
        if not space:
            raise HTTPException(status_code=404, detail=f"Knowledge space '{space_id}' not found")
        cursor.execute("SELECT COUNT(*) as doc_count FROM documents WHERE space_id = ?", (space_id,))
        space["doc_count"] = cursor.fetchone()["doc_count"]
        return space

@router.post("/spaces")
def create_space(
    req: SpaceCreateRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_user)
):
    now = datetime.utcnow().isoformat()
    space_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        if current_user:
            user_id = current_user["id"]
        else:
            cursor.execute("SELECT id FROM users LIMIT 1")
            user_row = cursor.fetchone()
            user_id = user_row["id"] if user_row else "default_user"

        cursor.execute("""
            INSERT INTO knowledge_spaces (id, user_id, name, description, domain, default_lang, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (space_id, user_id, req.name, req.description, req.domain, req.default_lang, now))
    return {
        "id": space_id,
        "name": req.name,
        "domain": req.domain,
        "created_at": now
    }

@router.get("")
def list_documents(space_id: str | None = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if space_id:
            cursor.execute("SELECT id FROM knowledge_spaces WHERE id = ?", (space_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Knowledge space '{space_id}' not found")
            cursor.execute("SELECT * FROM documents WHERE space_id = ? ORDER BY created_at DESC", (space_id,))
        else:
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        return cursor.fetchall()

@router.post("/ingest-text")
def ingest_text_document(req: DirectDocumentIngestRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty")
    if len(req.content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"Payload exceeds maximum allowed size ({MAX_FILE_SIZE_BYTES // (1024*1024)} MB)")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM knowledge_spaces WHERE id = ?", (req.space_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Knowledge space '{req.space_id}' not found")

    res = rag_service.ingest_document(
        space_id=req.space_id,
        filename=req.filename,
        content=req.content,
        file_type="txt",
        domain=req.domain
    )
    return res

@router.post("/upload")
async def upload_document(
    space_id: str = Form(...),
    domain: str = Form("cloud_computing"),
    file: UploadFile = File(...)
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM knowledge_spaces WHERE id = ?", (space_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Knowledge space '{space_id}' not found")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"Uploaded file exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)} MB limit")

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "txt"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type .{ext}. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Try decoding text
    try:
        text_content = contents.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback text extraction
        text_content = contents.decode("latin-1", errors="ignore")

    res = rag_service.ingest_document(
        space_id=space_id,
        filename=file.filename,
        content=text_content,
        file_type=ext,
        domain=domain
    )
    return res

@router.get("/{doc_id}/chunks")
def get_document_chunks(doc_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE id = ?", (doc_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

        cursor.execute("SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index ASC", (doc_id,))
        chunks = cursor.fetchall()
        for c in chunks:
            if c["detected_terms_json"]:
                c["detected_terms"] = json.loads(c["detected_terms_json"])
        return chunks
