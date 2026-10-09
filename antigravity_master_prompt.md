# MASTER PROMPT: Fix and Complete the CL-RAG Platform

Paste everything below the line into the agent. If the agent struggles with the length, give it the "Operating Rules" and "Verified Defects" sections first, then feed one Phase at a time.

---

## ROLE

You are a senior full-stack and applied-NLP engineer working in the repository
`AI-Powered-Cross-Language-Knowledge-Transfer-Platform` (FastAPI + SQLite + vanilla JS frontend).
Your job is to fix every verified defect below, close the gaps between what the project claims and what it does, and leave it in a state where every number it reports is measured and reproducible.

## PROJECT IN ONE PARAGRAPH

The platform translates technical text (English to hi/ta/de/es) with a three-agent pipeline (Translator, Terminology-Verifier, Domain-Critic). It keeps a versioned terminology store (the "Living Terminology KG") that is updated from human reviewer corrections, and routes low-confidence segments to a human review queue. It also offers expertise-adaptive summaries and a cross-lingual Q&A over uploaded documents (CL-RAG). The research claim is narrow: a self-updating terminology store plus confidence-gated review lets the system expand into a new target language without a pre-built, human-curated termbase, and reduces review volume as the store converges.

## OPERATING RULES (NON-NEGOTIABLE)

1. **No fabricated or hardcoded metrics, ever.** Any number shown in the API, UI, README, docs, or paper must come from a stored evaluation run (raw outputs saved to `data/evaluation/runs/`). Constants such as `0.96`, `42.5`, `88.0`, baseline rows like `28.5/64.2/58.0`, and flags like `verified_without_fabrication: True` must be deleted.
2. **Report results honestly.** If the proposed system loses to a baseline, report that. Never tune evaluation code until it "looks good". Real curves can be flat or non-monotonic.
3. **Offline/deterministic mode is a demo fallback, not evidence.** Every API response and UI view must say which mode produced the output. Any evaluation run in offline mode must be labeled `OFFLINE_NOT_EVIDENCE` in its saved output and refused by the report generator for headline claims.
4. **If you cannot run something** (no API key, no GPU, model download blocked), say so explicitly in your report and mark the related results as NOT RUN. Never simulate results.
5. **Test-first for each defect.** Write a failing test that reproduces the defect, then fix it. Do not weaken or delete a test to make it pass.
6. **Work in phases on a branch** (`fix/full-remediation`). One conventional commit per logical change. After each phase run the full test suite and post a short status: what changed, what passes, what is still open.
7. **Ask before guessing** on anything that changes the research claim. Defaults for common decisions are given in "Default Decisions" below.

## VERIFIED DEFECTS (reproduce each with a test before fixing)

| # | Defect | How it was reproduced |
|---|---|---|
| D1 | Clean install fails | `requirements.txt` lacks `email-validator`; `auth.py` uses `EmailStr` so import fails |
| D2 | Clean boot creates 3 users but 0 knowledge spaces and 0 documents | `database.init_db()` seeds the admin before the `main.py` lifespan seed runs; the lifespan seed sees admin exists and skips workspace + sample doc |
| D3 | `POST /api/chat` with an unknown `space_id` returns HTTP 500 | Foreign-key `IntegrityError` in `rag_service._save_and_package_message`; should be 404 |
| D4 | "Cross-lingual retrieval" is a 54-entry hand-written dictionary (`bilingual_bridge` in `rag_service.py`) | Same meaning scores 0.34 with dictionary words and 0.0 without; Hindi, Tamil, German queries return "not found" for the demo doc |
| D5 | Eval comparison table is fabricated | Baseline rows in `eval_service.py` are typed constants; `verified_without_fabrication: True` is a literal; rounds 2 and 3 are identical; proposed system computed at 31.6% sits below the made-up 64.2% baseline |
| D6 | A reviewer can approve any translation, and the gate cannot catch it | Approving the Hindi term "POISONED" for "fault tolerance" was accepted (confidence 0.95) and later used at 0.975 confidence with nothing queued |
| D7 | Read and run endpoints need no token | `/api/stats`, `/api/documents/spaces`, `/api/kg/terms`, `POST /api/eval/run` all return 200 unauthenticated |
| D8 | Frontend hard-codes the reviewer password and auto-logs in (`ensureAuthenticated` in `app.js`); there is no login form | Every UI write runs as REVIEWER; the role model is bypassed |
| D9 | Adaptive output invents specifications | One-sentence ventilator input returns "expert" text with p99, RPO, RTO figures that are not in the source; scores are constants |
| D10 | Tests do not test production code | `test_regex_safety` tests a lambda defined inside the test; multilingual test passes only because queries contain dictionary words; eval test checks its own output |
| D11 | Silent fallback hides live-mode failures | `except Exception: pass` in translator, critic, adaptive, RAG; no per-segment record of live vs fallback; model ID and API-key-in-URL hardcoded |
| D12 | The "knowledge graph" is a flat termbase | Only domain-to-term and term-to-translation edges, and those are synthesized at export time |
| D13 | Term discovery cannot find unseen terms | `find_uncovered_terms` only detects terms already present in the table; extraction is acronym-only (ALL-CAPS 3 to 6 letters copied as their own translation) |
| D14 | Domain handling is a hack | `(domain = ? OR domain = 'cloud_computing')` hardcoded in lookups; `UNIQUE(source_term, domain)`; same term in two domains yields conflicting constraints |
| D15 | Review queue stores one term per segment; duplicates on re-translation; corrections do not re-translate past output | `constraints[0]` only; no dedupe; items marked RESOLVED without regenerating the segment |
| D16 | Confidence is called "calibrated" but the weights (0.50/0.35/0.15) and threshold (0.85) are hand-picked and never validated | No labeled data, no reliability curve |
| D17 | Translation is English to X only | Prompts hardcode `Source (EN)` |
| D18 | Unsupported upload formats become garbage | PDFs/DOCX decoded as UTF-8/latin-1; no parsing, size or type limits |

## PHASES

### Phase 1: Boot, install, seed, errors (D1, D2, D3)
- Add `email-validator` and every other missing runtime dependency to `requirements.txt` (pinned). Verify with a fresh virtualenv: `pip install -r requirements.txt && pytest`.
- Create **one** idempotent seed routine called from one place. It creates the demo accounts only when `ENVIRONMENT=development`, the default workspace, and the sample document, each independently idempotent (check each, do not gate all on admin existing).
- Chat, adaptive, review, and documents endpoints must return 404 for unknown ids and 422 for invalid input. No 500 for foreign-key violations; validate existence first.
- Add `Dockerfile`, `docker-compose.yml`, `.env.example` (complete), and `.github/workflows/ci.yml` (install, lint, test on push).
- **Acceptance:** fresh clone, empty DB, `uvicorn` starts, `/api/documents/spaces` shows 1 space with 1 document, chat to unknown space returns 404.

### Phase 2: Security and tenancy (D7, D8)
- Remove all hardcoded credentials from the frontend. Add a real login screen, logout, token expiry handling, and role-aware UI (USER, REVIEWER, ADMIN).
- Require authentication on every route except `GET /api/health` and `POST /api/auth/login|register`. Eval run endpoints require ADMIN.
- Add `tenant_id` (organization) to users, knowledge_spaces, terms, review_queue, and document tables; scope every query by tenant. A user must never see another tenant's spaces, documents, terms, or reviews.
- Startup must refuse to run outside development if `JWT_SECRET` is the default or shorter than 32 chars. Restrict CORS to configured origins (no `*` with credentials). Add per-IP and per-user rate limits, request body size caps, and text length caps on all LLM-backed routes.
- File uploads: allow-list extensions (`pdf, docx, pptx, txt, md`), size cap, content sniffing, safe filenames.
- **Acceptance:** an automated test that every route's unauthenticated response is 401 except the allow-list; a cross-tenant test that returns 404 or empty for foreign ids.

### Phase 3: Terminology store integrity and review workflow (D6, D12 to D15)
- **Validation of proposed translations:** reject empty, over-length, control characters, regex/template metacharacters used as syntax, text containing instruction-like patterns, a translation in the wrong script for the target language (Unicode block check; allow Latin acronyms/loanwords). Return 422 with a reason.
- **Proposal and approval workflow:** a correction creates a `PROPOSED` version. It becomes `APPROVED` only after N distinct reviewers approve (default N = 2, configurable; the proposer cannot approve their own). Store reviewer id and role in `term_audit_log`. Confidence is derived from approvals and agreement, not forced to 1.0.
- **Real graph:** add `term_relations(source_term_id, target_term_id, relation)` with relations such as `synonym`, `broader`, `narrower`, `related`, `abbreviation_of`. Use relations in lookup (abbreviations resolve to their full term) and expose them in the graph export.
- **Matching:** replace per-segment regex table scans with an in-memory automaton (Aho-Corasick or trie), longest-match-first, case-insensitive, with English plural/lemma normalization. Cache with invalidation on every approved change. No hardcoded `cloud_computing` fallback domain; use explicit domain lists and a documented cross-domain resolution rule (domain-specific beats general; conflicts are flagged, never silently resolved).
- **Term discovery:** implement real candidate extraction (noun-phrase chunking plus C-value or TF-IDF against a reference corpus; optional LLM-assisted extraction behind a flag). Terms not in the store must be flagged as `UNKNOWN_TERM` so that a fully unseen term reaches human review. Keep acronym extraction but do not copy acronyms as translations automatically; propose them as candidates.
- **Review queue:** add a child table so a segment can reference many terms; dedupe identical pending items; when a correction is approved, re-run the affected segments and update stored translation output (add `translation_jobs` and `translation_segments` tables so past documents can be refreshed).
- Add rollback (ADMIN), history endpoint, and import/export of the termbase as CSV and TBX.
- **Acceptance:** the "POISONED" test: a single reviewer's proposal is not used in translation; a second reviewer's approval of a wrong-script term is rejected by validation; a fully unseen multi-word term is queued as `UNKNOWN_TERM`.

### Phase 4: Multi-agent pipeline (D11, D16, D17)
- Introduce an `LLMClient` abstraction with `mode = live | offline | auto`. In `live`, errors raise and are surfaced as 502 with details; no silent fallback. In `auto`, fallback is allowed but every segment records `engine: "live:<model>" | "offline_demo"` and the response carries a top-level `mode` field. Model ID comes from `GEMINI_MODEL` (check current model names in the provider's documentation; do not assume), API key goes in the request header, not the URL.
- Retries with exponential backoff, timeouts, and bounded concurrency (`asyncio.gather` with a semaphore). Segments may be processed in parallel.
- Validate critic output with a strict schema (Pydantic): score in [0,1], notes string; invalid output counts as a failure with a logged reason.
- Prompt-injection hardening: wrap source text and retrieved context in clearly delimited data blocks, instruct the model to treat them as data, and strip or escape delimiter lookalikes.
- Verifier: token-boundary and morphology-aware matching, plus a check that the English source term does not remain untranslated in the output.
- **Confidence calibration, done for real:** build a labeled set from reviewer decisions (and the evaluation gold data), fit the combination weights (logistic regression) and pick the threshold from a target error-recall. Report reliability curve and expected calibration error. If calibration data is insufficient, rename the score "weighted confidence" everywhere and say so; do not call it calibrated.
- Add `source_lang` to the API (language detection with a standard library if omitted). Support at least en to hi/ta/de/es and one non-English source pair, for example de to en.
- **Acceptance:** with a mocked failing provider in `live` mode the API returns 502, not a fake translation; per-segment `engine` is present in every response.

### Phase 5: Cross-lingual retrieval (D4, D18)
- Replace the bilingual dictionary with multilingual embeddings: default `intfloat/multilingual-e5-base` via `sentence-transformers` (CPU-friendly; allow BGE-M3 via config). Store vectors as float32 BLOBs; use an ANN index or `sqlite-vec` when available, with brute-force fallback. Use hybrid retrieval (BM25 plus dense, reciprocal rank fusion).
- **KG-bridged query expansion (the genuinely new part):** detect target-language terms in the query using the terminology store, map them to their English source terms, and add them to the query. Evaluate it with an ablation (with vs without).
- Parse PDF, DOCX, PPTX (PyMuPDF, python-docx, python-pptx) preserving page or slide numbers; citations must include page numbers and the exact supporting span, not the first 160 characters of a chunk.
- Answer generation: include conversation history; add a support check (LLM judge or NLI) and abstain with a clear message when the answer is not supported by retrieved text. Confidence shown to the user = function of retrieval score and support score; delete the constant 0.96.
- Delete `bilingual_bridge`, or keep it only as an explicitly labeled optional fallback that is never used in evaluation.
- Build a retrieval benchmark of at least 100 queries (hi, ta, de, es, plus English) over English documents, where queries are paraphrases that share no tokens with a dictionary. Report Recall@1/5 and MRR.
- **Acceptance:** "दोष सहनशीलता क्या है?" retrieves the fault-tolerance chunk; the old dictionary-dependent test is replaced by one that fails on the old implementation.

### Phase 6: Expertise-adaptive summarization (D9)
- Delete all canned offline templates that ignore the input. Offline mode may return a clearly labeled extractive summary of the actual input only.
- Route output through the terminology constraints and verifier; enforce that approved target terms appear.
- Add a faithfulness guard: flag any number, unit, or named entity in the output that does not appear in the source or approved terminology; block or mark such output.
- Compute readability: Flesch-Kincaid (or equivalent) for English; for other languages use a documented proxy (mean sentence length, mean word length) and label it as a proxy. Remove constants `42.5`, `88.0`, and `adaptation_appropriateness_score`; replace with a computed LLM-judge rubric score from a separate model call, or `null` when not computed.
- Support three levels (novice, intermediate, expert) and a domain-neutral expert prompt (no SLA/latency boilerplate).
- **Acceptance:** the ventilator input yields no p99/RPO/RTO text; scores are `null` or computed, never constant.

### Phase 7: Real evaluation (D5, plus everything that feeds the paper)
- Delete all hardcoded baselines and flags. Implement real conditions, each run on an isolated temporary copy of the database:
  - **B1 Generic MT:** translator with zero constraints.
  - **B2 Static glossary (AIDA_term-inspired, never labeled "AIDA_term"):** full termbase supplied up front, no self-update.
  - **P Proposed:** self-updating store with gating and uncovered/unknown-term detection.
  - **Ablations:** no unknown-term detection; no gating (review everything); no self-update; batch instead of per-segment processing.
- Data: expand `data/evaluation/` to at least 300 terms and 200 sentences, at least 2 domains and at least 2 target languages (hi plus one of ta/de/es), with reference translations. Record who validated the gold data and how; unvalidated items are flagged and excluded from headline results.
- Make correction rounds meaningful: reviewers correct only the items routed to them in each round, with a simulated-reviewer error rate as a parameter; do not apply all gold corrections at once.
- Metrics: term success rate (exact and lemma-aware), chrF++ and BLEU via `sacrebleu`, optional COMET, review volume, gate precision and recall against truly wrong segments, AUROC of confidence for error detection, ECE. Use at least 3 seeds or bootstrap confidence intervals.
- Run in live mode with a real API key. Save raw segment-level outputs as JSONL under `data/evaluation/runs/<timestamp>/` with config, model ID, and per-segment engine.
- Provide a CLI (`python -m backend.evaluation.run --config configs/eval.yaml`) and a non-destructive API endpoint. Generate `docs/EVALUATION.md` and the README results table from saved runs only.
- If you cannot run live mode, produce the harness, run it offline, and label every output `OFFLINE_NOT_EVIDENCE`.

### Phase 8: Frontend (D8 plus UI correctness)
- Login/logout, role-aware navigation, token expiry, error and empty states.
- A persistent banner showing `mode` (live or offline demo) and engine per output.
- Eval Hub reads the real schema from Phase 7 and shows confidence intervals and per-baseline results; no placeholders.
- Review UI: multiple terms per item, approvals count (n of N), reviewer identity, validation errors from the API.
- Remove inline `onclick` string interpolation; use event listeners and `textContent`. Vendor Chart.js, Font Awesome, and fonts locally (or pin with SRI) so the demo works offline.

### Phase 9: Tests and CI (D10)
- Tests must call production code. Replace tautological tests. Add:
  - clean-DB boot and seed test;
  - auth matrix test for every route and role, plus cross-tenant tests;
  - KG poisoning, validation, and two-reviewer workflow tests;
  - regex-safety tests that call the real substitution function with hostile terms;
  - retrieval tests on the paraphrase benchmark (must fail against the old dictionary);
  - live-mode failure tests with mocked HTTP (`respx`): 502 surfaced, no silent fallback;
  - eval isolation test: snapshot the live KG, run an evaluation, assert the snapshot is unchanged;
  - adaptive faithfulness tests.
- CI runs lint (`ruff`), type checks (`mypy` on services), tests with coverage; require at least 80% coverage on `backend/services`.

### Phase 10: Documentation and paper alignment
- Rewrite `README.md`: remove every number not produced by a saved run; state limitations; document modes; include the claims-versus-evidence table below.
- Update `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/API_REFERENCE.md` to match the code.
- Update `paper.tex`: replace "cold start from zero" with the true scope (target-language expansion for terms already in the store, plus unknown-term detection after Phase 3); replace "calibrated" unless Phase 4 calibration succeeded; delete any "outperforms" claim; regenerate tables from saved runs. Keep the limitations section honest.
- Reconcile project identity: the Review-1 slides and `implementation_plan.md` promise multilingual-e5, pgvector, PDF/DOCX/PPTX, langdetect, bcrypt+JWT, and Docker. List which are now implemented and which are deliberately out of scope.

## DEFAULT DECISIONS (override only if I say otherwise)
- Embeddings: `intfloat/multilingual-e5-base`; BGE-M3 optional via config.
- All read endpoints require authentication except `/api/health`.
- LLM provider: Gemini, model from `GEMINI_MODEL`; code written behind an interface so another provider can be swapped in.
- Two-reviewer approval (N = 2).
- Database stays SQLite (WAL mode) with a documented path to PostgreSQL; do not migrate now.

## DELIVERABLES
1. Branch `fix/full-remediation` with one commit per logical change and a PR description.
2. `CHANGELOG.md` mapping every defect D1 to D18 to its fix commit and test.
3. Saved evaluation runs, `docs/EVALUATION.md`, and a regenerated README results table.
4. A final **claims-versus-evidence table**:

| Claim in README/paper | Evidence file | Status (MEASURED / NOT RUN / DROPPED) |
|---|---|---|

5. A short "what is still not done and why" list.

## DEFINITION OF DONE (verify with commands, not assertions)
- `pip install -r requirements.txt` in a clean venv, then `pytest` all green, coverage at least 80% on services.
- Clean DB boot: 1 workspace and 1 document exist; chat to an unknown space returns 404.
- `curl` of every route without a token returns 401 except health and login.
- Proposing "POISONED" as a Hindi term does not change any translation until two distinct reviewers approve, and is rejected by validation anyway.
- A paraphrased Hindi, Tamil, or German query with no dictionary overlap retrieves the right chunk; Recall@5 is reported from the benchmark.
- With a failing mocked provider in live mode the API returns 502.
- Searching the repo for `0.96`, `42.5`, `88.0`, `28.5`, `64.2`, `verified_without_fabrication` finds no hardcoded metric.
- The evaluation report was generated from files under `data/evaluation/runs/`, and every headline number in the README matches it.
