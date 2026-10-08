import os
import uuid
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import SUPPORTED_LANGUAGES, DEFAULT_DOMAINS, CONFIDENCE_THRESHOLD
from backend.database import init_db, get_db, get_utc_now_iso
from backend.services.kg_service import kg_service
from backend.services.rag_service import rag_service
from backend.services.auth_service import hash_password

from backend.routers import (
    auth,
    documents,
    knowledge_graph,
    translate,
    review,
    adaptive,
    chat,
    eval as eval_router
)

logger = logging.getLogger("clrag.main")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Clean Database Initialization
    logger.info("Initializing database tables and indexes...")
    init_db()

    # 2. Seed Living Knowledge Graph ontology
    logger.info("Checking terminology knowledge graph seed...")
    kg_service.seed_database_if_empty()

    # 3. Seed Default Accounts (Admin, Reviewer, User) with secure bcrypt hashes
    now = get_utc_now_iso()
    created_space_id = None
    created_user_id = None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = 'admin@clrag.org'")
        if not cursor.fetchone():
            admin_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                VALUES (?, 'Chief Systems Architect', 'admin@clrag.org', ?, 'ADMIN', 'en', ?)
            """, (admin_id, hash_password("AdminPassword123!"), now))

            reviewer_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                VALUES (?, 'Domain Terminology Reviewer', 'reviewer@clrag.org', ?, 'REVIEWER', 'en', ?)
            """, (reviewer_id, hash_password("ReviewerPassword123!"), now))

            user_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                VALUES (?, 'Research Student', 'user@clrag.org', ?, 'USER', 'en', ?)
            """, (user_id, hash_password("UserPassword123!"), now))

            # Create default workspace
            space_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO knowledge_spaces (id, user_id, name, description, domain, default_lang, created_at)
                VALUES (?, ?, 'Cloud & Distributed Systems Architecture', 'Authoritative technical specifications covering fault tolerance, load balancers, and eventual consistency.', 'cloud_computing', 'en', ?)
            """, (space_id, admin_id, now))

            created_space_id = space_id
            created_user_id = admin_id
            logger.info("Default seed accounts (admin, reviewer, user) created.")

    # 4. Seed sample technical document OUTSIDE the database transaction block
    if created_space_id:
        try:
            sample_text = (
                "Cloud infrastructure requires comprehensive fault tolerance to prevent catastrophic system downtime. "
                "A robust load balancer dynamically distributes incoming user traffic across container clusters to ensure horizontal scaling. "
                "In modern distributed systems, microservices communicate through a service mesh while enforcing strict rate limiting. "
                "To mitigate cascading network partitions, architects implement the circuit breaker pattern alongside eventual consistency models. "
                "Furthermore, write operations must guarantee idempotency so that consumer retries in a dead-letter queue do not produce corrupt side effects. "
                "High-velocity cache invalidation ensures that state updates propagate predictably across nodes executing the consensus protocol."
            )
            rag_service.ingest_document(
                space_id=created_space_id,
                filename="cloud_systems_specification_v2.txt",
                content=sample_text,
                file_type="txt",
                domain="cloud_computing",
                user_id=created_user_id
            )
            logger.info("Sample technical document ingested successfully without nested locks.")
        except Exception as e:
            logger.error(f"Sample document ingestion encountered an error, continuing startup: {e}")

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
