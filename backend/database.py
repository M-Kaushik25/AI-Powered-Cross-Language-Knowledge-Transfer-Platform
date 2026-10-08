import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.config import get_current_db_path


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = db_path or get_current_db_path()
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.row_factory = dict_factory
    # Enable WAL mode for high concurrency & safe multi-process reads/writes
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db(db_path: str | None = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: str | None = None):
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Users with strictly enforced roles: ADMIN, REVIEWER, USER
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'USER' CHECK(role IN ('ADMIN', 'REVIEWER', 'USER')),
            preferred_lang TEXT NOT NULL DEFAULT 'en',
            created_at TEXT NOT NULL
        )
        """)

        # 2. Knowledge Spaces (User/Org Scoped)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_spaces (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            domain TEXT NOT NULL DEFAULT 'cloud_computing',
            default_lang TEXT NOT NULL DEFAULT 'en',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)

        # 3. Documents
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            user_id TEXT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'READY',
            chunk_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (space_id) REFERENCES knowledge_spaces (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        """)

        # 4. Document Chunks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding_json TEXT,
            detected_terms_json TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
            FOREIGN KEY (space_id) REFERENCES knowledge_spaces (id) ON DELETE CASCADE
        )
        """)

        # 5. Semantic Concepts (Relational Graph Level 1)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            definition TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(canonical_name, domain)
        )
        """)

        # 6. Living Terminology Nodes (Graph Level 2)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id TEXT PRIMARY KEY,
            concept_id TEXT,
            source_term TEXT NOT NULL,
            domain TEXT NOT NULL,
            definition TEXT,
            translations_json TEXT NOT NULL DEFAULT '{}',
            version INTEGER NOT NULL DEFAULT 1,
            confidence REAL NOT NULL DEFAULT 0.85,
            status TEXT NOT NULL DEFAULT 'APPROVED' CHECK(status IN ('APPROVED', 'CANDIDATE', 'REJECTED')),
            created_by TEXT,
            approved_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_term, domain),
            FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE SET NULL
        )
        """)

        # 7. Graph Relationships (Graph Level 3)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS term_relationships (
            id TEXT PRIMARY KEY,
            source_term_id TEXT NOT NULL,
            target_term_id TEXT NOT NULL,
            relation_type TEXT NOT NULL CHECK(relation_type IN ('SYNONYM', 'TRANSLATES_TO', 'CONTEXT_OF', 'SUBCLASS_OF')),
            confidence REAL NOT NULL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_term_id) REFERENCES terms (id) ON DELETE CASCADE,
            FOREIGN KEY (target_term_id) REFERENCES terms (id) ON DELETE CASCADE
        )
        """)

        # 8. Term Audit Log (Provenanced rollback & evolution history)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS term_audit_log (
            id TEXT PRIMARY KEY,
            term_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            action TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            old_value_json TEXT,
            new_value_json TEXT,
            reviewer_notes TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (term_id) REFERENCES terms (id) ON DELETE CASCADE
        )
        """)

        # 9. Confidence-Gated Review Queue
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            source_segment TEXT NOT NULL,
            target_segment TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            domain TEXT NOT NULL,
            term_id TEXT,
            term_text TEXT NOT NULL,
            confidence REAL NOT NULL,
            verifier_score REAL NOT NULL,
            critic_score REAL NOT NULL,
            critic_notes TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'RESOLVED', 'DISMISSED')),
            reviewer_comment TEXT,
            reviewed_by TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (term_id) REFERENCES terms (id) ON DELETE SET NULL,
            FOREIGN KEY (reviewed_by) REFERENCES users (id) ON DELETE SET NULL
        )
        """)

        # 10. Conversations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            target_lang TEXT NOT NULL DEFAULT 'en',
            created_at TEXT NOT NULL,
            FOREIGN KEY (space_id) REFERENCES knowledge_spaces (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)

        # 11. Messages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            target_lang TEXT NOT NULL DEFAULT 'en',
            citations_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """)

        # 12. Evaluation Runs (Isolated results store)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS eval_runs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT NOT NULL,
            rounds_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_terms_source_domain ON terms(source_term, domain);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_space ON document_chunks(space_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_term ON term_audit_log(term_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON term_relationships(source_term_id);")

def seed_all(db_path: str | None = None):
    """
    Unified, independently idempotent seed routine.
    Creates demo accounts only when ENVIRONMENT=development, default workspace,
    and sample document independently (each check is independent).
    """
    import os

    from backend.config import ENVIRONMENT
    from backend.services.auth_service import hash_password
    now = get_utc_now_iso()

    env = os.getenv("ENVIRONMENT", ENVIRONMENT)

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Independently Seed Demo Accounts in Development
        admin_id = None
        if env == "development":
            cursor.execute("SELECT id FROM users WHERE email = 'admin@clrag.org'")
            admin_row = cursor.fetchone()
            if not admin_row:
                admin_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                    VALUES (?, 'Chief Systems Architect', 'admin@clrag.org', ?, 'ADMIN', 'en', ?)
                """, (admin_id, hash_password("AdminPassword123!"), now))
            else:
                admin_id = admin_row["id"]

            cursor.execute("SELECT id FROM users WHERE email = 'reviewer@clrag.org'")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                    VALUES (?, 'Domain Terminology Reviewer', 'reviewer@clrag.org', ?, 'REVIEWER', 'en', ?)
                """, (str(uuid.uuid4()), hash_password("ReviewerPassword123!"), now))

            cursor.execute("SELECT id FROM users WHERE email = 'user@clrag.org'")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (id, name, email, password_hash, role, preferred_lang, created_at)
                    VALUES (?, 'Research Student', 'user@clrag.org', ?, 'USER', 'en', ?)
                """, (str(uuid.uuid4()), hash_password("UserPassword123!"), now))
        else:
            cursor.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1")
            admin_row = cursor.fetchone()
            if admin_row:
                admin_id = admin_row["id"]

        # If admin_id is not set, find any user or use a placeholder system ID
        if not admin_id:
            cursor.execute("SELECT id FROM users LIMIT 1")
            u_row = cursor.fetchone()
            admin_id = u_row["id"] if u_row else str(uuid.uuid4())

        # 2. Independently Seed Default Knowledge Space
        cursor.execute("SELECT id FROM knowledge_spaces WHERE name = 'Cloud & Distributed Systems Architecture'")
        space_row = cursor.fetchone()
        if not space_row:
            space_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO knowledge_spaces (id, user_id, name, description, domain, default_lang, created_at)
                VALUES (?, ?, 'Cloud & Distributed Systems Architecture', 'Authoritative technical specifications covering fault tolerance, load balancers, and eventual consistency.', 'cloud_computing', 'en', ?)
            """, (space_id, admin_id, now))
        else:
            space_id = space_row["id"]

        # 3. Independently Seed Sample Document & Chunks for Default Space
        cursor.execute("SELECT id FROM documents WHERE space_id = ?", (space_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            doc_id = str(uuid.uuid4())
            sample_filename = "cloud_systems_specification_v2.txt"
            sample_text = (
                "Cloud infrastructure requires comprehensive fault tolerance to prevent catastrophic system downtime. "
                "A robust load balancer dynamically distributes incoming user traffic across container clusters to ensure horizontal scaling. "
                "In modern distributed systems, microservices communicate through a service mesh while enforcing strict rate limiting. "
                "To mitigate cascading network partitions, architects implement the circuit breaker pattern alongside eventual consistency models. "
                "Furthermore, write operations must guarantee idempotency so that consumer retries in a dead-letter queue do not produce corrupt side effects. "
                "High-velocity cache invalidation ensures that state updates propagate predictably across nodes executing the consensus protocol."
            )
            # Create chunks
            words = sample_text.split()
            chunk_size = 180
            overlap = 30
            chunks = []
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_str = " ".join(words[start:end])
                if chunk_str.strip():
                    chunks.append(chunk_str)
                if end >= len(words):
                    break
                start += (chunk_size - overlap)

            cursor.execute("""
                INSERT INTO documents (id, space_id, user_id, filename, file_type, raw_text, status, chunk_count, created_at)
                VALUES (?, ?, ?, ?, 'txt', ?, 'READY', ?, ?)
            """, (doc_id, space_id, admin_id, sample_filename, sample_text, len(chunks), now))

            # Sample domain terms known in cloud_computing
            sample_terms = ["fault tolerance", "load balancer", "service mesh", "rate limiting", "circuit breaker", "eventual consistency", "idempotency", "cache invalidation"]
            for idx, chunk_text in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO document_chunks (id, document_id, space_id, chunk_index, content, embedding_json, detected_terms_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id,
                    doc_id,
                    space_id,
                    idx + 1,
                    chunk_text,
                    json.dumps([]),
                    json.dumps(sample_terms)
                ))

def get_utc_now_iso() -> str:
    """Standardized timezone-aware UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()

