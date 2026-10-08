# System Architecture & Technical Specifications

## 1. High-Level Architecture Overview

The **AI-Powered Cross-Language Knowledge Transfer Platform (CL-RAG)** is an enterprise research-grade system designed to solve high-stakes terminology drift, catastrophic mistranslation, and domain conceptual fragmentation across resource-diverse languages (English, Hindi, Tamil, German, and Spanish).

```
                      +------------------------------------------+
                      |         Web Client (Vanilla JS)          |
                      |   Modern Glassmorphic Dark UI / Chart.js |
                      +--------------------+---------------------+
                                           | HTTPS / JSON (JWT)
                      +--------------------v---------------------+
                      |           FastAPI Gateway Router         |
                      |   CORS / RBAC Security / WAL DB Pool     |
                      +--------------------+---------------------+
                                           |
         +---------------------------------+---------------------------------+
         |                                 |                                 |
+--------v--------+               +--------v--------+               +--------v--------+
| 5-Agent Pipeline|               |  Living KG (T-KG|               | Cross-Lingual   |
| (Transl, Critic,| <-----------> |  Ontology, Term | <-----------> | RAG & Semantic  |
|  Verifier, Gate)|               |  Relationships) |               | Vectorizer      |
+-----------------+               +--------+--------+               +-----------------+
                                           |
                                  +--------v--------+
                                  | Human Review Hub|
                                  | & Provenance Log|
                                  +-----------------+
```

---

## 2. Core Subsystems

### 2.1 The 5-Agent Translation & Verification Pipeline (`multi_agent_service.py`)

Rather than relying on unconstrained end-to-end LLM generation, translation execution is decomposed into five specialized autonomous agents:

1. **Agent 1: Contextual Translator (`_run_translator_agent`)**
   - Formulates initial target-language drafts.
   - Enforces segment-level terminology constraint injection (AIDA-term design pattern) to avoid batch degradation.
   - Operates in hybrid mode: calls Google Gemini 1.5 Flash when API key is present, or utilizes high-fidelity deterministic offline translation templates when disconnected.

2. **Agent 2: Terminology Controller & Verifier (`_run_verifier_agent`)**
   - Performs symbolic constraint satisfaction verification.
   - Assesses whether required target terms appear verbatim or via normalized morphological variants.
   - Emits symbolic Term Satisfaction Rate ($S_{\text{term}} \in [0.0, 1.0]$).

3. **Agent 3: Cross-Lingual Context Validator (`_run_context_validator_agent`)**
   - Identifies uncovered technical entities and vocabulary gaps.
   - Prevents uncataloged terms from silently bypassing verification.

4. **Agent 4: Adversarial Critic (`_run_critic_agent`)**
   - Evaluates domain register, syntax distortion, punctuation parity, and output length divergence ($0.4 \le \text{ratio} \le 2.5$).
   - Returns a penalized quality critique score ($S_{\text{critic}} \in [0.0, 1.0]$).

5. **Agent 5: Calibrated Gating & Human Router (`_compute_calibrated_confidence`)**
   - Combines symbolic, critic, and historical prior confidence scores via calibrated weighting:
     $$\mathcal{C} = 0.50 \cdot S_{\text{term}} + 0.35 \cdot S_{\text{critic}} + 0.15 \cdot S_{\text{prior}}$$
   - Routing Decision:
     - If $\mathcal{C} \ge \tau$ (where $\tau = 0.85$), segment is marked `AUTOMATICALLY_VERIFIED`.
     - If $\mathcal{C} < \tau$, segment is routed to `review_queue` for expert human intervention.

---

### 2.2 Living Terminology Knowledge Graph (`kg_service.py`)

- **Node Types**:
  - `Domain`: Root clusters (`cloud_computing`, `distributed_systems`, `biomedical_devices`).
  - `Concept`: Abstract ontology anchors.
  - `Term`: Verified technical entries with localized translations (`translations_json`), semantic definitions, version history, and confidence scores.
- **Ontological Relationships** (`term_relationships`):
  - `SUBCLASS_OF` (e.g., `circuit breaker` $\rightarrow$ `fault tolerance`)
  - `CONTEXT_OF` (e.g., `load balancer` $\rightarrow$ `fault tolerance`)
  - `SYNONYM` / `TRANSLATES_TO`
- **Self-Evolution Feedback Loop**:
  - When an authorized reviewer submits a correction via `POST /api/review/{id}/correct`, the Living Knowledge Graph automatically increments term version ($v \rightarrow v+1$), recalibrates confidence, records full provenance in `term_audit_log`, and immediately updates future constraint lookups.

---

### 2.3 Cross-Lingual Semantic Retrieval (`rag_service.py`)

Traditional RAG systems fail when queries and documents are in different languages. CL-RAG implements **Knowledge Graph Concept-Guided Dual-Projection**:

1. **Chunk-Level Indexing**:
   - Ingested document chunks are tokenized and expanded with canonical concept keys (`__concept_fault_tolerance__`) and multilingual synonyms from the Knowledge Graph.
2. **Query Projection**:
   - Queries in Hindi, Tamil, German, or Spanish are mapped through both direct KG lookup and a bilingual bridge dictionary.
   - Canonical concepts and bridged English terms are projected into the query vector.
3. **Hybrid Retrieval**:
   - Computes cosine similarity across the joint multilingual-concept vector space, enabling Hindi queries like *"फॉल्ट टॉलेरेंस उच्च उपलब्धता कैसे प्रदान करता है?"* to retrieve English technical chunks with high relevance ($\ge 0.50$).

---

### 2.4 Expertise-Adaptive Summarization Lab (`adaptive_service.py`)

Adapts complex technical documents into two cognitive formats:
- **Novice Adaptation**: Everyday physical analogies, simplified sentence structures, demystified jargon.
- **Expert Adaptation**: Formal invariants, SLAs, architectural trade-offs, high technical density.
- **Empirical Metric Calculation**:
  - Computes **Flesch Reading Ease (FRE)**:
    $$\text{FRE} = 206.835 - 1.015 \left(\frac{\text{Words}}{\text{Sentences}}\right) - 84.6 \left(\frac{\text{Syllables}}{\text{Words}}\right)$$
  - Computes **Flesch-Kincaid Grade Level (FKGL)**, **Type-Token Ratio (TTR)**, and **Complexity Index** directly from text structures. Zero hardcoded values.
