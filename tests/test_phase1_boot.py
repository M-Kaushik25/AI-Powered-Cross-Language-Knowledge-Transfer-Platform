import sqlite3

from fastapi.testclient import TestClient

from backend.database import init_db
from backend.main import app

client = TestClient(app)

def test_d1_requirements_has_email_validator():
    """D1 reproduction: verify requirements.txt explicitly specifies email-validator."""
    with open("requirements.txt", "r", encoding="utf-8") as f:
        content = f.read()
    assert "email-validator" in content, "requirements.txt must contain email-validator to prevent install failure"

def test_d2_clean_boot_creates_space_and_document(tmp_path):
    """
    D2 reproduction: On clean boot, both knowledge space and sample document must be created.
    Furthermore, seeding must be independently idempotent: if users already exist,
    missing workspaces and documents must still be seeded.
    """
    from backend.database import seed_all
    test_db = str(tmp_path / "boot_test.db")
    init_db(test_db)

    # Run unified seed routine
    seed_all(test_db)

    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    try:
        users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        spaces = conn.execute("SELECT COUNT(*) as c FROM knowledge_spaces").fetchone()["c"]
        docs = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]

        assert users >= 3, f"Expected at least 3 users, got {users}"
        assert spaces >= 1, f"Expected at least 1 knowledge space on clean boot, got {spaces}"
        assert docs >= 1, f"Expected at least 1 document on clean boot, got {docs}"

        # Test independent idempotency: delete space and doc, re-run seed_all
        conn.execute("DELETE FROM document_chunks")
        conn.execute("DELETE FROM documents")
        conn.execute("DELETE FROM knowledge_spaces")
        conn.commit()

        seed_all(test_db)

        spaces_after = conn.execute("SELECT COUNT(*) as c FROM knowledge_spaces").fetchone()["c"]
        docs_after = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]
        assert spaces_after >= 1, "Seed should recreate workspace even if users already exist"
        assert docs_after >= 1, "Seed should recreate documents even if users already exist"
    finally:
        conn.close()

def test_d3_chat_unknown_space_returns_404():
    """
    D3 reproduction: POST /api/chat with an unknown space_id must return 404, not 500.
    """
    token = client.post("/api/auth/login", json={
        "email": "user@clrag.org",
        "password": "UserPassword123!"
    }).json()["access_token"]

    response = client.post(
        "/api/chat",
        json={
            "space_id": "non-existent-space-uuid-00000",
            "question": "What is fault tolerance?",
            "target_lang": "en"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404, f"Expected 404 for unknown space_id, got {response.status_code}: {response.text}"
    assert "not found" in response.json()["detail"].lower()

def test_documents_unknown_space_returns_404():
    """Verify document endpoints return 404 for unknown space_id."""
    token = client.post("/api/auth/login", json={
        "email": "user@clrag.org",
        "password": "UserPassword123!"
    }).json()["access_token"]

    response = client.get(
        "/api/documents/spaces/non-existent-space-uuid-00000",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
