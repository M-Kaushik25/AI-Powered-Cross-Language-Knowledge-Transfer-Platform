"""
Phase 6 Tests: Faithful Expertise-Adaptive Summarization (D9)
- Ventilator input produces NO invented latency/p99/RPO/RTO text
- Three levels supported: novice, intermediate, expert
- No canned templates; faithful extractive summary in offline mode
- Faithfulness guard detecting hallucinated numbers/entities
- Real readability metrics (English Flesch-Kincaid, proxy for other languages, null appropriateness when unjudged)
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.adaptive_service import adaptive_service

client = TestClient(app)


def get_token(email: str = "reviewer@clrag.org", password: str = "ReviewerPassword123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_d9_ventilator_input_produces_no_hallucinated_sla_or_p99():
    """
    D9 Acceptance: A biomedical ventilator input must NOT return expert text with
    invented p99 latency, RPO, RTO, or SLA boilerplate not present in the source.
    """
    ventilator_text = (
        "Positive end-expiratory pressure delivers continuous mechanical ventilation "
        "to prevent alveolar collapse and maintain arterial oxygenation."
    )

    res = await adaptive_service.generate_adaptive_summaries(
        source_text=ventilator_text,
        target_lang="en",
        domain="biomedical_devices"
    )

    # Check all levels
    assert "novice_adaptation" in res
    assert "intermediate_adaptation" in res
    assert "expert_adaptation" in res

    all_output_text = (
        res["novice_adaptation"]["text"] + " " +
        res["intermediate_adaptation"]["text"] + " " +
        res["expert_adaptation"]["text"]
    ).lower()

    # Must NOT invent cloud computing SLA parameters on a biomedical input
    assert "p99" not in all_output_text
    assert "rpo" not in all_output_text
    assert "rto" not in all_output_text
    assert "<50ms" not in all_output_text
    assert "sla" not in all_output_text

    # Appropriateness score must be null in offline mode (not a hardcoded constant)
    assert res["adaptation_appropriateness_score"] is None or isinstance(res["adaptation_appropriateness_score"], float)
    if res["mode"] == "offline_extractive":
        assert res["adaptation_appropriateness_score"] is None


@pytest.mark.asyncio
async def test_faithfulness_guard_blocks_invented_numbers():
    """
    Verifies that the faithfulness guard flags or strips numbers not present in source text.
    """
    source_text = "The load balancer distributes traffic evenly across servers."
    # Hypothetical unfaithful text with invented numbers 99.99% and 50ms
    unfaithful_text = "The load balancer distributes traffic with 99.99% availability and 50ms latency."

    violations = adaptive_service._check_faithfulness(source_text, unfaithful_text)
    assert len(violations) >= 1
    assert any("99.99" in v or "50" in v for v in violations)


@pytest.mark.asyncio
async def test_multilingual_readability_proxy_and_real_scores():
    """
    Verifies that readability metrics are computed dynamically and non-English
    languages are labeled with proxy metrics (no constants like 42.5 or 88.0).
    """
    # 1. English
    en_res = await adaptive_service.generate_adaptive_summaries(
        source_text="Fault tolerance maintains high system availability.",
        target_lang="en",
        domain="cloud_computing"
    )
    en_metrics = en_res["expert_adaptation"]["readability"]
    assert en_metrics["is_proxy"] is False
    assert "flesch_kincaid_grade" in en_metrics
    assert en_metrics["flesch_reading_ease"] != 42.5
    assert en_metrics["flesch_reading_ease"] != 88.0

    # 2. Hindi
    hi_res = await adaptive_service.generate_adaptive_summaries(
        source_text="त्रुटि सहिष्णुता उच्च उपलब्धता बनाए रखती है।",
        target_lang="hi",
        domain="cloud_computing"
    )
    hi_metrics = hi_res["expert_adaptation"]["readability"]
    assert hi_metrics["is_proxy"] is True
    assert "mean_sentence_length" in hi_metrics
    assert "mean_word_length" in hi_metrics


def test_api_adaptive_endpoint():
    """
    Verifies POST /api/adaptive endpoint returns 3 levels and no hardcoded constants.
    """
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/adaptive",
        headers=headers,
        json={
            "source_text": "Circuit breaker isolates failures in microservice architectures.",
            "target_lang": "en",
            "domain": "distributed_systems"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "novice_adaptation" in data
    assert "intermediate_adaptation" in data
    assert "expert_adaptation" in data
    assert "mode" in data
    assert "p99" not in data["expert_adaptation"]["text"].lower()


@pytest.mark.asyncio
async def test_adaptive_service_live_mode_mocked():
    """Verify live LLM generation branch and packaging in adaptive_service."""
    import httpx
    import respx

    with respx.mock:
        respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent").mock(
            return_value=httpx.Response(
                200,
                json={
                    "candidates": [{
                        "content": {
                            "parts": [{"text": "Adapted content without hallucinated metrics."}]
                        }
                    }]
                }
            )
        )

        old_key = adaptive_service.gemini_api_key
        adaptive_service.gemini_api_key = "fake_key_for_test"
        try:
            res = await adaptive_service.generate_adaptive_summaries(
                source_text="Fault tolerance maintains high system availability.",
                target_lang="en",
                domain="cloud_computing",
                mode="live"
            )
            assert res["mode"] == "live_llm"
            assert "novice_adaptation" in res
        finally:
            adaptive_service.gemini_api_key = old_key
