# Secure Digital Abuse Reporting Platform

An enterprise-grade, secure web application designed to empower citizens to safely report digital abuse, cyberbullying, harassment, and cyber crimes with end-to-end evidence validation, privacy controls, status tracking, and reviewer dashboards.

---

## 🎓 Academic Semester Evaluation Status

- **Academic Milestone:** Current Semester Mid-Term Evaluation (~55–60% Completion Target Achieved)
- **Automated Test Suite:** 23 / 23 Tests Passing (100% Pass Rate via Pytest)
- **Status:** Stable Working Baseline Ready for Mentor Evaluation

---

## 🛠️ Technology Stack

- **Backend:** Python 3.13, Flask (Application Factory pattern)
- **Database:** SQLite (managed via SQLAlchemy ORM with normalized relations)
- **Frontend:** Responsive HTML5, CSS3, Vanilla JavaScript (ES6) with Jinja2 Templating
- **Security & Integrity:** Werkzeug cryptographic hashing, signed HttpOnly session cookies, role-based access control (RBAC), isolated evidence storage, SHA-256 file checksums, immutable audit logging
- **Testing:** Pytest 9.2 (23 unit & integration tests)
- **Version Control:** Git & GitHub

---

## 📋 Semester Milestone Breakdown

### 1. Completed Modules (Current Semester)

| Module | Implementation Details | Associated Files |
|:---|:---|:---|
| **Database Management (Req 11)** | Normalized SQLite schema containing 6 relational models: `User`, `ReportCategory`, `IncidentReport`, `EvidenceFile`, `AuditLog`, `Notification`. Foreign keys, database indexes, and cascading deletes implemented. | [`app/models/`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/models/), [`init_db.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/init_db.py) |
| **Data Seeding** | Automated script populating 7 standardized abuse categories and pre-configured test accounts (`admin@digitalabuse.gov`, `citizen@example.com`). | [`init_db.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/init_db.py) |
| **User Authentication (Req 1)** | Complete citizen registration, login, and logout available via both web browser forms and REST JSON APIs. Prevents duplicate email signups and enforces password strength rules. | [`app/routes/auth.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/routes/auth.py), [`app/services/auth_service.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/services/auth_service.py) |
| **Password Security & Hashing (Req 10)** | Passwords are never stored in plain-text. Cryptographic salting and verification handled via `werkzeug.security.generate_password_hash`. | [`app/models/user.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/models/user.py) |
| **Session Security & RBAC** | Signed `HttpOnly` and `SameSite=Lax` session cookies. Custom decorators (`@login_required`, `@admin_required`, `@role_required`) protecting authenticated pages and API routes. | [`app/services/auth_service.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/services/auth_service.py) |
| **Incident Reporting (Req 3, 4)** | Multi-field reporting interface capturing title, platform, category, incident date (validated not in the future), description, and evidence files. | [`app/routes/citizen.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/routes/citizen.py), [`app/templates/citizen/report.html`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/templates/citizen/report.html) |
| **Secure Evidence Storage (Req 5)** | Evidence files strictly stored in `uploads/evidence/` **outside `app/static/`**. Whitelist extension enforcement (`png`, `jpg`, `pdf`, `mp4`, `txt`), UUID4 filenames (`ev_<uuid>.ext`), and 16 MB size limits. | [`app/services/file_service.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/services/file_service.py), [`uploads/evidence/`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/uploads/evidence/) |
| **Evidence Access Control (Req 5, 10)** | Secure streaming route (`/evidence/view/<file_id>`) verifying that caller is either the complaint owner or a verified administrator. Unauthorized visitors receive `HTTP 403 Forbidden`. | [`app/routes/evidence.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/routes/evidence.py) |
| **Complaint Reference & Tracking (Req 7)** | Automatic generation of collision-proof tracking codes (e.g. `REP-2026-F9A8C2B1`). Live status tracking page with privacy shielding for public viewers. | [`app/routes/citizen.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/routes/citizen.py), [`app/templates/citizen/track.html`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/templates/citizen/track.html) |
| **Citizen Dashboard ("My Reports")** | Responsive web view listing user complaints, current review status, evidence counters, and tracking links. | [`app/templates/citizen/my_reports.html`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/templates/citizen/my_reports.html) |
| **Audit Logging Service (Req 10)** | Backend service persisting immutable audit trail entries (`USER_REGISTERED`, `LOGIN_SUCCESS`, `LOGIN_FAILED`, `REPORT_SUBMITTED`, `EVIDENCE_ACCESSED`). | [`app/services/audit_service.py`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/services/audit_service.py) |
| **Citizen Web Frontend** | Responsive Jinja2 web templates for Home, Sign In, Register, File Report, My Reports, and Case Tracking. | [`app/templates/`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/app/templates/) |
| **Automated Testing Suite** | 23 comprehensive tests covering database relations, authentication, input validation, role checks, reporting workflows, evidence security, and browser rendering. | [`tests/`](file:///C:/Users/darsh/.gemini/antigravity/scratch/secure-digital-abuse-reporting/tests/) |

---

### 2. Partially Completed Modules (Current Semester Baseline)

* **Evidence Checksum Generation (Req 5):**
  - *Implemented:* `app/services/file_service.py` computes SHA-256 hashes during upload.
  - *Pending for Next Semester:* Adding a dedicated `file_hash` column to the `EvidenceFile` SQLite table schema to persist the checksum long-term.
* **Notification System (Req 9):**
  - *Implemented:* `Notification` model and automated notification generation on report submission.
  - *Pending for Next Semester:* Reviewer status transition triggers and interactive in-app notification inbox.
* **User Privacy Controls (Req 2):**
  - *Implemented:* Public status tracker shields confidential victim descriptions; profile inspection via `/auth/me`.
  - *Pending for Next Semester:* Explicit anonymous report toggle and pseudonymization settings.

---

### 3. Features Intentionally Reserved for Next Semester

As per project guidelines and academic milestone requirements (~50–60% target), the following advanced features are intentionally reserved for the upcoming semester:

1. **Reviewer / Administrator Dashboard (Req 8):**
   - Reviewer case management interface (`app/routes/reviewer.py`).
   - Case status lifecycle progression (`Pending` &rarr; `Under Review` &rarr; `Resolved` / `Rejected`).
   - Investigator internal notes and severity assignment.
   - Administrative security audit log viewer interface.
2. **Optional NLP / Machine Learning Abuse Identification (Req 6):**
   - Scikit-learn and Pandas text classification model (`app/services/ml_service.py`).
   - Automatic category recommendation and toxicity/severity scoring based on description text.
3. **Advanced Analytics & Export:**
   - Platform incident statistics and PDF report generation.
4. **Production Cloud Deployment:**
   - Production WSGI configuration (Gunicorn/Waitress), HTTPS/SSL enforcement, and containerization.

---

## 🏃 Mentor Evaluation & Quick Start Guide

### Step 1: Environment Setup
Ensure Python 3.13 is available. Activate the project virtual environment:
```powershell
# From the project root:
.\venv\Scripts\Activate.ps1
```

### Step 2: Database Initialization & Seeding
The SQLite database is pre-initialized, but can be cleanly re-seeded anytime with:
```powershell
.\venv\Scripts\python.exe init_db.py
```
*Seeded Test Accounts:*
- **Citizen User:** `citizen@example.com` / `Citizen@12345` (Role: `user`)
- **System Admin:** `admin@digitalabuse.gov` / `Admin@12345` (Role: `admin`)

### Step 3: Run the Automated Test Suite
Verify that all 23 unit and integration tests pass:
```powershell
.\venv\Scripts\python.exe -m pytest tests -v
```

### Step 4: Launch the Live Web Application
Start the local development server:
```powershell
.\venv\Scripts\python.exe run.py
```
Open your browser (Google Chrome, Edge, or Firefox) and navigate to:
👉 **`http://127.0.0.1:5000/`**

---

## 🧪 Mentor Demonstration Script

1. **Visit Home Page (`/`):** View public safety guidelines, category overviews, and reporting workflow.
2. **Citizen Registration (`/register`):** Register a new citizen account or log in with `citizen@example.com` / `Citizen@12345`.
3. **Submit an Incident (`/report`):**
   - Choose a category (e.g., *Cyberbullying* or *Impersonation*).
   - Select platform (*Instagram*, *WhatsApp*, etc.).
   - Choose incident date (demonstrate that future dates cannot be selected).
   - Enter detailed description.
   - Attach a proof screenshot or document (`.png`, `.jpg`, `.pdf`).
   - Submit and receive instant reference code (e.g. `REP-2026-XXXXXXXX`).
4. **Complaint Tracking (`/track/<report_number>`):**
   - View complaint status badge (*Pending*).
   - Click to view or download attached evidence.
5. **View My Reports (`/my-reports`):** Review the citizen dashboard table showing all personal submissions.
6. **Role-Based Access Verification:**
   - Attempting to view another citizen's evidence returns `HTTP 403 Forbidden`.
   - Admin check endpoint (`/auth/admin/check`) returns `403 Forbidden` for standard users and `200 OK` for administrators.

---

## 🔒 Security Architecture Highlights

1. **Evidence Isolation:** Uploaded evidence is stored in `uploads/evidence/` outside `app/static/`, preventing unauthorized web access or public search engine indexing.
2. **Access-Controlled Streaming:** Evidence files are only served via `/evidence/view/<id>`, which verifies session authentication and ownership.
3. **Defense Against Path Traversal:** File names are sanitized with Werkzeug and assigned random UUIDs.
4. **Zero Plain-Text Passwords:** Salted hashes generated via PBKDF2/scrypt.
5. **Session Hardening:** Signed cookies with `HttpOnly` and `SameSite=Lax` flags.
