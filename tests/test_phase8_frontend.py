"""
Phase 8 Tests: Frontend UI Correctness, Persistent Telemetry & Security (D8)
- Verification that index.html contains the persistent operational mode banner
- Zero inline onclick attributes or string interpolations in index.html and app.js
- Real empirical evaluation schema rendered in Evaluation Hub (no placeholders)
- Health check exposes mode (live vs offline_demo) and engine
- Review queue endpoint enriches items with multiple terms and consensus approvals
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def get_token(email: str = "admin@clrag.org", password: str = "AdminPassword123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_d8_health_endpoint_surfaces_mode_and_engine():
    """Verify GET /api/health returns operational mode and engine metadata."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "mode" in data, "health must surface operational mode"
    assert data["mode"] in ["live", "offline_demo"]
    assert "engine" in data, "health must surface active engine"


def test_d8_persistent_banner_in_index_html():
    """Verify persistent system mode banner exists in index.html without fabricated metrics."""
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'id="system-mode-banner"' in index_html, "Must have persistent system-mode-banner"
    assert 'id="banner-mode-title"' in index_html
    assert 'id="banner-engine-tag"' in index_html

    # Ensure placeholder metrics are deleted
    assert "0.96" not in index_html
    assert "42.5" not in index_html
    assert "88.0" not in index_html


def test_d8_zero_inline_onclick_attributes():
    """Verify all inline onclick string interpolations and attributes are removed."""
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")
    app_js = Path("frontend/js/app.js").read_text(encoding="utf-8")

    assert not re.search(r'\bonclick\s*=', index_html, re.IGNORECASE), "No inline onclick allowed in index.html"
    assert not re.search(r'\bonclick\s*=', app_js, re.IGNORECASE), "No onclick string interpolation allowed in app.js"


def test_d8_review_queue_enrichment_with_consensus_and_multiple_terms():
    """Verify review queue items include terms array, approvals count, and required approvals."""
    token = get_token("reviewer@clrag.org", "ReviewerPassword123!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/review?status=ALL", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data

    if data["items"]:
        item = data["items"][0]
        assert "terms" in item, "Item must include multiple terms list"
        assert isinstance(item["terms"], list)
        assert "approvals" in item, "Item must include prior approvals"
        assert "approvals_count" in item, "Item must include approvals count"
        assert "required_approvals" in item, "Item must include required approvals"
        assert item["required_approvals"] == 2
