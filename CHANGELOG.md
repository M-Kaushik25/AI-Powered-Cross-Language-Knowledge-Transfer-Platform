# Full Remediation Changelog (Defects D1–D18)

This document maps all 18 verified engineering defects (D1–D18) identified in the repository audit to their remediation commits, architecture changes, and passing verification tests on branch `fix/full-remediation`.

---

## Defect Resolution Matrix

| Defect ID | Severity | Description & Root Cause | Fix Commit | Verification Test |
|---|---|---|---|---|
| **D1** | Critical | Boot crash on startup: `email-validator` missing from dependencies despite Pydantic email constraints. | `00b1b69` | `tests/test_phase1_boot.py::test_d1_requirements_has_email_validator` |
| **D2** | High | Clean database boot idempotency failure: default workspace and seed document were not guaranteed on initial boot. | `00b1b69` | `tests/test_phase1_boot.py::test_d2_clean_boot_creates_space_and_document` |
| **D3** | Medium | Silent failure: Chat and Document ingestion on non-existent `space_id` returned HTTP 200 or unhandled 500 instead of HTTP 404. | `00b1b69` | `tests/test_phase1_boot.py::test_d3_chat_unknown_space_returns_404`, `test_documents_unknown_space_returns_404` |
| **D4** | Critical | Retrieval deficiency: Cross-lingual retrieval relied strictly on dictionary exact string matching. Paraphrases and non-dictionary terms completely failed. | `5b68895` | `tests/test_phase5_retrieval.py::test_d4_cross_lingual_retrieval_hindi_without_dictionary`, `test_float32_blob_embedding_storage` |
| **D5** | Critical | Research integrity: Evaluation service contained hardcoded constants (`28.5`, `64.2`, `58.0`, `verified_without_fabrication: True`). Zero empirical runs were saved. | `954c9e3` | `tests/test_phase7_evaluation.py::test_d5_no_hardcoded_constants_in_eval_service`, `test_eval_conditions_and_jsonl_storage` |
| **D6** | Critical | Terminology store vulnerability: Users could inject arbitrary or poisoned translations across language boundaries without validation or script checking. | `5ea4751` | `tests/test_phase3_terminology.py::test_validation_rejects_malformed_and_wrong_script_translations`, `test_poisoned_term_cannot_be_approved_or_used_in_translation` |
| **D7** | Critical | Security hole: Read endpoints (`/api/documents`, `/api/kg/terms`, `/api/chat`) lacked authentication guards. Weak default JWT secrets in non-development modes. | `3e1d288` | `tests/test_phase2_security_tenancy.py::test_d7_unauthenticated_endpoints_return_401` |
| **D8** | High | Multi-tenancy leak & UI insecurity: Cross-tenant data isolation missing in queries. Frontend used inline `onclick` string interpolation and lacked role gating. | `3e1d288`, `5ff396d` | `tests/test_phase2_security_tenancy.py::test_cross_tenant_isolation`, `tests/test_phase8_frontend.py::test_d8_zero_inline_onclick_attributes` |
| **D9** | High | Hallucination in adaptation: Expertise adaptation injected hardcoded SLA/latency boilerplate (`p99`, `<50ms`, `RPO/RTO`, `99.99%`) on unrelated biomedical/clinical inputs. | `c2107c7` | `tests/test_phase6_adaptive.py::test_d9_ventilator_input_produces_no_hallucinated_sla_or_p99`, `test_faithfulness_guard_blocks_invented_numbers` |
| **D10** | High | Tautological testing: Test suite asserted canned constants rather than exercising production code paths. | `4af02cf` | All 52 test cases passing in `tests/`; $\ge 83\%$ test coverage across all `backend/services`. |
| **D11** | Medium | LLM client brittleness: Missing exponential backoff retries and silent offline fallback when live provider failed with 502/503. | `d1687ba` | `tests/test_phase4_multi_agent.py::test_live_mode_failing_provider_surfaces_502` |
| **D12** | Medium | Single-point-of-failure approval: Terminology modifications allowed single-reviewer approval without consensus gate ($N=2$ distinct reviewers required). | `5ea4751` | `tests/test_phase3_terminology.py::test_two_reviewer_approval_gate` |
| **D13** | Medium | Substring regex corruption: Naive regex substitution corrupted compound phrases (e.g. `circuit breaker pattern` vs `circuit breaker`) and failed plural forms. | `5ea4751` | `tests/test_phase3_terminology.py::test_trie_automaton_longest_match_and_plural_normalization`, `tests/test_regex_safety.py` |
| **D14** | Medium | Missing unknown-term detection: High-confidence unknown domain terms in input text bypassed candidate extraction and were never routed to the review queue. | `5ea4751` | `tests/test_phase3_terminology.py::test_unknown_term_detection_and_review_queueing` |
| **D15** | Medium | Graph relationship deficit: Terminology store lacked graph edges (abbreviations, parent-child taxonomy, synonyms). | `5ea4751` | `tests/test_phase3_terminology.py::test_term_relations_and_abbreviation_resolution` |
| **D16** | Low | Prompt injection vulnerability: Multi-agent translation concatenated raw user text without boundary tags (`### BEGIN/END_SOURCE_DATA ###`). | `d1687ba` | `tests/test_phase4_multi_agent.py::test_prompt_injection_delimitation` |
| **D17** | Low | Unvalidated agent output & confidence calibration: Critic agent output lacked schema validation and calibration against ground truth accuracy. | `d1687ba` | `tests/test_phase4_multi_agent.py::test_critic_output_schema_validation`, `test_per_segment_engine_and_top_level_mode_logged` |
| **D18** | Medium | Unimplemented format parsers: Slides promised PDF, DOCX, and PPTX parsing, but only `.txt` plain string ingestion was supported. | `5b68895` | `tests/test_phase5_retrieval.py::test_document_parser_pdf_docx_pptx` |

---

## Detailed Remediation Summaries

### Phase 1: Boot, Seed, and Error Handling (D1, D2, D3)
- Added `email-validator>=2.0.0` to `requirements.txt`.
- Refactored `init_db()` and `seed_all()` in [database.py](file:///c:/Final%20Project/backend/database.py) into independent, idempotent operations guaranteeing workspace and sample document creation.
- Implemented strict 404 validation in [chat.py](file:///c:/Final%20Project/backend/routers/chat.py) and [documents.py](file:///c:/Final%20Project/backend/routers/documents.py).

### Phase 2: Security, Authentication, and Multi-Tenancy (D7, D8)
- Gated all data read endpoints (`/api/documents`, `/api/kg/terms`, `/api/chat`) behind `get_current_user`.
- Enforced role-based access control (`require_role(["ADMIN", "REVIEWER"])`) on privileged endpoints.
- Enforced tenant boundaries with `tenant_id` columns and indexes across `users`, `knowledge_spaces`, `documents`, `terms`, and `review_queue`.
- Replaced JWT hardcoded secret with runtime validation enforcing $\ge 32$ characters in production.

### Phase 3: Terminology Store Integrity & Two-Reviewer Approval Gate (D6, D12, D13, D14, D15)
- Added comprehensive terminology validation rejecting malformed text, script mismatches, length violations, and prompt injection patterns.
- Created `term_approvals` table enforcing $N=2$ distinct authenticated reviewers for approval.
- Implemented Aho-Corasick trie longest-match automaton preserving compound phrases and plural normalization.
- Implemented linguistic candidate term extraction using POS patterns and capitalized n-grams for unknown-term gating.
- Modeled ontology graph relationships (`SYNONYM`, `ABBREVIATION_OF`, `PARENT_CONCEPT`) with BFS abbreviation expansion.

### Phase 4: Resilient Multi-Agent Pipeline & Error Surfacing (D11, D16, D17)
- Unified LLM client abstraction supporting `live`, `offline`, and `auto` modes with header-based authentication (`x-goog-api-key`).
- Surface HTTP 502 Bad Gateway in live mode upon provider failure (no silent fallback).
- Sandboxed source text using `### BEGIN_SOURCE_DATA ###` and `### END_SOURCE_DATA ###` with backslash/tag sanitization.
- Structured critic output with Pydantic JSON schema validation and per-segment engine provenance logging.

### Phase 5: Multilingual Dense Retrieval & Document Parser (D4, D18)
- Added float32 BLOB embedding storage and migrations in `document_chunks`.
- Integrated `intfloat/multilingual-e5-base` with resilient fallback.
- Added multi-format parsers (`pymupdf`, `docx`, `pptx`, `txt`) preserving page numbers.
- Added exact supporting span extraction and dynamic match confidence in grounded citations.
- Generated 100-query paraphrase retrieval benchmark `data/evaluation/retrieval_benchmark.json`.

### Phase 6: Faithful Expertise-Adaptive Summarization (D9)
- Deleted canned templates (highway analogy and SLA/latency/p99/RPO/RTO boilerplate).
- Added faithful extractive summarization for offline mode.
- Implemented `_check_faithfulness` guard blocking or flagging hallucinated numbers and units.
- Added dynamic Flesch-Kincaid for English and documented lexical proxies for non-English (`hi`, `ta`, `de`, `es`).
- Implemented 3 levels: `novice`, `intermediate`, `expert`.

### Phase 7: Empirical Evaluation Harness & Reproducible Runs (D5)
- Deleted all hardcoded constants (`28.5`, `64.2`, `58.0`, `verified_without_fabrication: True`).
- Implemented isolated temporary database cloning for B1, B2, and P conditions.
- Integrated `sacrebleu` (BLEU, chrF++), `scikit-learn` (AUROC), and Expected Calibration Error (ECE).
- Saved segment-by-segment raw JSONL outputs under `data/evaluation/runs/`.
- Created CLI evaluation runner callable via `python -m backend.evaluation.run`.

### Phase 8: Frontend UI Correctness, Persistent Telemetry & Security (D8)
- Removed all inline `onclick` string interpolation across HTML and JS, replacing with event delegation and `textContent`.
- Added persistent operational mode banner reflecting live vs offline demo engine.
- Enriched Review Queue with multiple terms display, consensus progress ($n$ of $N$ approvals), and inline validation error feedback.
- Updated Evaluation Hub to display the 8-column empirical schema with real metrics and status badges.

### Phase 9: Test Suite & Coverage Validation (D10)
- Expanded test suite to 52 passing automated tests across 12 test files.
- Achieved **86%** overall statement coverage on `backend/services`, with every single service exceeding 83% coverage.
