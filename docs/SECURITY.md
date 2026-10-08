# Security Architecture & Hardening Guide

## 1. Authentication & Role-Based Access Control (RBAC)

CL-RAG implements cryptographic authentication and role-based access control to prevent unauthorized modification of the mission-critical Living Knowledge Graph.

### 1.1 User Roles & Privilege Matrix

| Role | Permissions | Endpoints Authorized |
| :--- | :--- | :--- |
| **`ADMIN`** | Full platform management, user auditing, term version rollback | All endpoints including `POST /api/kg/terms/{id}/rollback` |
| **`REVIEWER`** | Approve/dismiss review queue items, update terms, verified feedback | `POST /api/kg/terms`, `POST /api/review/{id}/correct`, `POST /api/review/{id}/dismiss` |
| **`USER`** | Ingest documents, query CL-RAG, submit candidate term suggestions | `POST /api/kg/candidates`, `POST /api/documents/*`, `POST /api/chat`, `POST /api/translate` |

### 1.2 Default Seed Credentials (Development & Evaluation)

| Account Role | Email | Password | Role Key |
| :--- | :--- | :--- | :--- |
| **Chief Systems Architect** | `admin@clrag.org` | `AdminPassword123!` | `ADMIN` |
| **Domain Terminology Reviewer** | `reviewer@clrag.org` | `ReviewerPassword123!` | `REVIEWER` |
| **Research Student** | `user@clrag.org` | `UserPassword123!` | `USER` |

> [!IMPORTANT]
> Passwords are salted and hashed using native `bcrypt` (12 rounds) with input truncation safeguards to avoid 72-byte buffer overflow issues.

---

## 2. Token Security & Lifetime

- **Algorithm**: HMAC-SHA256 (`HS256`).
- **Secret Generation**: Automatically loaded from `JWT_SECRET` environment variable or generated securely using `secrets.token_hex(32)`.
- **Token Payload**: Contains subject identifier (`sub`), authenticated role (`role`), and UTC expiration (`exp`).
- **Default Lifespan**: 1440 minutes (24 hours).

---

## 3. Knowledge Graph Anti-Poisoning & Provenance

To safeguard against malicious or unverified terminology injection:
1. **Provenance Logging**: Every modification writes an immutable record to `term_audit_log` detailing `term_id`, `version`, `action`, `changed_by` (authenticated user UUID), `old_value_json`, `new_value_json`, `reviewer_notes`, and timestamp.
2. **Version Rollback**: If an erroneous or poisoned term is approved, administrators can invoke `POST /api/kg/terms/{term_id}/rollback` specifying `target_version`. The engine reads the historical audit log, restores prior translations, increments the version with action `ROLLBACK`, and re-logs provenance.
3. **Staged Candidate Ingestion**: Standard users cannot directly write to the approved Knowledge Graph. User suggestions are staged with `status = 'CANDIDATE'` and confidence $0.50$ pending Reviewer approval.

---

## 4. Input Sanitization & Defensive Engineering

1. **Regex Backreference Injection Defense**:
   - Standard `re.sub(pattern, replacement, text)` crashes with `re.error: bad escape` or expands corrupted backreferences if replacement strings contain `\1`, `\g<1>`, or backslashes.
   - All string substitution pipelines utilize safe literal callable closures:
     ```python
     re.sub(pattern, lambda m, r=replacement_val: r, text, flags=re.IGNORECASE)
     ```
2. **SQL Injection Defense**:
   - 100% of database interactions utilize parameterized queries (`?` parameter placeholders). No string concatenation is used in SQL statements.
3. **File Upload Hardening**:
   - File size ceiling enforced at **15 MB**. Payloads exceeding this limit receive HTTP 413.
   - File type whitelist: `.txt`, `.md`, `.pdf`, `.docx`, `.json`, `.csv`.
4. **Database Concurrency & WAL Mode**:
   - SQLite configured with `PRAGMA journal_mode = WAL;`, `PRAGMA busy_timeout = 30000;`, and `PRAGMA foreign_keys = ON;` to eliminate locking collisions under concurrent multi-process access.
