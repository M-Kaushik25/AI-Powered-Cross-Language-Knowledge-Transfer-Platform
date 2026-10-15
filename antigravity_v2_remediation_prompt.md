# MASTER PROMPT V2: Fix All 7 Critical Architectural & Empirical Drawbacks

Paste everything below into the Antigravity agent. Work sequentially through Phases 1 to 7, running `pytest` after each phase.

---

## ROLE

You are a Staff Applied-NLP & Full-Stack Systems Engineer working in `AI-Powered-Cross-Language-Knowledge-Transfer-Platform` (FastAPI + SQLite WAL + Vanilla JS). A deep code audit of the repository revealed 7 critical drawbacks (C1–C7) that invalidate the multi-round evaluation curve, corrupt the Knowledge Graph during benchmark runs, break vector embeddings across process restarts, and leave hardcoded constants/URLs in the services. Your job is to remediate every defect below, verify with automated tests, regenerate the evaluation artifacts, and align `paper.tex` and `docs/EVALUATION.md`.

## OPERATING RULES (NON-NEGOTIABLE)

1. **Never slice a full sentence translation and store it as a single term's translation.**
2. **Never delete gold reference translations from the lookup dictionary used to score Term Success Rate (TSR).**
3. **Round 1, Round 2, and Round 3 in `eval_service.py` must reflect genuine, distinct states of Knowledge Graph evolution**, where Round 1 is Cold Start, Round 2 reflects partial/high-priority reviewer batch corrections, and Round 3 reflects second-wave reviewer corrections on remaining queued items.
4. **Zero hardcoded metric constants (`ece_estimate: 0.042`) or hardcoded model URLs (`gemini-1.5-flash`).** All services must use `LLMClient` and `GEMINI_MODEL` (`gemini-2.5-flash`).
5. **Deterministic hashing only.** Never use Python's salted built-in `hash()` for persisted vector blobs. Use `hashlib.blake2b`.
6. **Keep all existing 52 tests passing** while adding dedicated regression tests for C1–C7.

---

## VERIFIED CRITICAL DRAWBACKS TO FIX (C1–C7)

| ID | File(s) | Exact Bug / Drawback in Current Code |
|---|---|---|
| **C1** | `backend/services/eval_service.py` | (a) `_apply_human_corrections_to_queued` takes `gold_target = item.get("gold_translations", {}).get(target_lang)` (the full sentence!) and passes `corrected_translation=gold_target[:40]` as the single term's translation, polluting the KG with sentence prefixes. (b) `_simulate_cold_start` deletes `tr[target_lang]` from the `terms` table, and `_get_gold_term_translation` queries that same mutated `terms` table, returning `None` during Round 1 scoring. (c) In `_run_condition_proposed`, no correction step is called between Round 2 and Round 3 (`r2_queued` is ignored), making Round 2 and Round 3 identical. |
| **C2** | `backend/services/eval_service.py`, `backend/evaluation/run.py` | `_run_condition_b1`, `_run_condition_b2`, and `_eval_pipeline_round` hardcode `mode="offline"`. `_compute_metrics` does not compute `latency_p50` or `latency_p95`, causing `run.py` to print `0.000` for all latency columns. |
| **C3** | `data/evaluation/generate_gold_data.py`, `benchmark_*.json` | All 100 sentences in `benchmark_biomedical.json` and `benchmark_cloud_computing.json` use a single cloned sentence template ("During clinical life-support management, X maintains patient safety while continuous monitoring tracks Y"), inflating BLEU/chrF++ and detaching Tamil case suffixes (`" ஐ"`). |
| **C4** | `backend/services/rag_service.py` | `DenseMultilingualEmbedding._fallback_multilingual_vector` uses Python's built-in `hash(w)`, which is salted per process via `PYTHONHASHSEED`, making SQLite `embedding_blob` vectors invalid across restarts. Also lacks KG-bridged concept projection in fallback vectors. |
| **C5** | `backend/services/multi_agent_service.py`, `backend/services/kg_service.py`, `backend/routers/review.py` | (a) Line 365 of `multi_agent_service.py` still hardcodes `"ece_estimate": 0.042`. (b) `translation_segments.needs_refresh` is never updated when a term is corrected or approved in `kg_service.py`. (c) `POST /api/review/{item_id}/correct` bypasses 2-reviewer consensus without tracking approvals in `term_approvals`. |
| **C6** | `backend/services/multi_agent_service.py`, `backend/services/adaptive_service.py`, `backend/services/rag_service.py`, `backend/config.py` | (a) `_run_verifier_agent` uses exact substring matching, failing on Tamil agglutinative suffixes and Hindi oblique inflections. (b) `process_single_segment` has no 1-step self-correction loop when `verifier_res["violated"]` is non-empty. (c) `adaptive_service.py` and `rag_service.py` hardcode `gemini-1.5-flash` HTTP URLs instead of using `LLMClient` and `GEMINI_MODEL="gemini-2.5-flash"`. |
| **C7** | `backend/routers/auth.py` | `POST /api/auth/register` allows unauthenticated callers in non-development environments to self-assign `"role": "ADMIN"` or `"REVIEWER"`. |

---

## STEP-BY-STEP REMEDIATION PHASES

### Phase 1: Fix the Evaluation Engine, Gold Term Dictionary, Multi-Round Progression & Latency Telemetry (C1, C2)

Modify `backend/services/eval_service.py` and `backend/evaluation/run.py`:

1. **Snapshot Immutable Gold Term Dictionary Before Cold-Start:**
   - Add a method `_build_gold_term_map(self, items: list[dict[str, Any]], target_lang: str) -> dict[str, str]` in `EvaluationService`.
   - Before `_simulate_cold_start()` is ever called, populate `self._active_gold_terms` from:
     1. Each item's `"term_translations"` dictionary in the benchmark JSON (if present),
     2. `SEED_TERMS` in `backend.services.kg_service`, and
     3. The initial unmutated `terms` table in SQLite.
   - Update `_get_gold_term_translation(self, source_term: str, target_lang: str) -> str | None` to check `self._active_gold_terms.get(source_term.lower().strip())` first before querying the database. This guarantees that even when `_simulate_cold_start()` strips target translations from the DB table, TSR scoring always knows the true ground-truth term translation.

2. **Fix `_apply_human_corrections_to_queued` (Never Slice Sentence Prefix `gold_target[:40]`):**
   - Delete `gold_target = item.get("gold_translations", {}).get(target_lang)` and `corrected_translation=gold_target[:40]`.
   - Instead, look up the exact ground-truth term translation `gold_term = self._get_gold_term_translation(term, target_lang)`.
   - Only if `gold_term` is found, call `kg_service.apply_human_correction(source_term=term, target_lang=target_lang, corrected_translation=gold_term, domain=domain, reviewer_notes="Empirical benchmark review consensus")`.

3. **Make Rounds 1, 2, and 3 Realistically Distinct in `_run_condition_proposed`:**
   - **Round 1 (Cold Start):** Call `self._simulate_cold_start(items, target_lang)` to strip target-language translations from the cloned DB. Run `_eval_pipeline_round(..., "Round 1 (Cold Start)", mode=mode)`.
   - **Between Round 1 and Round 2 (Batch 1 High-Priority Review):** Collect all unique uncovered/flagged terms in `r1_queued` ordered by frequency descending. Have reviewers correct the **first 55% of unique queued terms** (representing the first shift/batch of human review bandwidth, with `reviewer_error_rate`). Invalidate the KG cache.
   - **Round 2 (Post-Batch-1 Evolution):** Run `_eval_pipeline_round(..., "Round 2 (Post-Correction)", mode=mode)`. Because the top 55% of terms are now in the KG, TSR will rise significantly (~50%–60%) and `r2_queued` will shrink.
   - **Between Round 2 and Round 3 (Batch 2 Residual Review):** Call `self._apply_human_corrections_to_queued(r2_queued, target_lang, domain, error_rate=reviewer_error_rate, max_fraction=1.0)` on the remaining queued items from Round 2! Invalidate the KG cache.
   - **Round 3 (Converged Living KG):** Run `_eval_pipeline_round(..., "Round 3 (Converged Living KG)", mode=mode)`. Now TSR reaches 85%–95%+ and Review Volume drops to the residual floor.

4. **Support `mode` Parameter and Measure Real `latency_p50` / `latency_p95`:**
   - Add `mode: str = "offline"` to `run_comparative_evaluation` and pass it down to `_run_condition_b1`, `_run_condition_b2`, `_run_condition_proposed`, and `_eval_pipeline_round`.
   - In `_run_condition_b1`, run `multi_agent_service._run_translator_agent(segment=src, constraints=[], source_lang="en", target_lang=target_lang, domain=domain, mode=mode)`.
   - In `_run_condition_b2`, run with static partial glossary (e.g., only seed terms present at $t=0$, no self-update).
   - Measure per-segment wall-clock time using `time.perf_counter()` across all conditions, and compute `"latency_p50": round(float(np.percentile(latencies, 50)), 4)` and `"latency_p95": round(float(np.percentile(latencies, 95)), 4)` inside `_compute_metrics()`.
   - Add `--mode` argument (`choices=["offline", "live", "auto"]`, default `"offline"`) to `backend/evaluation/run.py`.

---

### Phase 2: Indic Morphological Stem Matching, Agentic Self-Correction & Telemetry Cleanup (C5a, C6a, C6b)

Modify `backend/services/multi_agent_service.py`:

1. **Indic Morphological Stem & Prefix Normalization in `_run_verifier_agent`:**
   - Create helper `_match_term_in_target(required_term: str, draft_translation: str, target_lang: str) -> bool`:
     - Strip parenthetical glosses: `clean_term = re.sub(r'\(.*?\)', '', required_term).strip().lower()`.
     - Check exact substring match first (`required_term.lower() in draft_translation.lower()` or `clean_term in draft_translation.lower()`).
     - For Tamil (`ta`) and Hindi (`hi`), split `clean_term` into words. For each word $w$ of length $\ge 4$, strip common agglutinative/oblique suffixes (`["ஐ", "இல்", "ஆல்", "க்கு", "உடன்", "இன்", "கள்", "த்தினால்", "த்தை", "ओं", "यों", "ें"]`) or take its morphological stem prefix of length `max(3, int(len(w) * 0.75))`. If all content word stems of `clean_term` appear in `draft_translation.lower()`, return `True`.

2. **Bounded 1-Step Agentic Self-Correction Loop:**
   - In `process_single_segment()`, right after Step 3 (`_run_verifier_agent`), check if `verifier_res["violated"]` is non-empty and `constraints` is non-empty:
     - Construct a self-correction prompt specifying the violated constraints (`source_term -> target_term`) and asking the Translator Agent to revise `draft_translation` so every required target term is preserved.
     - If `segment_mode == "live"`, call `self.llm_client.generate_text(correction_prompt, mode=mode)`; if `segment_mode == "offline"`, re-apply `_deterministic_translate(segment, constraints, source_lang, target_lang)`.
     - Re-run `_run_verifier_agent` once on the revised draft and record `"self_correction_triggered": True` in `agent_2_terminology_controller`.

3. **Remove Hardcoded `ece_estimate: 0.042`:**
   - In `translate_document()`, delete the literal `"ece_estimate": 0.042` from `pipeline_telemetry`. Replace it with a dynamically computed confidence dispersion metric:
     `round(float(sum(abs(s["calibrated_confidence"] - (len(s["agent_2_terminology_controller"]["satisfied"]) / max(len(s["constraints_injected"]), 1))) for s in segment_results) / max(len(segment_results), 1)), 4)` (or `0.0` when no constraints are present).

---

### Phase 3: Diversify Benchmark Sentence Templates & Include Explicit Term Dictionaries (C3)

Modify `data/evaluation/generate_gold_data.py` and regenerate `benchmark_biomedical.json`, `benchmark_cloud_computing.json`, and `gold_corpus.json`:

1. **Replace the Single Cloned Sentence Template with 10 Distinct Syntactic Templates per Domain:**
   - In `generate_gold_data.py`, define at least 10 varied English sentence templates and matching Hindi (`hi`), Tamil (`ta`), German (`de`), and Spanish (`es`) templates for both `cloud_computing` and `biomedical_devices` (e.g., alarm thresholds, fault recovery, clinical SOP verification, telemetry monitoring, compliance auditing).
   - Ensure Tamil translations use natural suffixes/casings rather than a detached `" ஐ"` token.
   - In each item of `benchmark_biomedical.json` and `benchmark_cloud_computing.json`, include `"term_translations": {term_en: {"hi": ..., "ta": ..., "de": ..., "es": ...}}` so every benchmark item carries its exact per-term gold translations alongside the full sentence `gold_translations`.
   - Run `python data/evaluation/generate_gold_data.py` so the JSON files on disk are updated.

---

### Phase 4: Deterministic `blake2b` Embeddings & Unified `LLMClient` Across All Services (C4, C6c)

1. **Fix `DenseMultilingualEmbedding._fallback_multilingual_vector` in `backend/services/rag_service.py`:**
   - Import `hashlib`.
   - Create a deterministic helper:
     ```python
     def _det_hash(token: str, dim: int) -> int:
         digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
         return int.from_bytes(digest, "little") % dim
     ```
   - Replace every `abs(hash(...)) % self.dim` with `_det_hash(..., self.dim)`.
   - Inside `encode(self, text: str)`, before falling back to `_fallback_multilingual_vector`, also check if any known non-English KG terms appear in `text` and append their canonical English `source_term` tokens to the text being hashed so cross-lingual queries project into the same vector dimensions as English document chunks even when `sentence-transformers` is offline.

2. **Route `adaptive_service.py` and `rag_service.py` Through `LLMClient` & Update Default Model:**
   - In `backend/config.py` and `.env.example`, change the default `GEMINI_MODEL` from `"gemini-1.5-flash"` to `"gemini-2.5-flash"`.
   - In `backend/services/adaptive_service.py` and `backend/services/rag_service.py`, remove all hardcoded `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent` URLs and direct `httpx.AsyncClient` calls. Instead, use `multi_agent_service.llm_client.generate_text(prompt, mode=mode)`.

---

### Phase 5: Wire Up Historical Segment Refresh, Review Consensus & Auth Hardening (C5b, C5c, C7)

1. **Mark `translation_segments.needs_refresh = 1` on KG Updates (`backend/services/kg_service.py`):**
   - Inside both `approve_term()` and `apply_human_correction()`, whenever a term transitions to `'APPROVED'`, execute:
     ```python
     cursor.execute("""
         UPDATE translation_segments
         SET needs_refresh = 1, updated_at = ?
         WHERE lower(source_segment) LIKE ?
     """, (now, f"%{source_clean}%"))
     ```
   - Add a method `refresh_stale_segments(self, job_id: str | None = None)` in `multi_agent_service.py` and expose `POST /api/translate/jobs/{job_id}/refresh` in `backend/routers/translate.py` that re-translates segments where `needs_refresh = 1`, updates `target_segment`, and resets `needs_refresh = 0`.

2. **Enforce Role Security in `backend/routers/auth.py` (C7):**
   - In `POST /api/auth/register`, check `os.getenv("ENVIRONMENT", ENVIRONMENT)`: if the environment is not `"development"`, force `assigned_role = "USER"` regardless of what `req.role` was passed in the request body (preventing privilege escalation in production while keeping development/test fixtures working seamlessly).

---

### Phase 6: Add Regression Tests for C1–C7 & Regenerate Evaluation Artifacts

Add a new test file `tests/test_c1_c7_remediation.py` verifying:
1. `test_c1_eval_does_not_corrupt_kg_with_sentence_prefix`: Runs `eval_service.run_comparative_evaluation(sample_size=6)` and verifies that `Round 1 TSR < Round 2 TSR <= Round 3 TSR` and that corrected terms in the KG match true term translations, not 40-char sentence prefixes.
2. `test_c2_eval_metrics_include_latency_percentiles`: Asserts `latency_p50` and `latency_p95` are present in every condition's metrics dict.
3. `test_c3_benchmark_sentence_diversity`: Loads `benchmark_biomedical.json` and asserts there are at least 8 distinct sentence structures across the 100 items and that `"term_translations"` is present.
4. `test_c4_deterministic_blake2b_embeddings`: Verifies `DenseMultilingualEmbedding()._fallback_multilingual_vector("fault tolerance")` uses `blake2b` and produces identical float32 bytes independent of `PYTHONHASHSEED`.
5. `test_c5_segment_needs_refresh_flagged_on_kg_update`: Translates a segment, updates a term in `kg_service`, and asserts `needs_refresh == 1` in `translation_segments`.
6. `test_c6_indic_stem_verifier_and_no_hardcoded_ece`: Verifies Tamil inflected forms pass `_run_verifier_agent` and `0.042` does not appear in `backend/services/multi_agent_service.py`.
7. `test_c7_production_register_blocks_admin_escalation`: Sets `ENVIRONMENT=production` via monkeypatch and verifies `POST /api/auth/register` with `role="ADMIN"` assigns `role="USER"`.

Finally, run:
- `python data/evaluation/generate_gold_data.py`
- `python -m backend.evaluation.run --domain cloud_computing --lang hi --output data/evaluation/runs/latest_cloud_hi.json`
- `python -m backend.evaluation.run --domain biomedical_devices --lang hi --output data/evaluation/runs/latest_biomedical_hi.json`
- `python -m backend.evaluation.run --domain biomedical_devices --lang ta --output data/evaluation/runs/latest_biomedical_ta.json`
- Update `docs/EVALUATION.md`, `README.md`, and `paper.tex` tables with the newly measured numbers.

## DEFINITION OF DONE (Verify with Commands)
1. `ruff check backend/ tests/` passes with 0 errors.
2. `pytest -v --cov=backend/services tests/` passes 100% of tests (including `tests/test_c1_c7_remediation.py`) with $\ge 85\%$ coverage.
3. Searching `backend/` for `0.042`, `gemini-1.5-flash`, `gold_target[:40]`, or `abs(hash(` returns **zero matches**.
4. Running `python -m backend.evaluation.run --domain biomedical_devices --lang ta` shows a genuine monotonic improvement from Round 1 (Cold Start) $\rightarrow$ Round 2 $\rightarrow$ Round 3 with non-zero `p50` and `p95` latencies.