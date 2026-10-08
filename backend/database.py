import sqlite3
import json
import uuid
from datetime import datetime
from contextlib import contextmanager
from backend.config import DB_PATH

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'USER',
            preferred_lang TEXT NOT NULL DEFAULT 'en',
            created_at TEXT NOT NULL
        )
        """)
        
        # 2. Knowledge Spaces
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
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'READY',
            chunk_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (space_id) REFERENCES knowledge_spaces (id) ON DELETE CASCADE
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
        
        # 5. Living Terminology Knowledge Graph (terms)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id TEXT PRIMARY KEY,
            source_term TEXT NOT NULL,
            domain TEXT NOT NULL,
            definition TEXT,
            translations_json TEXT NOT NULL DEFAULT '{}',
            version INTEGER NOT NULL DEFAULT 1,
            confidence REAL NOT NULL DEFAULT 0.90,
            status TEXT NOT NULL DEFAULT 'APPROVED',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_term, domain)
        )
        """)
        
        # 6. Term Audit Log (provenance & self-evolution history)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS term_audit_log (
            id TEXT PRIMARY KEY,
            term_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            action TEXT NOT NULL,
            changed_by TEXT NOT NULL DEFAULT 'HUMAN_REVIEWER',
            old_value_json TEXT,
            new_value_json TEXT,
            reviewer_notes TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (term_id) REFERENCES terms (id) ON DELETE CASCADE
        )
        """)
        
        # 7. Confidence-Gated Review Queue
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
            status TEXT NOT NULL DEFAULT 'PENDING',
            reviewer_comment TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (term_id) REFERENCES terms (id) ON DELETE SET NULL
        )
        """)
        
        # 8. Conversations
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
        
        # 9. Messages
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
        
        # 10. Evaluation Runs
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
        
        # Create Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_terms_source_domain ON terms(source_term, domain);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_space ON document_chunks(space_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_term ON term_audit_log(term_id);")

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
