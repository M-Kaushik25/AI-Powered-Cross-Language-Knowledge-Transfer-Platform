import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import SUPPORTED_LANGUAGES, DEFAULT_DOMAINS, CONFIDENCE_THRESHOLD
from backend.database import init_db, get_db
from backend.services.kg_service import kg_service
from backend.services.rag_service import rag_service
from backend.services.eval_service import eval_service

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

app = FastAPI(
    title="AI-Powered Cross-Language Knowledge Transfer Platform",
    description="Final-Year Engineering Project & IEEE Research Platform featuring Living Terminology Knowledge Graph, Multi-Agent Verification, and Confidence Gating",
    version="1.0.0"
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

@app.on_event("startup")
def on_startup():
    init_db()
    kg_service.seed_database_if_empty()
    
    # Ensure default knowledge space and sample technical document exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM knowledge_spaces LIMIT 1")
        row = cursor.fetchone()
        if not row:
            import uuid
            from datetime import datetime
            space_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                VALUES (?, 'Chief Researcher', 'admin@clrag.org', 'hash_admin', 'ADMIN', 'en', ?)
            """, (user_id, now))

            cursor.execute("""
                INSERT INTO knowledge_spaces (id, user_id, name, description, domain, default_lang, created_at)
                VALUES (?, ?, 'Cloud & Distributed Systems Architecture', 'Authoritative technical specifications covering fault tolerance, load balancers, and eventual consistency.', 'cloud_computing', 'en', ?)
            """, (space_id, user_id, now))

            sample_text = (
                "Cloud infrastructure requires comprehensive fault tolerance to prevent catastrophic system downtime. "
                "A robust load balancer dynamically distributes incoming user traffic across container clusters to ensure horizontal scaling. "
                "In modern distributed systems, microservices communicate through a service mesh while enforcing strict rate limiting. "
                "To mitigate cascading network partitions, architects implement the circuit breaker pattern alongside eventual consistency models. "
                "Furthermore, write operations must guarantee idempotency so that consumer retries in a dead-letter queue do not produce corrupt side effects. "
                "High-velocity cache invalidation ensures that state updates propagate predictably across nodes executing the consensus protocol."
            )

            rag_service.ingest_document(
                space_id=space_id,
                filename="cloud_systems_specification_v2.txt",
                content=sample_text,
                file_type="txt",
                domain="cloud_computing"
            )
            print("Default space and sample document seeded successfully.")

# Mount frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
