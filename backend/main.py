import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import CONFIDENCE_THRESHOLD, DEFAULT_DOMAINS, SUPPORTED_LANGUAGES
from backend.database import get_db, init_db, seed_all
from backend.routers import (
    adaptive,
    auth,
    chat,
    documents,
    knowledge_graph,
    review,
    translate,
)
from backend.routers import eval as eval_router
from backend.services.kg_service import kg_service

logger = logging.getLogger("clrag.main")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Clean Database Initialization (tables and indexes only)
    logger.info("Initializing database tables and indexes...")
    init_db()

    # 2. Seed Living Knowledge Graph ontology
    logger.info("Checking terminology knowledge graph seed...")
    kg_service.seed_database_if_empty()

    # 3. Unified idempotent seed routine for demo accounts, space, and document
    logger.info("Running unified idempotent seed routine...")
    seed_all()

    yield
    logger.info("CL-RAG backend shutting down.")

app = FastAPI(
    title="AI-Powered Cross-Language Knowledge Transfer Platform",
    description="Final-Year Engineering Project & IEEE Research Platform featuring Living Terminology Knowledge Graph, Multi-Agent Verification, and Confidence Gating",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(knowledge_graph.router)
app.include_router(translate.router)
app.include_router(review.router)
app.include_router(adaptive.router)
app.include_router(chat.router)
app.include_router(eval_router.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "CL-RAG Cross-Language Knowledge Transfer Platform",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "supported_languages": SUPPORTED_LANGUAGES,
        "domains": DEFAULT_DOMAINS
    }

@app.get("/api/stats")
def get_system_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM terms")
        term_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM documents")
        doc_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM document_chunks")
        chunk_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM review_queue WHERE status = 'PENDING'")
        pending_reviews = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM term_audit_log WHERE action = 'HUMAN_CORRECTION'")
        corrections_applied = cursor.fetchone()["count"]

    return {
        "terminology_nodes": term_count,
        "documents_indexed": doc_count,
        "semantic_chunks": chunk_count,
        "pending_reviews": pending_reviews,
        "self_evolution_updates": corrections_applied,
        "confidence_threshold": CONFIDENCE_THRESHOLD
    }

# Mount frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
