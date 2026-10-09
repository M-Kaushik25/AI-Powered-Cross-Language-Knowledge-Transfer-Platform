from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def test_d7_unauthenticated_endpoints_return_401():
    """
    D7 reproduction: Verify all sensitive endpoints return 401 Unauthorized
    when accessed without a valid JWT token, except /api/health and /api/auth.
    """
    # Allowed endpoints without token
    health_res = client.get("/api/health")
    assert health_res.status_code == 200

    # Protected endpoints that must reject unauthenticated requests
    protected_get_routes = [
        "/api/stats",
        "/api/documents/spaces",
        "/api/documents",
        "/api/kg/terms",
        "/api/kg/concepts",
        "/api/kg/relationships",
        "/api/review",
        "/api/chat/conversations",
        "/api/eval/runs"
    ]

    for route in protected_get_routes:
        res = client.get(route)
        assert res.status_code == 401, f"Route {route} allowed unauthenticated access (got {res.status_code})"

    # Protected POST routes
    protected_post_routes = [
        ("/api/eval/run", {"domain": "cloud_computing", "target_lang": "hi"}),
        ("/api/translate", {"source_text": "Fault tolerance", "target_lang": "hi", "domain": "cloud_computing"}),
        ("/api/adaptive", {"source_text": "Fault tolerance", "target_lang": "hi", "domain": "cloud_computing"}),
    ]

    for route, payload in protected_post_routes:
        res = client.post(route, json=payload)
        assert res.status_code == 401, f"POST route {route} allowed unauthenticated access (got {res.status_code})"

def test_eval_run_requires_admin_role():
    """Verify that running evaluations strictly requires ADMIN role."""
    # Login as regular user
    user_token = client.post("/api/auth/login", json={
        "email": "user@clrag.org",
        "password": "UserPassword123!"
    }).json()["access_token"]

    res_user = client.post(
        "/api/eval/run",
        json={"domain": "cloud_computing", "target_lang": "hi"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res_user.status_code == 403, f"Expected 403 for USER role on /api/eval/run, got {res_user.status_code}"

    # Login as reviewer
    rev_token = client.post("/api/auth/login", json={
        "email": "reviewer@clrag.org",
        "password": "ReviewerPassword123!"
    }).json()["access_token"]

    res_rev = client.post(
        "/api/eval/run",
        json={"domain": "cloud_computing", "target_lang": "hi"},
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert res_rev.status_code == 403, f"Expected 403 for REVIEWER role on /api/eval/run, got {res_rev.status_code}"

def test_cross_tenant_isolation(tmp_path):
    """
    Verify multi-tenancy: users in Tenant A cannot see or access spaces/documents/terms/reviews in Tenant B.
    """
    import uuid

    from backend.database import get_db, get_utc_now_iso
    from backend.services.auth_service import create_access_token, hash_password

    now = get_utc_now_iso()
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    space_b_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.cursor()
        # Create user in tenant_a
        cursor.execute("""
            INSERT INTO users (id, name, email, password_hash, role, preferred_lang, tenant_id, created_at)
            VALUES (?, 'User Org A', 'user_a@orga.com', ?, 'USER', 'en', 'tenant_a', ?)
        """, (user_a_id, hash_password("PasswordA123!"), now))

        # Create user in tenant_b
        cursor.execute("""
            INSERT INTO users (id, name, email, password_hash, role, preferred_lang, tenant_id, created_at)
            VALUES (?, 'User Org B', 'user_b@orgb.com', ?, 'USER', 'en', 'tenant_b', ?)
        """, (user_b_id, hash_password("PasswordB123!"), now))

        # Create space belonging to tenant_b
        cursor.execute("""
            INSERT INTO knowledge_spaces (id, user_id, tenant_id, name, description, domain, default_lang, created_at)
            VALUES (?, ?, 'tenant_b', 'Tenant B Confidential Space', 'Secret spec', 'cloud_computing', 'en', ?)
        """, (space_b_id, user_b_id, now))

    token_a = create_access_token({"sub": user_a_id, "role": "USER", "tenant_id": "tenant_a"})

    # User A tries to list spaces - should not see Tenant B's space
    spaces_res = client.get("/api/documents/spaces", headers={"Authorization": f"Bearer {token_a}"})
    assert spaces_res.status_code == 200
    space_ids = [s["id"] for s in spaces_res.json()]
    assert space_b_id not in space_ids, "Tenant A user should not see Tenant B space in list"

    # User A tries to access Tenant B space directly
    single_res = client.get(f"/api/documents/spaces/{space_b_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert single_res.status_code == 404, "Tenant A user should get 404 when querying Tenant B space"
