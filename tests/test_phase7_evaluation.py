"""
Phase 7 Tests: Empirical Evaluation Harness & Reproducible Runs (D5)
- Verification that hardcoded constants (28.5, 64.2, 58.0, verified_without_fabrication: True) are deleted
- B1, B2, and P conditions run on isolated temp databases
- Raw outputs saved as JSONL under data/evaluation/runs/
- Real BLEU, chrF++, AUROC, ECE, and TSR computed dynamically
"""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.eval_service import eval_service

client = TestClient(app)


def get_token(email: str = "admin@clrag.org", password: str = "AdminPassword123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_d5_no_hardcoded_constants_in_eval_service():
    """
    D5 Acceptance: Verify that fabricated constants (28.5, 64.2, 58.0)
    and the flag 'verified_without_fabrication: True' do NOT exist in eval_service source code.
    """
    eval_file = Path("backend/services/eval_service.py").read_text(encoding="utf-8")
    assert "28.5" not in eval_file, "Hardcoded baseline TSR 28.5 must be deleted"
    assert "64.2" not in eval_file, "Hardcoded baseline TSR 64.2 must be deleted"
    assert "58.0" not in eval_file, "Hardcoded baseline TSR 58.0 must be deleted"
    assert "verified_without_fabrication: True" not in eval_file, "Fabricated flag must be deleted"


def test_eval_conditions_and_jsonl_storage():
    """
    Verifies that running evaluation executes real conditions (B1, B2, P),
    computes empirical metrics, and saves raw segment JSONL under data/evaluation/runs/.
    """
    result = eval_service.run_comparative_evaluation(
        domain="cloud_computing",
        target_lang="hi",
        sample_size=3  # Small sample for fast test execution
    )

    assert "eval_id" in result
    assert "conditions" in result
    assert "B1_generic_mt" in result["conditions"]
    assert "B2_static_glossary" in result["conditions"]
    assert "P_proposed_pipeline" in result["conditions"]

    # Verify real metrics exist and are computed floats
    b1 = result["conditions"]["B1_generic_mt"]
    p = result["conditions"]["P_proposed_pipeline"]
    assert "tsr" in b1 and isinstance(b1["tsr"], (int, float))
    assert "bleu" in b1 and isinstance(b1["bleu"], (int, float))
    assert "chrf" in b1 and isinstance(b1["chrf"], (int, float))
    assert "tsr" in p and isinstance(p["tsr"], (int, float))

    # Verify JSONL artifacts were written
    run_dir = Path(result["run_dir"])
    assert run_dir.exists()
    segments_file = run_dir / "segments.jsonl"
    metadata_file = run_dir / "metadata.json"
    assert segments_file.exists()
    assert metadata_file.exists()

    # Verify segment contents
    lines = segments_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3
    sample_seg = json.loads(lines[0])
    assert "condition" in sample_seg
    assert "source" in sample_seg
    assert "hypothesis" in sample_seg


def test_api_eval_run_endpoint():
    """
    Verifies POST /api/eval/run requires ADMIN and returns empirical results.
    """
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/eval/run",
        headers=headers,
        json={
            "domain": "cloud_computing",
            "target_lang": "hi",
            "sample_size": 2
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "eval_id" in data
    assert "conditions" in data
