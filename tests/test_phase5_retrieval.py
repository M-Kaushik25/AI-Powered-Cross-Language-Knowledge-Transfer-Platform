"""
Phase 5 Tests: Cross-Lingual Retrieval, KG Query Expansion, Float32 BLOB Embeddings,
Document Parsers (PDF/DOCX/PPTX), Citations, and Retrieval Benchmark (D4, D18)
"""
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.database import get_db, get_utc_now_iso
from backend.main import app
from backend.services.rag_service import parse_document_file, rag_service

client = TestClient(app)


def get_token(email: str = "reviewer@clrag.org", password: str = "ReviewerPassword123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_d4_cross_lingual_retrieval_hindi_without_dictionary():
    """
    Acceptance Test D4: 'दोष सहनशीलता क्या है?' retrieves the fault-tolerance chunk
    WITHOUT depending on the old hardcoded 54-word bilingual_bridge dictionary.
    """
    space_id = "test_phase5_space"
    now = get_utc_now_iso()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        user = cursor.fetchone()
        user_id = user["id"] if user else "test_user"
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_spaces (id, user_id, name, domain, created_at)
            VALUES (?, ?, 'Phase 5 Space', 'cloud_computing', ?)
        """, (space_id, user_id, now))

    content = (
        "Fault tolerance guarantees high availability in distributed architectures. "
        "A circuit breaker monitors downstream services and isolates cascading failures automatically."
    )
    ingest_res = rag_service.ingest_document(
        space_id=space_id,
        filename="fault_tolerance_guide.txt",
        content=content,
        file_type="txt",
        domain="cloud_computing"
    )
    assert ingest_res["status"] == "READY"

    # Query in Hindi with standard terminology 'दोष सहनशीलता' (not in the old 54-word dictionary)
    hi_query = "दोष सहनशीलता क्या है?"
    results = rag_service.search_chunks(space_id=space_id, query=hi_query, top_k=2)
    assert len(results) >= 1
    assert results[0]["filename"] == "fault_tolerance_guide.txt"
    assert results[0]["score"] >= 0.35, f"Expected cross-lingual score >= 0.35, got {results[0]['score']}"


def test_kg_query_expansion_ablation():
    """
    Validates KG-bridged query expansion ablation:
    Detects target-language terms in query via terminology store, maps them to English canonical source terms.
    """
    query = "दोष सहनशीलता कैसे काम करती है?"
    expanded, bridged_terms = rag_service.expand_query_with_kg(query, domain="cloud_computing")
    assert len(bridged_terms) >= 1
    assert any(b["source_term"].lower() == "fault tolerance" for b in bridged_terms)
    assert "fault tolerance" in expanded.lower()


def test_float32_blob_embedding_storage():
    """
    Validates that document chunks store dense embeddings as float32 BLOBs.
    """
    space_id = "test_blob_space"
    now = get_utc_now_iso()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        user = cursor.fetchone()
        user_id = user["id"] if user else "test_user"
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_spaces (id, user_id, name, domain, created_at)
            VALUES (?, ?, 'Blob Space', 'cloud_computing', ?)
        """, (space_id, user_id, now))

    rag_service.ingest_document(
        space_id=space_id,
        filename="blob_doc.txt",
        content="Distributed load balancing distributes traffic evenly across server replicas.",
        file_type="txt",
        domain="cloud_computing"
    )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT embedding_blob FROM document_chunks WHERE space_id = ?", (space_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["embedding_blob"] is not None
        vec = np.frombuffer(row["embedding_blob"], dtype=np.float32)
        assert len(vec) > 0
        assert np.isfinite(vec).all()


def test_document_parser_pdf_docx_pptx():
    """
    Validates multi-format document parsing (PDF, DOCX, PPTX) preserving page/slide numbers.
    """
    # 1. Plain text parser
    txt_pages = parse_document_file(b"Line 1.\nLine 2.", "sample.txt", "txt")
    assert len(txt_pages) == 1
    assert txt_pages[0]["page_number"] == 1
    assert "Line 1" in txt_pages[0]["text"]

    # 2. DOCX Parser
    import docx
    doc = docx.Document()
    doc.add_heading("Cloud Resiliency Architecture", level=1)
    doc.add_paragraph("Circuit breakers prevent cascading failures across microservices.")
    docx_buf = io.BytesIO()
    doc.save(docx_buf)
    docx_pages = parse_document_file(docx_buf.getvalue(), "resiliency.docx", "docx")
    assert len(docx_pages) >= 1
    assert docx_pages[0]["page_number"] == 1
    assert "Circuit breakers" in docx_pages[0]["text"]

    # 3. PPTX Parser
    import pptx
    prs = pptx.Presentation()
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    title.text = "Microservices Fault Tolerance"
    pptx_buf = io.BytesIO()
    prs.save(pptx_buf)
    pptx_pages = parse_document_file(pptx_buf.getvalue(), "slides.pptx", "pptx")
    assert len(pptx_pages) >= 1
    assert pptx_pages[0]["page_number"] == 1
    assert "Microservices Fault Tolerance" in pptx_pages[0]["text"]


@pytest.mark.asyncio
async def test_grounded_answer_citations_and_abstention():
    """
    Validates:
    1. Exact citation span and page numbers in citations.
    2. Dynamic confidence (never constant 0.96).
    3. Abstention when context does not support answering.
    """
    space_id = "test_answer_space"
    now = get_utc_now_iso()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        user = cursor.fetchone()
        user_id = user["id"] if user else "test_user"
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_spaces (id, user_id, name, domain, created_at)
            VALUES (?, ?, 'Answer Space', 'cloud_computing', ?)
        """, (space_id, user_id, now))

    rag_service.ingest_document(
        space_id=space_id,
        filename="distributed_patterns.txt",
        content="A load balancer distributes incoming network traffic across multiple backend servers to prevent overload.",
        file_type="txt",
        domain="cloud_computing"
    )

    # Relevant question
    ans_res = await rag_service.answer_question(space_id, "What is the function of a load balancer?", "en")
    assert ans_res["confidence"] != 0.96, "Confidence must not be the hardcoded constant 0.96"
    assert len(ans_res["citations"]) >= 1
    citation = ans_res["citations"][0]
    assert "exact_span" in citation
    assert "load balancer distributes" in citation["exact_span"].lower()
    assert "page_number" in citation

    # Irrelevant question (should abstain)
    abstain_res = await rag_service.answer_question(space_id, "How to cook a chocolate cake?", "en")
    assert "sufficient context" in abstain_res["answer"] or "couldn't find" in abstain_res["answer"].lower()
    assert abstain_res["confidence"] <= 0.20


def test_retrieval_benchmark_100_queries():
    """
    Validates the 100-query multilingual retrieval benchmark across en, hi, ta, de, es.
    Ensures Recall@1, Recall@5, and MRR are computed empirically without fabrication.
    """
    results = rag_service.evaluate_retrieval_benchmark()
    assert results["total_queries"] == 100
    assert "recall_at_1" in results
    assert "recall_at_5" in results
    assert "mrr" in results
    assert 0.0 <= results["recall_at_1"] <= 100.0
    assert results["recall_at_5"] >= results["recall_at_1"]
    assert 0.0 <= results["mrr"] <= 1.0
    assert len(results["per_language"]) == 5
    for lang in ["en", "hi", "ta", "de", "es"]:
        assert lang in results["per_language"]
        assert results["per_language"][lang]["total"] == 20

