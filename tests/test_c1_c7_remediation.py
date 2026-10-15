"""
Regression and Verification Suite for Drawbacks C1 through C7 Remediation.
- C1: Multi-round progression & immutable gold reference dictionary without sentence-prefix slicing.
- C2: Wall-clock latency telemetry (p50, p95) across all comparative conditions.
- C3: 10 diverse syntactic benchmark templates with per-item term translations & clean Tamil casings.
- C4: Deterministic blake2b multilingual embeddings independent of PYTHONHASHSEED with KG bridging.
- C5: Segment needs_refresh flag updated on term approval and historical job refresh endpoint.
- C6: Indic morphological stem matching in verifier and removal of hardcoded ece_estimate 0.042.
- C7: Role privilege escalation prevented in production environment.
"""
import hashlib
import json
import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.config import BASE_DIR
from backend.database import get_db
from backend.main import app
from backend.services.eval_service import eval_service
from backend.services.kg_service import kg_service
from backend.services.multi_agent_service import multi_agent_service
from backend.services.rag_service import DenseMultilingualEmbedding

client = TestClient(app)


def test_c1_eval_does_not_corrupt_kg_with_sentence_prefix():
    """Verify that multi-round evolution improves TSR and never pollutes KG with sentence prefixes."""
    res = eval_service.run_comparative_evaluation(domain="cloud_computing", target_lang="hi", sample_size=6)
    rounds = res["evolution_rounds"]
    assert len(rounds) == 3

    r1_tsr = rounds[0]["tsr"]
    r2_tsr = rounds[1]["tsr"]
    r3_tsr = rounds[2]["tsr"]

    # Round 1 (Cold Start) must be less than Round 2, and Round 2 <= Round 3
    assert r1_tsr < r2_tsr <= r3_tsr, f"Expected r1 ({r1_tsr}) < r2 ({r2_tsr}) <= r3 ({r3_tsr})"

    # Verify no term in active gold terms was corrupted by sentence prefixes
    for term, trans in eval_service._active_gold_terms.items():
        assert "लचीले क्लाउड" not in trans
        assert "में, " not in trans


def test_c2_eval_metrics_include_latency_percentiles():
    """Verify latency_p50 and latency_p95 are computed and present across all conditions."""
    res = eval_service.run_comparative_evaluation(domain="cloud_computing", target_lang="hi", sample_size=4)
    conditions = res["conditions"]
    for cond_name, metrics in conditions.items():
        assert "latency_p50" in metrics, f"Missing latency_p50 in {cond_name}"
        assert "latency_p95" in metrics, f"Missing latency_p95 in {cond_name}"
        assert metrics["latency_p50"] >= 0.0
        assert metrics["latency_p95"] >= metrics["latency_p50"]


def test_c3_benchmark_sentence_diversity():
    """Verify benchmark sentences use at least 8 distinct structures and include term_translations."""
    bio_path = BASE_DIR / "data" / "evaluation" / "benchmark_biomedical.json"
    assert bio_path.exists()
    with open(bio_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data["items"]
    assert len(items) == 100

    # Extract distinct prefixes
    prefixes = set(it["source_en"].split(",")[0].strip() for it in items)
    assert len(prefixes) >= 8, f"Expected at least 8 distinct templates, got {len(prefixes)}"

    for it in items:
        assert "term_translations" in it
        assert len(it["term_translations"]) >= 2
        ta_trans = it["gold_translations"]["ta"]
        assert " ஐ" not in ta_trans, "Found detached ' ஐ' token in Tamil gold reference"


def test_c4_deterministic_blake2b_embeddings():
    """Verify blake2b deterministic vector hashing and KG cross-lingual semantic bridging."""
    emb = DenseMultilingualEmbedding()
    v1 = emb._fallback_multilingual_vector("fault tolerance")
    v2 = emb._fallback_multilingual_vector("fault tolerance")
    assert np.array_equal(v1, v2)

    # Verify hash uses blake2b
    token = "test_token_c4"
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
    expected_idx = int.from_bytes(digest, "little") % emb.dim
    assert emb._det_hash(token, emb.dim) == expected_idx

    # Verify cross-lingual bridging produces positive similarity
    vec_hi = emb.encode("त्रुटि सहिष्णुता")
    vec_en = emb.encode("fault tolerance")
    sim = emb.cosine_similarity(vec_hi, vec_en)
    assert sim > 0.0, f"Expected positive cross-lingual similarity, got {sim}"


@pytest.mark.asyncio
async def test_c5_segment_needs_refresh_flagged_on_kg_update():
    """Verify translation_segments.needs_refresh flag triggers upon term correction and resets on refresh."""
    job_id = f"test_job_{uuid.uuid4().hex[:8]}"

    # Translate segment containing fault tolerance
    await multi_agent_service.translate_document(
        source_text="In resilient cloud topologies, fault tolerance provides operational stability.",
        target_lang="hi",
        domain="cloud_computing",
        job_id=job_id
    )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, needs_refresh FROM translation_segments WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["needs_refresh"] == 0

    # Apply correction to fault tolerance
    kg_service.apply_human_correction(
        source_term="fault tolerance",
        target_lang="hi",
        corrected_translation="त्रुटि सहिष्णुता (अपडेटेड)",
        domain="cloud_computing",
        reviewer_notes="Updating translation for test"
    )

    # Verify needs_refresh is now flagged (1)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT needs_refresh FROM translation_segments WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["needs_refresh"] == 1

    # Call refresh_stale_segments and verify flag resets to 0
    refreshed = await multi_agent_service.refresh_stale_segments(job_id=job_id)
    assert len(refreshed) >= 1

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT needs_refresh FROM translation_segments WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["needs_refresh"] == 0

    # Restore seed translation to prevent side effects in subsequent retrieval tests
    kg_service.apply_human_correction(
        source_term="fault tolerance",
        target_lang="hi",
        corrected_translation="त्रुटि सहिष्णुता (दोष सहनशीलता)",
        domain="cloud_computing",
        reviewer_notes="Restore seed translation"
    )


def test_c6_indic_stem_verifier_and_no_hardcoded_ece():
    """Verify Indic morphological stem matching in verifier and absence of hardcoded ece_estimate 0.042."""
    constraints = [{"source_term": "fault tolerance", "target_term": "பிழை சகிப்புத்தன்மை"}]
    # Tamil inflected form with case suffix
    draft = "கணினியில் பிழை சகிப்புத்தன்மையை உறுதி செய்ய வேண்டும்."
    res = multi_agent_service._run_verifier_agent(
        source_segment="Ensure fault tolerance in the system.",
        draft_translation=draft,
        constraints=constraints,
        target_lang="ta"
    )
    assert res["score"] == 1.0
    assert len(res["satisfied"]) == 1

    # Check that 0.042 does not appear in backend/services/multi_agent_service.py
    mas_path = BASE_DIR / "backend" / "services" / "multi_agent_service.py"
    content = mas_path.read_text(encoding="utf-8")
    assert "0.042" not in content


def test_c7_production_register_blocks_admin_escalation(monkeypatch):
    """Verify registration in production environment assigns USER role regardless of requested role."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    unique_email = f"attacker_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "Attacker",
        "email": unique_email,
        "password": "Password123!",
        "role": "ADMIN"
    })
    assert res.status_code == 201
    user_data = res.json()["user"]
    assert user_data["role"] == "USER"
