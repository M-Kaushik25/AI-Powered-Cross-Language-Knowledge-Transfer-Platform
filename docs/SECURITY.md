# Security Architecture & Hardening Guide

## 1. Authentication & Role-Based Access Control (RBAC)

CL-RAG enforces cryptographic authentication and strict role-based access control across all endpoints:

### 1.1 Route Security Policy
- Every route requires a valid Bearer JWT **except**:
  - `GET /api/health`
  - `POST /api/auth/login`
  - `POST /api/auth/register`
- Unauthenticated requests to protected routes strictly return **HTTP 401 Unauthorized**.

### 1.2 User Roles & Privilege Matrix

| Role | Permissions | Endpoints Authorized |
| :--- | :--- | :--- |
| **`ADMIN`** | Full platform management, user auditing, term version rollback, empirical evaluation execution | All endpoints including `POST /api/kg/terms/{id}/rollback` and `POST /api/eval/run` |
| **`REVIEWER`** | Approve/dismiss review queue items, propose/update terms, participate in 2-reviewer gate | `POST /api/kg/terms`, `POST /api/kg/terms/{id}/approve`, `POST /api/review/{id}/correct`, `POST /api/review/{id}/dismiss` |
| **`USER`** | Ingest documents, query CL-RAG spaces, run translations, submit candidate suggestions | `POST /api/kg/candidates`, `POST /api/documents/*`, `POST /api/chat`, `POST /api/translate`, `POST /api/adaptive` |

### 1.3 Tenant Scoping (Multi-Tenancy)
- All database entities (`users`, `knowledge_spaces`, `terms`, `review_queue`, `documents`) are scoped by `tenant_id`.
- Queries are strictly isolated by the authenticated user's `tenant_id`. Cross-tenant resource access attempts return HTTP 404 or empty sets.

---

## 2. Token Security & Lifetime

- **Algorithm**: HMAC-SHA256 (`HS256`).
- **Secret Validation**: The server refuses to start in non-development environments if `JWT_SECRET` is the default placeholder or shorter than 32 characters.
- **Token Payload**: Contains subject identifier (`sub`), authenticated role (`role`), `tenant_id`, and UTC expiration timestamp (`exp`).
- **Password Hashing**: Uses `bcrypt` with automatic 72-byte input truncation safeguards to avoid buffer overflow issues.

---

## 3. Knowledge Graph Anti-Poisoning & Provenance

To safeguard against malicious, corrupted, or unverified terminology injection:

1. **Two-Reviewer Consensus Gate ($N=2$)**:
   - Proposed terms or corrections enter `PROPOSED` status.
   - A term is only activated when approved by $N=2$ distinct reviewers.
   - The user who submitted the proposal cannot approve their own submission.
2. **Unicode Script Validation**:
   - Translations submitted for Indic or non-Latin languages are validated against their respective Unicode block (e.g., Devanagari for Hindi, Tamil script for Tamil).
   - Latin loanwords and acronyms are permitted, but corrupt script submissions (e.g. English text submitted as Hindi) are rejected with HTTP 422.
3. **Input Sanitization & Injection Defense**:
   - Rejects empty strings, excessive length, control characters, and prompt injection patterns.
   - String substitution uses safe lambda closures `re.sub(pattern, lambda m: r, text)` to prevent regex backreference corruption.
4. **Provenance Audit Trail**:
   - Every modification writes an immutable record to `term_audit_log` detailing `term_id`, `version`, `action`, `changed_by` (reviewer UUID), `old_value_json`, `new_value_json`, and timestamps.
5. **Admin Rollback**:
   - Administrators can invoke `POST /api/kg/terms/{term_id}/rollback` specifying `target_version` to immediately restore previous verified states.

---

## 4. Rate Limiting, Request Caps & Concurrency

1. **Rate Limiting**:
   - Sliding-window rate limiting per IP and per authenticated user to prevent denial-of-service and LLM quota exhaustion.
2. **Payload Size Caps**:
   - File uploads capped at 15 MB with extension allow-listing (`pdf`, `docx`, `pptx`, `txt`, `md`).
   - LLM generation endpoints enforce maximum input character length caps.
3. **Prompt Injection Hardening**:
   - Source texts and retrieved context are encapsulated in strict XML/data boundary tags (`<source_text>` ... `</source_text>`) instructing models to treat content strictly as passive data.
4. **Database Concurrency & WAL Mode**:
   - SQLite configured with `PRAGMA journal_mode = WAL;`, `PRAGMA busy_timeout = 30000;`, and `PRAGMA foreign_keys = ON;`.
