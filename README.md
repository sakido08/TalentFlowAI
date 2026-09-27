# Talentflow AI

**Where AI Meets Career Potential** is a small academic prototype for resume extraction, candidate management, and explainable resume-to-job matching. It uses rule-based extraction and classic machine learning rather than a custom deep-learning model.

## Features

- Account registration and login with hashed passwords and JWT sessions
- User, recruiter, and administrator roles
- PDF and DOCX upload with a 10 MB limit and local file storage
- Resume text extraction, conservative cleanup, and editable structured fields
- Regular-expression email/phone/date handling, heading-based sections, and a small editable skills dictionary
- Candidate search and profile review
- Recruiter job descriptions and weighted candidate/job matching
- Admin role/access management and a small activity log
- Plain HTML, CSS, and JavaScript frontend

## Technologies and structure

- **Frontend:** HTML, CSS, browser JavaScript
- **Backend:** Python and FastAPI
- **Database:** PostgreSQL through SQLAlchemy; SQLite is supported as a zero-setup demo/test option
- **Resume parsing:** PyMuPDF for PDF, python-docx for DOCX
- **Matching:** weighted skill coverage, TF-IDF/cosine similarity, experience/education signals, and optional SBERT semantic similarity
- **Authentication:** Argon2 password hashing through pwdlib and signed JWT tokens

```text
backend/
  main.py                 FastAPI app and static frontend
  database.py             SQLAlchemy connection and sessions
  models.py               Relational tables
  routes/                 Authentication, resumes, candidates, jobs, matching, admin
  services/               Parsing, cleanup, extraction, skills, similarity
frontend/
  index.html              Login and application shell
  css/style.css           Minimalist layout
  js/app.js               Pages and API interactions
tests/                    API, extraction, and matching tests
uploads/                  Locally stored original resume files
```

## System architecture

```text
Browser (HTML/CSS/JavaScript)
          ↓ JSON and file uploads
FastAPI routes and role checks
          ↓
Resume services: extract → clean → identify fields
          ↓
SQLAlchemy models → PostgreSQL (or SQLite for a demo)
          ↓
TF-IDF vectors → cosine similarity for candidate/job comparison
```

The backend serves the frontend from the same origin, so there is no separate frontend build step or CORS setup.

## Database

The `users` table stores account details and roles. A resume belongs to the user who uploaded it; each resume can have one candidate profile. Skills, education, experience, and certifications are separate rows connected to that profile. Recruiters own jobs. Matches store the TF-IDF score and an optional semantic score (not currently enabled). Activity rows record selected account and workflow actions.

For this prototype, SQLAlchemy `create_all()` creates missing tables on startup. If the schema changes after a database already exists, reset the demo database or add a migration before retaining important data.

## Installation

Python 3.11 or newer and PostgreSQL are recommended. Create a database and login role (using your own password), then from this project directory run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If `py` is unavailable on Windows, install Python and use `python` in its place. For a local PostgreSQL server, create the login and database in `psql` (choose your own password):

```sql
CREATE ROLE talentflow LOGIN PASSWORD 'your-password';
CREATE DATABASE talentflow OWNER talentflow;
```

The copied `.env.example` is already set to PostgreSQL. Update the password in its `DATABASE_URL` to match the role you created. If you need to demonstrate the project before PostgreSQL is available, change `DATABASE_URL` to `sqlite:///./talentflow.db`; the application code supports both databases.

Also set `SECRET_KEY` to a long random value for any shared deployment. Uploaded source files go to `UPLOAD_DIR` (default `uploads/`); do not expose that directory as a public static folder.

## Run the application

From the project root:

```powershell
python -m uvicorn backend.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Create fictional demo accounts, candidates, and jobs in the configured database:

```powershell
python -m backend.seed_demo
```

Demo accounts:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@talentflow.local` | `AdminDemo123!` |
| Recruiter | `recruiter@talentflow.local` | `Recruiter123!` |
| User | `user@talentflow.local` | `UserDemo123!` |

These are classroom-only credentials. Do not use them for a public deployment.

## Use the main workflow

1. Register a regular user or log in as the demo recruiter.
2. Upload a PDF or DOCX. The backend extracts text and creates a candidate profile.
3. Review the original extracted text beside the structured fields. Correct fields and save.
4. As a recruiter, add a job description and comma-separated required skills.
5. Choose a candidate and job on Matching. Review the score and matched/missing skill list.
6. As an admin, assign recruiter roles, enable/disable accounts, and inspect activity.

## How resume extraction works

1. PyMuPDF reads selectable text from a PDF; python-docx reads paragraphs and table cells from DOCX.
2. Cleanup normalizes line breaks and whitespace while retaining contact details, dates, and useful punctuation. The original and cleaned text are both stored.
3. Regular expressions find email addresses, phone numbers, and dates. Familiar headings divide sections. The first plausible short name in the header is offered as a name guess.
4. A small skill dictionary finds known technologies. Add terms to `backend/services/skills.py` as the project grows.
5. The guesses are saved as editable candidate fields. They are intentionally reviewed by a person because resume formats vary.

Optional spaCy entity recognition is not enabled. SBERT is off by default; the required extraction and matching baseline work without it. Scanned image-only PDFs need OCR, which is outside this prototype.

## How matching works

The matching page displays a weighted overall score and the raw score and weight for each component. With SBERT off, the formula is:

```text
0.55 × TF-IDF + 0.30 × skills + 0.10 × experience + 0.05 × education
```

When SBERT is configured, the formula is:

```text
0.40 × SBERT + 0.30 × skills + 0.15 × TF-IDF + 0.10 × experience + 0.05 × education
```

**TF-IDF** turns the resume and job description into weighted word vectors. **Cosine similarity** compares the direction of those vectors. Skill coverage is the share of comma-separated job requirements present in the candidate's reviewed skill list. Experience and education scores indicate whether a dated experience period or education details were detected; they do not measure relevance, years required, or qualification fit. Optional **SBERT** compares normalized sentence embeddings and is loaded only when `SBERT_MODEL` is set.

The overall score is an algorithmic indicator for human review. It is not a probability of being hired and must not be used as an automatic hiring decision. If SBERT is unavailable or fails to load, the app uses the default TF-IDF weights.

To enable SBERT, install the optional package and configure a model name in `.env`:

```powershell
python -m pip install sentence-transformers
```

```text
SBERT_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The matched/missing skill list compares the job's comma-separated requirements with known skills detected from the resume. It is a useful review aid, not a complete understanding of someone’s abilities.

## Tests

The tests cover registration/login, password rejection, role restrictions, PDF and DOCX extraction, missing information, preprocessing, skill matching, and TF-IDF similarity. They use an isolated in-memory SQLite database:

```powershell
python -m pytest
```

## Limitations and future improvements

- Extraction guesses can miss or mislabel information; human review is part of the intended workflow.
- The skills list and resume heading names are deliberately small and English-oriented.
- Image-only PDFs are not OCR processed. Address, company, and job-title extraction remain basic.
- Files are stored on the local filesystem. This is suitable for a classroom prototype, not a multi-server deployment.
- There is no password reset, email verification, account self-service settings, or database migration tool.
- Optional future work: OCR, carefully evaluated spaCy NER, evaluation of SBERT and the weighted signals, richer filters, audit history pagination, and migration support.

## API overview

- `POST /api/register`, `POST /api/login`, `GET /api/me`
- `POST /api/resumes/upload`, `GET /api/resumes`, `GET /api/resumes/{id}`, `POST /api/resumes/{id}/extract`, `PUT /api/resumes/{id}`, `DELETE /api/resumes/{id}`
- `GET /api/candidates`, `GET /api/candidates/{id}`, `PUT /api/candidates/{id}`, `DELETE /api/candidates/{id}`
- `GET/POST /api/jobs`, `PUT/DELETE /api/jobs/{id}`
- `POST /api/matching`
- `GET /api/admin/users`, `PUT /api/admin/users/{id}/role`, `PUT /api/admin/users/{id}/active`, `DELETE /api/admin/users/{id}`
