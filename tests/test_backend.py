import pytest
import asyncio
from backend.database import init_db, get_db
from backend.services.kg_service import kg_service
from backend.services.multi_agent_service import multi_agent_service
from backend.services.adaptive_service import adaptive_service
from backend.services.rag_service import rag_service
from backend.services.eval_service import eval_service

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()
    kg_service.seed_database_if_empty()

def test_kg_seed_and_terms():
    terms = kg_service.get_all_terms()
    assert len(terms) >= 15
    sources = [t["source_term"] for t in terms]
    assert "fault tolerance" in sources
    assert "load balancer" in sources
    assert "circuit breaker" in sources

def test_candidate_term_extraction():
    sample_text = "The cluster implements a load balancer and guarantees fault tolerance under high SLA demand."
    extracted = kg_service.extract_candidate_terms(sample_text, domain="cloud_computing")
    found_sources = [e["source_term"] for e in extracted]
    assert "load balancer" in found_sources
    assert "fault tolerance" in found_sources
    assert any(e["source_term"] == "SLA" for e in extracted)

def test_kg_self_evolution_feedback_loop():
    # Simulate a human expert correcting a translation
    term = "cache invalidation"
    res = kg_service.apply_human_correction(
        source_term=term,
        target_lang="hi",
        corrected_translation="सटीक कैश अमान्यकरण (विशेषज्ञ स्वीकृत)",
        domain="cloud_computing",
        reviewer_notes="Standardized per IEEE 2026 guidelines"
    )
    assert res["status"] == "APPROVED"
    assert res["new_version"] >= 2
    assert res["confidence"] == 1.0

    # Verify audit log recorded provenance
    detail = kg_service.get_term_by_id(res["term_id"])
    assert detail is not None
    assert len(detail["audit_history"]) >= 1

    # Verify subsequent lookup retrieves the updated term
    constraints = kg_service.lookup_constraints("We need cache invalidation now.", "cloud_computing", "hi")
    assert any("सटीक कैश अमान्यकरण" in c["target_term"] for c in constraints)

@pytest.mark.asyncio
async def test_multi_agent_pipeline():
    source_sentence = "A reliable load balancer distributes traffic to guarantee fault tolerance."
    result = await multi_agent_service.translate_document(
        source_text=source_sentence,
        target_lang="hi",
        domain="cloud_computing"
    )
    assert result["segment_count"] == 1
    assert result["terms_encountered"] >= 2
    assert result["avg_confidence"] > 0.5
    seg = result["segments"][0]
    assert "verifier_report" in seg
    assert "critic_report" in seg
    assert "calibrated_confidence" in seg

@pytest.mark.asyncio
async def test_adaptive_summarization():
    text = "A circuit breaker trips automatically when downstream failure thresholds exceed safety margins."
    res = await adaptive_service.generate_adaptive_summaries(text, "en", "distributed_systems")
    assert "novice_adaptation" in res
    assert "expert_adaptation" in res
    assert res["novice_adaptation"]["complexity_index"] < res["expert_adaptation"]["complexity_index"]

def test_rag_semantic_search():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password_hash, created_at) VALUES ('u_test', 'Tester', 'tester@clrag.ai', 'pwd', ?)", (now,))
        cursor.execute("INSERT OR IGNORE INTO knowledge_spaces (id, user_id, name, domain, created_at) VALUES ('test_space_1', 'u_test', 'Test Space', 'distributed_systems', ?)", (now,))

    # Ingest document
    doc_res = rag_service.ingest_document(
        space_id="test_space_1",
        filename="distributed_patterns.txt",
        content="The circuit breaker pattern isolates failures to guarantee high availability in distributed architectures.",
        file_type="txt",
        domain="distributed_systems"
    )
    assert doc_res["status"] == "READY"
    
    # Query
    results = rag_service.search_chunks("test_space_1", "circuit breaker failure", top_k=2)
    assert len(results) >= 1
    assert results[0]["filename"] == "distributed_patterns.txt"
    assert "circuit breaker" in results[0]["content"].lower()

def test_eval_ablation_runner():
    res = eval_service.run_comprehensive_ablation(domain="cloud_computing")
    assert "metrics" in res
    rounds = res["metrics"]["rounds"]
    assert len(rounds) == 4
    # Verify TSR strictly increases across rounds
    assert rounds[0]["tsr_percentage"] < rounds[1]["tsr_percentage"] < rounds[3]["tsr_percentage"]
    # Verify review volume strictly decreases across rounds
    assert rounds[0]["review_volume_percentage"] > rounds[1]["review_volume_percentage"] > rounds[3]["review_volume_percentage"]
