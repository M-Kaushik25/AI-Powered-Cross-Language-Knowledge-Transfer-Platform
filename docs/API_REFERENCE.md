# REST API Specification & Router Reference

Base URL: `http://localhost:8000/api`

---

## 1. Authentication Router (`/api/auth`)

### `POST /api/auth/login`
Authenticates user and returns JWT Bearer token.
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
      "role": "REVIEWER",
      "tenant_id": "default_tenant"
    }
  }
  ```

### `GET /api/auth/me`
Returns currently authenticated user profile.
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`)

---

## 2. Multi-Agent Translation Studio (`/api/translate`)

### `POST /api/translate`
Executes multi-agent translation pipeline with terminology constraint enforcement.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "source_text": "Fault tolerance guarantees high availability in distributed architectures.",
    "target_lang": "hi",
    "source_lang": "en",
    "domain": "cloud_computing",
    "mode": "auto"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "job_id": "uuid",
    "full_translation": "...",
    "mode": "live",
    "avg_confidence": 0.88,
    "term_usage_rate": 1.0,
    "segments": [
      {
        "segment_id": 0,
        "source_text": "...",
        "target_text": "...",
        "engine": "live:gemini-1.5-flash",
        "weighted_confidence": 0.88,
        "verifier_score": 1.0,
        "critic_score": 0.85,
        "status": "AUTOMATICALLY_VERIFIED"
      }
    ]
  }
  ```

---

## 3. Living Terminology Knowledge Graph (`/api/kg`)

### `GET /api/kg/terms`
Lists approved terms in the Living Knowledge Graph for the caller's tenant.
- **Headers**: `Authorization: Bearer <token>`
- **Query Params**: `domain` (optional), `search` (optional)

### `POST /api/kg/terms`
Proposes a new term or translation (Requires `REVIEWER` or `ADMIN`).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "source_term": "fault tolerance",
    "domain": "cloud_computing",
    "target_lang": "hi",
    "translation": "दोष सहनशीलता",
    "definition": "Ability of a system to continue operating properly"
  }
  ```
- **Response** (`201 Created`): Returns term object with status `PROPOSED`.

### `POST /api/kg/terms/{term_id}/approve`
Records an approval in the 2-reviewer consensus gate (Requires `REVIEWER` or `ADMIN`). Proposer cannot approve own submission.
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`): Returns approval count ($n$ of $N$) and updated term status (`APPROVED` once consensus reached).

### `POST /api/kg/terms/{term_id}/rollback`
Rolls back term to a prior version (Requires `ADMIN`).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**: `{"target_version": 1, "reason": "Restoration"}`

### `GET /api/kg/graph`
Exports graph topology including nodes, translations, and relational edges (`synonym`, `broader`, `narrower`, `related`, `abbreviation_of`).
- **Headers**: `Authorization: Bearer <token>`

---

## 4. Confidence-Gated Review Queue (`/api/review`)

### `GET /api/review`
Lists review queue segments filtered by status (`PENDING`, `RESOLVED`, `DISMISSED`).
- **Headers**: `Authorization: Bearer <token>`

### `POST /api/review/{item_id}/correct`
Applies a human correction and propagates term to the Living Knowledge Graph.
- **Headers**: `Authorization: Bearer <token>` (Requires `REVIEWER` or `ADMIN`)
- **Request Body**:
  ```json
  {
    "corrected_translation": "...",
    "reviewer_notes": "Expert approved"
  }
  ```

---

## 5. Expertise-Adaptive Summarization (`/api/adaptive`)

### `POST /api/adaptive`
Generates expertise-adapted summary across 3 levels (`novice`, `intermediate`, `expert`).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "text": "...",
    "target_level": "expert",
    "domain": "cloud_computing"
  }
  ```
- **Response** (`200 OK`): Returns adapted text, faithfulness verification report, and empirical readability scores.

---

## 6. Cross-Lingual Knowledge Spaces & RAG (`/api/documents`, `/api/chat`)

### `POST /api/documents/spaces`
Creates a scoped knowledge space.
- **Headers**: `Authorization: Bearer <token>`

### `POST /api/documents/upload`
Uploads and parses a document (`.pdf`, `.docx`, `.pptx`, `.txt`, `.md`) preserving page and slide offsets.
- **Headers**: `Authorization: Bearer <token>`

### `POST /api/chat`
Answers cross-lingual questions using dense multilingual retrieval (`multilingual-e5-base`), KG query expansion, and grounded evidence citations.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "space_id": "uuid",
    "query": "दोष सहनशीलता क्या है?",
    "target_lang": "hi"
  }
  ```
- **Response** (`200 OK`): Returns answer, supporting citations with page numbers and exact text spans, and support confidence.

---

## 7. Evaluation & Ablation Hub (`/api/eval`)

### `GET /api/eval/latest`
Returns the latest stored empirical benchmark results from `data/evaluation/runs/`.
- **Headers**: `Authorization: Bearer <token>`

### `POST /api/eval/run`
Executes an empirical benchmark on an isolated temporary database (Requires `ADMIN`).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "domain": "cloud_computing",
    "target_lang": "hi",
    "rounds": 3
  }
  ```
- **Response** (`200 OK`): Returns multi-round results across B1, B2, Proposed, and ablations, persisting run outputs to disk.
