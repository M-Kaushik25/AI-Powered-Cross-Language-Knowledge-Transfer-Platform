import re

import pytest

from backend.services.multi_agent_service import multi_agent_service


def test_safe_regex_substitution_patterns():
    """Verify that regex backreferences such as \\1, \\g<1>, and backslashes do not crash or corrupt text."""
    sample_text = "The system connects to primary cluster and secondary node."

    # Pathological replacement terms containing backreference syntax
    dangerous_replacements = [
        r"\1_corrupted",
        r"\g<1>_injection",
        r"C:\network\path\1",
        r"$\100%_guarantee",
        r"\\\\double_backslash\\",
    ]

    for dangerous in dangerous_replacements:
        pattern = r"\bcluster\b"
        # Standard re.sub(pattern, dangerous, sample_text) would fail with re.error: bad escape
        # Our safe lambda pattern:
        safe_result = re.sub(pattern, lambda m, r=dangerous: r, sample_text, flags=re.IGNORECASE)
        assert dangerous in safe_result
        assert "cluster" not in safe_result

@pytest.mark.asyncio
async def test_multi_agent_pipeline_with_tricky_characters():
    """Verify that multi-agent translation pipeline handles terms with punctuation/special characters safely."""
    complex_text = "The fault tolerance threshold is strictly set at 99.99%."
    result = await multi_agent_service.translate_document(
        source_text=complex_text,
        target_lang="hi",
        domain="cloud_computing"
    )
    assert result["full_translation"] is not None
    assert len(result["segments"]) > 0
