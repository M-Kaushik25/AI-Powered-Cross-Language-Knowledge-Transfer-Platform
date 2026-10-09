# System Architecture & Technical Specifications

## 1. High-Level Architecture Overview

The **AI-Powered Cross-Language Knowledge Transfer Platform (CL-RAG)** is an enterprise, research-grade platform designed to resolve cross-lingual terminology drift, catastrophic mistranslation, and domain conceptual fragmentation across resource-diverse languages (English, Hindi, Tamil, German, and Spanish).

```
                      +------------------------------------------+
                      |         Web Client (Vanilla JS)          |
                      |   Modern Glassmorphic Dark UI / Chart.js |
                      +--------------------+---------------------+
                                           | HTTPS / JSON (Bearer JWT, Role-Aware)
                      +--------------------v---------------------+
                      |           FastAPI Gateway Router         |
                      |   CORS / RBAC Security / Tenant Scoping  |
                      +--------------------+---------------------+
                                           |
         +---------------------------------+---------------------------------+
         |                                 |                                 |
+--------v--------+               +--------v--------+               +--------v--------+
| 3-Agent Pipeline|               |  Living KG      |               | Multilingual    |
| (Translator,    | <-----------> |  Ontology, Graph| <-----------> | Dense RAG & E5  |
|  Verifier,      |               |  2-Reviewer Gate|               | Parser (PDF/etc)|
|  Critic)        |               +--------+--------+               +-----------------+
+-----------------+                        |
                                  +--------v--------+
                                  | Human Review Hub|
                                  | & Provenance Log|
                                  +-----------------+
```

---

## 2. Core Subsystems

### 2.1 The Multi-Agent Translation & Verification Pipeline (`multi_agent_service.py`)

Execution is decomposed into specialized autonomous agents backed by an abstracted `LLMClient`:

1. **LLMClient Abstraction (`mode = live | offline | auto`)**:
   - In `live`: Provider errors (such as upstream HTTP failures) raise directly and surface as HTTP 502 with full diagnostic details. No silent fallback.
   - In `offline`: Uses deterministic rule-based and template fallbacks, clearly tagging each segment with `engine: "offline_demo"`.
   - In `auto`: Attempts live execution, falling back with explicit telemetry logging per segment.
   - Model name is configured via `GEMINI_MODEL`, and API authentication uses request headers rather than URL query parameters.

2. **Agent 1: Contextual Translator (`_run_translator_agent`)**:
   - Formulates target-language translations.
   - Injects constraint mappings from the Living Terminology Store.
   - Enforces prompt-injection hardening: untrusted source text is enclosed within strict data delimiters (`<source_text>` ... `</source_text>`) instructing the LLM to treat inputs strictly as passive data.

3. **Agent 2: Terminology Controller & Verifier (`_run_verifier_agent`)**:
   - Performs symbolic constraint satisfaction verification.
   - Checks token boundaries and morphological variations of approved terms.
   - Flags segments where the English source term was left untranslated.
   - Emits symbolic Term Satisfaction Rate ($S_{\text{term}} \in [0.0, 1.0]$).

4. **Agent 3: Domain & Quality Critic (`_run_critic_agent`)**:
   - Evaluates domain register, syntax distortion, punctuation parity, and output length divergence ($0.4 \le \text{ratio} \le 2.5$).
   - Returns a structured Pydantic-validated critique score ($S_{\text{critic}} \in [0.0, 1.0]$) and descriptive diagnostic notes.

5. **Confidence-Gated Human Router**:
   - Emits a weighted confidence score based on symbolic constraint satisfaction, critic evaluation, and term priors:
     $$\mathcal{C} = 0.50 \cdot S_{\text{term}} + 0.35 \cdot S_{\text{critic}} + 0.15 \cdot S_{\text{prior}}$$
   - If $\mathcal{C} \ge \tau$ (default $\tau = 0.85$), the segment is marked `AUTOMATICALLY_VERIFIED`.
   - If $\mathcal{C} < \tau$, the segment is routed to `review_queue` for expert human review.

---

### 2.2 Living Terminology Knowledge Graph (`kg_service.py`)

- **Terminology Validation & Script Integrity**:
   - Validates all proposed terms for length, empty strings, control characters, regex/prompt injection patterns, and script consistency.
   - Enforces Unicode block verification (e.g., Hindi translations must be in Devanagari; Tamil in Tamil script; Latin loanwords/acronyms permitted).
- **Two-Reviewer Consensus Gate ($N=2$)**:
   - Newly proposed or corrected terms enter `PROPOSED` status.
   - Requires approval by $N=2$ distinct reviewers. The original proposer cannot approve their own term.
   - Complete audit trail recorded in `term_audit_log` with user UUID, old/new translations, and timestamps.
- **Ontological Relationships (`term_relations`)**:
   - Explicit relational edges: `synonym`, `broader`, `narrower`, `related`, `abbreviation_of`.
   - Graph queries resolve abbreviations to their canonical terms and expose graph connectivity via `/api/kg/graph`.
- **In-Memory Trie & Aho-Corasick Matching**:
   - Longest-match-first matching with English plural and morphological normalization.
   - Thread-safe cache with automatic cache invalidation upon any approved term update.
- **Term Discovery & Candidate Extraction**:
   - Implements C-Value / noun-phrase chunking against reference corpora.
   - Uncataloged technical entities are flagged with `UNKNOWN_TERM` status and routed to human reviewers.

---

### 2.3 Cross-Lingual Semantic Retrieval & Grounding (`rag_service.py`)

- **Multilingual Dense Embeddings**:
   - Uses `intfloat/multilingual-e5-base` (or configurable BGE-M3) producing normalized dense vectors stored as raw float32 BLOBs in SQLite.
   - Cosine similarity computed via BLOB dot-product with fallback to in-memory vectorized search.
- **Hybrid Retrieval**:
   - Combines BM25 lexical keyword scoring with dense multilingual vector similarity using Reciprocal Rank Fusion (RRF).
- **KG-Bridged Query Expansion**:
   - Detects target-language terms in queries (Hindi, Tamil, German, Spanish), resolves them to English canonical source terms via the Terminology Store, and expands the search query.
- **Multi-Format Document Parsing**:
   - Preserves exact page and slide numbers:
     - PDF: PyMuPDF (`fitz`)
     - DOCX: `python-docx`
     - PPTX: `python-pptx`
     - Plaintext / Markdown: paragraph chunking
   - Citations return exact page/slide numbers and verbatim supporting text spans.
- **Faithfulness Verification & Abstention**:
   - Answers are checked against retrieved evidence using lexical/NLI support scoring.
   - The engine explicitly abstains when retrieved evidence is insufficient rather than hallucinating answers. Zero hardcoded confidence constants.

---

### 2.4 Expertise-Adaptive Summarization (`adaptive_service.py`)

Adapts complex technical documents into three cognitive levels:
- **Novice Adaptation**: Simplifies vocabulary, provides high-level context, and uses intuitive explanations.
- **Intermediate Adaptation**: Balances conceptual depth with standard technical vocabulary.
- **Expert Adaptation**: Uses domain-specific technical terminology, architectural trade-offs, and rigorous specifications derived strictly from source text.
- **Faithfulness Guard**:
   - Scans output for numerical values, units of measurement, or named entities. Flags or rejects outputs containing numbers not present in the source input.
- **Empirical Readability Metrics**:
   - For English: Flesch Reading Ease (FRE) and Flesch-Kincaid Grade Level (FKGL).
   - For non-Latin / Indic scripts: Documented readability proxies (mean sentence length, mean word length, type-token ratio). All metrics are dynamically computed.
