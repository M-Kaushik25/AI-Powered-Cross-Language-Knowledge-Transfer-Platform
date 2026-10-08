from fastapi.testclient import TestClient

from backend.main import app
from backend.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

client = TestClient(app)

def test_password_hashing():
    plain = "SuperSecure123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_creation_and_decoding():
    token = create_access_token({"sub": "user_123", "role": "REVIEWER"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user_123"
    assert payload["role"] == "REVIEWER"
    assert "exp" in payload

def test_auth_login_endpoint():
    # Login as seeded admin
    res = client.post("/api/auth/login", json={
        "email": "admin@clrag.org",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert data["token_type"] == "bearer"

    # Bad password
    res_bad = client.post("/api/auth/login", json={
        "email": "admin@clrag.org",
        "password": "IncorrectPassword"
    })
    assert res_bad.status_code == 401

def test_auth_me_endpoint():
    # Login to get token
    login_res = client.post("/api/auth/login", json={
        "email": "reviewer@clrag.org",
        "password": "ReviewerPassword123!"
    })
    token = login_res.json()["access_token"]

    # Valid token
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "reviewer@clrag.org"
    assert res.json()["role"] == "REVIEWER"

    # Missing token
    res_no_auth = client.get("/api/auth/me")
    assert res_no_auth.status_code == 401

def test_rbac_endpoint_access_control():
    # Get tokens for user, reviewer, and admin
    admin_token = client.post("/api/auth/login", json={
        "email": "admin@clrag.org",
        "password": "AdminPassword123!"
    }).json()["access_token"]

    reviewer_token = client.post("/api/auth/login", json={
        "email": "reviewer@clrag.org",
        "password": "ReviewerPassword123!"
    }).json()["access_token"]

    user_token = client.post("/api/auth/login", json={
        "email": "user@clrag.org",
        "password": "UserPassword123!"
    }).json()["access_token"]

    # 1. POST /api/kg/terms requires ADMIN or REVIEWER
    term_payload = {
        "source_term": "distributed transactions",
        "domain": "cloud_computing",
        "target_lang": "hi",
        "translation": "वितरित लेनदेन"
    }

    # Standard USER should be rejected with 403 Forbidden
    res_user = client.post("/api/kg/terms", json=term_payload, headers={"Authorization": f"Bearer {user_token}"})
    assert res_user.status_code == 403

    # REVIEWER should succeed
    res_reviewer = client.post("/api/kg/terms", json=term_payload, headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res_reviewer.status_code == 200
    assert res_reviewer.json()["status"] == "SUCCESS"

    # 2. Candidate staging is allowed for regular USER
    cand_payload = {
        "source_term": "edge runtime",
        "domain": "cloud_computing",
        "target_lang": "hi",
        "proposed_translation": "एज रनटाईम"
    }
    res_cand = client.post("/api/kg/candidates", json=cand_payload, headers={"Authorization": f"Bearer {user_token}"})
    assert res_cand.status_code == 200
    assert res_cand.json()["data"]["status"] == "CANDIDATE"

    # 3. Rollback requires ADMIN
    term_id = res_reviewer.json()["data"]["term_id"]
    rollback_payload = {"target_version": 1, "reason": "Test rollback"}

    # REVIEWER attempting rollback should be rejected (403)
    res_rb_reviewer = client.post(f"/api/kg/terms/{term_id}/rollback", json=rollback_payload, headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res_rb_reviewer.status_code == 403

    # ADMIN attempting rollback should succeed
    res_rb_admin = client.post(f"/api/kg/terms/{term_id}/rollback", json=rollback_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res_rb_admin.status_code == 200
