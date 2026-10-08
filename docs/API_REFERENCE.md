# REST API Specification & Router Reference

Base URL: `http://localhost:8000/api`

---

## 1. Authentication Router (`/api/auth`)

### `POST /api/auth/login`
Authenticates a user and issues a signed JWT Bearer access token.
- **Request Body**:
  ```json
  {
    "email": "reviewer@clrag.org",
    "password": "ReviewerPassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5c...",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "name": "Domain Terminology Reviewer",
      "email": "reviewer@clrag.org",
      "role": "REVIEWER"
    }
  }
  ```

### `GET /api/auth/me`
Returns the currently authenticated user's profile.
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
  ```json
  {
    "id": "uuid",
    "name": "Domain Terminology Reviewer",
    "email": "reviewer@clrag.org",
    "role": "REVIEWER",
    "preferred_lang": "en"
  }
  ```

---

## 2. Multi-Agent Translation Studio (`/api/translate`)

### `POST /api/translate`
Executes the 5-Agent Translation & Verification Pipeline.
- **Request Body**:
  ```json
  {
    "source_text": "Fault tolerance guarantees high availability in distributed architectures.",
    "target_lang": "hi",
    "domain": "cloud_computing"
  }
  ```
- **Response** (`200 OK`): Returns `job_id`, `full_translation`, `avg_confidence`, `term_usage_rate`, `pipeline_telemetry`, and per-segment breakdown containing reports from all 5 agents.

---

## 3. Living Terminology Knowledge Graph (`/api/kg`)

### `GET /api/kg/terms`
Lists all approved terms in the Living Knowledge Graph.
- **Query Params**: `domain` (optional), `search` (optional)

### `POST /api/kg/terms`
Adds or updates a verified term node (Requires `ADMIN` or `REVIEWER` role).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "source_term": "distributed transactions",
    "domain": "cloud_computing",
    "target_lang": "hi",
    "translation": "वितरित लेनदेन",
    "definition": "Transactions spanning multiple network nodes",
    "reviewer_notes": "Expert approved"
  }
  ```

### `POST /api/kg/candidates`
Stages an unverified candidate term proposed by standard users (`USER` role).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "source_term": "edge runtime",
    "domain": "cloud_computing",
    "target_lang": "hi",
    "proposed_translation": "एज रनटाईम"
  }
  ```

### `POST /api/kg/terms/{term_id}/rollback`
Reverts a term to a previous verified version (Requires `ADMIN` role).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "target_version": 1,
    "reason": "Anti-poisoning rollback"
  }
  ```

### `POST /api/kg/extract`
Extracts candidate terms, acronyms, and linguistic noun phrases using C-Value scoring.

### `GET /api/kg/graph`
Exports the complete Knowledge Graph including concept nodes, term nodes, translation nodes, and inter-term relationships (`SUBCLASS_OF`, `CONTEXT_OF`).

---

## 4. Confidence-Gated Review Queue (`/api/review`)

### `GET /api/review`
Lists review queue items filtered by status (`PENDING`, `RESOLVED`, `DISMISSED`, `ALL`).

### `POST /api/review/{item_id}/correct`
Applies an expert human correction, updates the Knowledge Graph, and increments version (Requires `ADMIN` or `REVIEWER` role).

### `POST /api/review/{item_id}/dismiss`
Dismisses a flagged item without altering the Knowledge Graph (Requires `ADMIN` or `REVIEWER` role).

---

## 5. Expertise-Adaptive Summarization (`/api/adaptive`)

### `POST /api/adaptive`
Generates dual-level Novice vs. Expert adaptations with empirical Flesch Reading Ease and Complexity Index metrics.

---

## 6. Cross-Lingual Knowledge Spaces & RAG (`/api/documents`, `/api/chat`)

### `POST /api/documents/spaces`
Creates a knowledge space.

### `POST /api/documents/ingest-text`
Ingests plain text document with automatic chunking and multilingual concept indexing.

### `POST /api/documents/upload`
Uploads a document file (size limit: 15 MB).

### `POST /api/chat`
Answers cross-lingual questions using grounded concept retrieval with empirical confidence scoring.

---

## 7. Evaluation & Ablation Hub (`/api/eval`)

### `GET /api/eval/latest`
Returns the latest stored empirical benchmark results.

### `POST /api/eval/run`
Executes an isolated, non-destructive 3-round self-evolution ablation run against a temporary database.

### `POST /api/eval/baselines`
Runs benchmark comparisons across Vanilla MT, Static Dictionary MT, Monolingual RAG, and Proposed CL-RAG.
