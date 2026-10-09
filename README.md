# AI-Powered Cross-Language Knowledge Transfer Platform (CL-RAG)
### Research-Grade Engineering Platform & IEEE Conference Implementation

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/pytest-52%20passed-success.svg)](file:///tests/)
[![Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen.svg)](file:///tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Core Research Problem**: Technical documentation in specialized domains (Cloud & Distributed Systems, Biomedical Devices) suffers from catastrophic terminology drift, semantic hallucination, and high post-editing costs when transferred across resource-diverse languages (English $\leftrightarrow$ Hindi, Tamil, German, Spanish).
> **Scientific Innovation**: Combines a **Living Terminology Knowledge Graph (T-KG)** with an **Agent Verification Pipeline**, **Two-Reviewer Consensus Gating ($N=2$)**, **Dense Multilingual Retrieval (`multilingual-e5-base`)**, and **Faithful Expertise-Adaptive Summarization**.

---

## 🔬 Core Architecture & Scientific Contributions

1. **Multi-Agent Translation & Verification Pipeline** ([multi_agent_service.py](file:///c:/Final%20Project/backend/services/multi_agent_service.py)):
   - **Translator Agent**: Injects per-segment terminology constraints from the Living KG with strict prompt injection sandboxing (`### BEGIN/END_SOURCE_DATA ###`).
   - **Verifier Agent**: Computes strict symbolic constraint satisfaction ($S_{\text{term}}$) across target scripts (Devanagari, Tamil, Latin).
   - **Critic Agent**: Audits semantic drift, register divergence, and syntax artifacts ($S_{\text{critic}}$) with Pydantic JSON schema validation.
   - **Confidence Gating Layer**: Computes $\mathcal{C} = 0.50 S_{\text{term}} + 0.35 S_{\text{critic}} + 0.15 S_{\text{prior}}$ to route low-confidence segments ($< \tau = 0.85$) to the Human Review Queue.
   - **Resilient LLMClient**: Header-based authentication, exponential backoff retries, and explicit HTTP 502 Bad Gateway error surfacing in live mode.

2. **Living Terminology Knowledge Graph (T-KG)** ([kg_service.py](file:///c:/Final%20Project/backend/services/kg_service.py)):
   - Aho-Corasick trie longest-match automaton preserving compound domain entities and plural normalization.
   - Linguistic candidate term discovery using POS chunking patterns and capitalized n-grams.
   - Multi-reviewer consensus gate requiring $N=2$ distinct authenticated reviewers to approve term candidates.
   - Anti-poisoning validation enforcing script consistency, length constraints, and prompt injection filtering.
   - Ontology relationships (`SYNONYM`, `ABBREVIATION_OF`, `PARENT_CONCEPT`) with BFS query expansion.

3. **Multilingual Dense Retrieval & Multi-Format Ingestion** ([rag_service.py](file:///c:/Final%20Project/backend/services/rag_service.py)):
   - Multilingual dense vector embeddings (`intfloat/multilingual-e5-base`) stored as float32 BLOB vectors with SQLite schema migrations.
   - Multi-format ingestion support for **PDF (`pymupdf`)**, **DOCX (`python-docx`)**, **PPTX (`python-pptx`)**, and **TXT** files preserving page provenance.
   - Grounded citations extracting exact supporting spans and dynamic match confidence scores.

4. **Faithful Expertise-Adaptive Summarization** ([adaptive_service.py](file:///c:/Final%20Project/backend/services/adaptive_service.py)):
   - Three cognitive tiers: **Novice** (plain explanations and analogies), **Intermediate** (technical summary), and **Expert** (rigorous specifications).
   - **Faithfulness Guard**: Detects and flags hallucinated numbers, units, and invented SLA parameters (`p99`, `<50ms`, `RPO/RTO`).
   - Dynamically calculated readability scores: Flesch-Kincaid Grade Level and Reading Ease for English; documented lexical proxies (mean sentence/word length) for non-English scripts. Zero hardcoded constants.

5. **Empirical Evaluation Harness** ([eval_service.py](file:///c:/Final%20Project/backend/services/eval_service.py)):
   - Non-destructive execution on temporary database clones (`eval_iso_<uuid>.db`).
   - Four-way comparative protocol: B1 (Generic MT), B2 (Static Glossary), P (Proposed Pipeline), and Ablation (w/o unknown gating).
   - Real metric calculation via `sacrebleu` (BLEU, chrF++), `scikit-learn` (AUROC), and Expected Calibration Error (ECE).
   - Raw segment outputs saved to `data/evaluation/runs/`. Zero hardcoded metrics.

---

## 📊 Empirical Evaluation Results (Saved Reproducible Runs)

*Evaluated on standardized gold benchmark corpora under `data/evaluation/` (Cloud & Distributed Systems and Biomedical Devices in Hindi `hi`).*

### Cloud & Distributed Systems Architecture (`cloud_computing`, Hindi `hi`)
*Source artifact: `data/evaluation/runs/latest_cloud_hi.json` (Run ID: `8cf56b51-7eac-488a-8994-9100be86c524`)*

| Condition | TSR (%) | BLEU | chrF++ | AUROC | ECE | Review Vol % | Latency (p50 / p95) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B1: Generic MT (Zero Constraints)** | 0.00% | 0.39 | 2.06 | 0.500 | 0.500 | 0.0% | 0.000s / 0.000s |
| **B2: Static Bilingual Glossary** | 75.00% | 3.81 | 16.65 | 0.500 | 0.250 | 0.0% | 0.000s / 0.000s |
| **P: Proposed CL-RAG Pipeline** | 70.00% | 17.06 | 26.93 | 0.750 | 0.370 | 0.0% | 0.000s / 0.000s |
| **Ablation: Pipeline w/o Unknown Gating** | 70.00% | 17.06 | 26.93 | 0.750 | 0.370 | 0.0% | 0.000s / 0.000s |

### Biomedical Devices & Clinical Engineering (`biomedical_devices`, Hindi `hi`)
*Source artifact: `data/evaluation/runs/latest_biomedical_hi.json` (Run ID: `a4c4bc0c-7f03-4dfd-948e-3c4da0da9e85`)*

| Condition | TSR (%) | BLEU | chrF++ | AUROC | ECE | Review Vol % | Latency (p50 / p95) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B1: Generic MT (Zero Constraints)** | 0.00% | 0.35 | 2.04 | 0.500 | 0.500 | 0.0% | 0.000s / 0.000s |
| **B2: Static Bilingual Glossary** | 45.00% | 3.64 | 10.85 | 0.500 | 0.350 | 0.0% | 0.000s / 0.000s |
| **P: Proposed CL-RAG Pipeline** | 55.00% | 13.59 | 19.80 | 0.900 | 0.465 | 0.0% | 0.000s / 0.000s |
| **Ablation: Pipeline w/o Unknown Gating** | 55.00% | 13.59 | 19.80 | 0.900 | 0.465 | 0.0% | 0.000s / 0.000s |

---

## 📋 Claims-versus-Evidence Matrix

| Claim in Proposal / Paper | Evidence File | Status | Notes |
|---|---|:---:|---|
| **Clean Boot & Idempotent Seeding** | `tests/test_phase1_boot.py` | **MEASURED** | Boot creates workspace and document; second boot is idempotent. |
| **Strict Authentication & Multi-Tenancy** | `tests/test_phase2_security_tenancy.py` | **MEASURED** | All read endpoints return 401 without token; tenant isolation verified. |
| **Anti-Poisoning & Script Validation** | `tests/test_phase3_terminology.py` | **MEASURED** | Malformed script and poisoned terms rejected by validation schema. |
| **Two-Reviewer Consensus Gate (N=2)** | `tests/test_phase3_terminology.py` | **MEASURED** | Term remains proposed after 1 reviewer; approved only upon distinct second reviewer. |
| **Longest-Match Trie & Plural Normalization** | `tests/test_phase3_terminology.py` | **MEASURED** | Compound phrases matched over substrings; plurals resolved to canonical lemma. |
| **Live Mode Failure Surfacing (HTTP 502)** | `tests/test_phase4_multi_agent.py` | **MEASURED** | Mocked failing provider returns 502; no silent fallback in live mode. |
| **Dense Cross-Lingual Paraphrase Retrieval** | `tests/test_phase5_retrieval.py` | **MEASURED** | Evaluated on 100-query benchmark (`retrieval_benchmark.json`) without dictionary overlap. |
| **Multi-Format Ingestion (PDF, DOCX, PPTX)** | `tests/test_phase5_retrieval.py` | **MEASURED** | Extracts text and preserves page numbers across PDF, DOCX, PPTX, TXT. |
| **Faithful Summarization (No Invented SLAs)** | `tests/test_phase6_adaptive.py` | **MEASURED** | Biomedical ventilator inputs verified to produce zero invented p99/SLA boilerplate. |
| **Non-Destructive Empirical Evaluation** | `tests/test_phase7_evaluation.py` | **MEASURED** | Evaluates B1, B2, P, Ablation on isolated temp DBs; outputs JSONL in `runs/`. |
| **Zero Fabricated Constants in Codebase** | `tests/test_phase7_evaluation.py` | **MEASURED** | Verified: `28.5`, `64.2`, `58.0`, `0.96`, `42.5`, `88.0` completely deleted. |
| **Frontend UI Correctness & Event Listeners** | `tests/test_phase8_frontend.py` | **MEASURED** | Zero inline `onclick` string interpolations; persistent operational mode banner. |
| **Service Test Coverage $\ge 80\%$** | `tests/` (pytest-cov) | **MEASURED** | Achieved **86%** overall coverage across `backend/services` (all files $\ge 83\%$). |
| **Cold Start from Absolute Zero (No Store)** | `docs/EVALUATION.md` | **DROPPED** | Replaced with true scope: target-language expansion for stored concepts + unknown term gating. |
| **PostgreSQL pgvector in Production** | `docs/ARCHITECTURE.md` | **NOT RUN** | Platform runs SQLite WAL mode with float32 BLOBs; PostgreSQL migration path documented. |

---

## 📁 Repository Structure

```
c:\Final Project\
├── backend/
│   ├── config.py                 # System config, dynamic test DB routing, JWT secret validation
│   ├── database.py               # SQLite WAL mode schema, seed accounts, column migrations
│   ├── main.py                   # FastAPI app, lifespan initialization, CORS, static mounting
│   ├── evaluation/
│   │   └── run.py                # CLI evaluation runner
│   ├── services/
│   │   ├── auth_service.py       # Native bcrypt hashing, JWT access token generation & RBAC
│   │   ├── kg_service.py         # Living KG, C-Value discovery, 2-reviewer consensus, trie automaton
│   │   ├── multi_agent_service.py# LLMClient, 3-agent pipeline, injection delimitation, gating
│   │   ├── rag_service.py        # Dense cross-lingual retrieval, e5-base, multi-format parser
│   │   ├── adaptive_service.py   # Novice/Intermediate/Expert adaptation, faithfulness guard
│   │   └── eval_service.py       # Empirical benchmark runner, sacrebleu, sklearn, JSONL outputs
│   └── routers/                  # Modular FastAPI routers (/api/auth, /api/kg, /api/eval, etc.)
├── data/
│   └── evaluation/
│       ├── benchmark_cloud_computing.json # 100 sentences, 155 domain terms in cloud architecture
│       ├── benchmark_biomedical.json      # 100 sentences, 155 domain terms in biomedical devices
│       ├── retrieval_benchmark.json       # 100 cross-lingual paraphrase retrieval queries
│       └── runs/                          # Empirical benchmark artifacts (.jsonl and metadata)
├── docs/
│   ├── ARCHITECTURE.md           # Detailed architectural and graph specification
│   ├── SECURITY.md               # RBAC matrix, anti-poisoning controls, input defenses
│   ├── EVALUATION.md             # Benchmark methodology and empirical results
│   ├── API_REFERENCE.md          # REST API endpoints and schemas
│   └── PROJECT_AUDIT.md          # Comprehensive repository audit and gap analysis
├── frontend/                     # Modern dark glassmorphic single-page web app
├── tests/                        # 52 automated tests covering D1–D18 with 86% service coverage
├── CHANGELOG.md                  # Comprehensive remediation log mapping D1–D18 to commits
├── paper.tex                     # Complete IEEE conference LaTeX research paper
├── requirements.txt              # Pinned, tested dependencies
└── .env.example                  # Environment configuration template
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Git

### 2. Environment Setup
```powershell
# Copy environment configuration
Copy-Item .env.example .env

# Install pinned dependencies
pip install -r requirements.txt
```

### 3. Run the Automated Test Suite & Coverage
```powershell
# Run full regression suite (52 tests)
pytest tests/ -v

# Run with statement coverage on backend services (requires >= 80%)
pytest --cov=backend/services tests/
```

### 4. Run the Empirical Evaluation Benchmark
```powershell
# Run comparative benchmark across B1, B2, P on Cloud Computing domain
python -m backend.evaluation.run --domain cloud_computing --lang hi

# Run comparative benchmark on Biomedical Devices domain
python -m backend.evaluation.run --domain biomedical_devices --lang hi
```

### 5. Launch the Web Application
```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Default development credentials:
- **Admin**: `admin@clrag.org` / `AdminPassword123!`
- **Reviewer**: `reviewer@clrag.org` / `ReviewerPassword123!`
- **Student User**: `user@clrag.org` / `UserPassword123!`

---

## 🔍 What Is Deliberately Out of Scope & Limitations

1. **PostgreSQL / pgvector Migration**:
   - The platform operates on SQLite WAL mode with binary float32 BLOB embedding storage and indexed cosine similarity computation. While a PostgreSQL pgvector schema is documented in `docs/ARCHITECTURE.md`, migrating the active local database to a remote PostgreSQL instance was kept out of scope to preserve zero-configuration reproducibility for evaluation.
2. **Grammatical Agreement for Indic Verb Conjugation**:
   - While symbolic terminology injection guarantees exact technical terms, morpho-syntactic postposition and gender agreement in Hindi and Tamil require the neural generation layer in live LLM mode. In offline demonstration mode, terms are rendered in their canonical glossary forms.
3. **Phonetic Readability Formulas for Non-Latin Scripts**:
   - Flesch-Kincaid is phonologically calibrated for English syllable counts. Non-English adaptations (`hi`, `ta`) compute lexical proxies (mean word and sentence lengths) rather than attempting to force English syllable assumptions on agglutinative or syllabic alphabets.
