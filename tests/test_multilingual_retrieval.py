from backend.database import get_db, get_utc_now_iso
from backend.services.kg_service import kg_service
from backend.services.rag_service import rag_service


def test_cross_lingual_retrieval_hindi_and_tamil():
    """
    Validates cross-lingual semantic retrieval:
    English technical documents retrieved via Hindi and Tamil domain queries.
    """
    now = get_utc_now_iso()
    space_id = "test_multilingual_space"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        user = cursor.fetchone()
        user_id = user["id"] if user else "test_user"
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_spaces (id, user_id, name, domain, created_at)
            VALUES (?, ?, 'Cloud Reliability Space', 'cloud_computing', ?)
        """, (space_id, user_id, now))

    # Ingest English technical chunk
    content = (
        "Fault tolerance guarantees high availability in distributed architectures. "
        "A circuit breaker monitors downstream services and isolates cascading failures automatically."
    )
    ingest_res = rag_service.ingest_document(
        space_id=space_id,
        filename="reliability_patterns.txt",
        content=content,
        file_type="txt",
        domain="cloud_computing"
    )
    assert ingest_res["status"] == "READY"

    # Query 1: Hindi query asking about fault tolerance
    # "फॉल्ट टॉलेरेंस उच्च उपलब्धता कैसे प्रदान करता है?"
    hi_query = "फॉल्ट टॉलेरेंस उच्च उपलब्धता कैसे प्रदान करता है?"
    hi_results = rag_service.search_chunks(space_id=space_id, query=hi_query, top_k=2)
    assert len(hi_results) >= 1
    assert hi_results[0]["filename"] == "reliability_patterns.txt"
    assert hi_results[0]["score"] >= 0.35, f"Expected cross-lingual score >= 0.35, got {hi_results[0]['score']}"

    # Query 2: Tamil query asking about circuit breaker isolating failures
    # "சுற்று முறிப்பான் பிழைகளை எவ்வாறு தனிமைப்படுத்துகிறது?"
    ta_query = "சுற்று முறிப்பான் பிழைகளை எவ்வாறு தனிமைப்படுத்துகிறது?"
    ta_results = rag_service.search_chunks(space_id=space_id, query=ta_query, top_k=2)
    assert len(ta_results) >= 1
    assert ta_results[0]["filename"] == "reliability_patterns.txt"
    assert ta_results[0]["score"] >= 0.35, f"Expected cross-lingual score >= 0.35, got {ta_results[0]['score']}"

def test_linguistic_candidate_term_extraction():
    """
    Validates POS-style compound extraction, acronym detection, and C-Value scoring.
    """
    sample_text = (
        "The distributed database utilizes an active monitoring agent and zero-trust protocol "
        "to ensure strict SLA compliance."
    )
    extracted = kg_service.extract_candidate_terms(sample_text, domain="cloud_computing")
    sources = [e["source_term"] for e in extracted]

    # Verify acronym detection
    assert "SLA" in sources
    sla_item = next(e for e in extracted if e["source_term"] == "SLA")
    assert sla_item["is_new"] is True

    # Verify compound term extraction
    assert any("zero-trust" in s or "active monitoring" in s or "distributed database" in s for s in sources)
    new_compounds = [e for e in extracted if e["is_new"] and e["source_term"] != "SLA"]
    assert len(new_compounds) >= 1
    for c in new_compounds:
        assert 0.50 <= c["confidence"] <= 0.85
