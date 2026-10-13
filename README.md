# Student Success Platform

A development foundation for an AI-powered student success platform. **All included seed records and credentials are fictional demo data; do not use real student information.**

## Prerequisites

- Docker Desktop with Docker Compose
- (Optional, for running the API or web app outside Docker) Python 3.11+ and Node.js 20.19+ (or 22.12+)

## Run locally with Docker

1. Copy `.env.example` to `.env`. If you change `POSTGRES_PASSWORD`, update the password in `DATABASE_URL` to the same value.
2. Start the services:

   ```powershell
   docker compose up --build
   ```

3. Apply the database migration (in another terminal):

   ```powershell
   docker compose exec api alembic upgrade head
   ```

4. Add the fictional sample dataset:

   ```powershell
   docker compose exec api python -m app.seed
   ```

The starter frontend is at <http://localhost:5173>, the API health endpoint at <http://localhost:8000/health>, and interactive API documentation at <http://localhost:8000/docs>.

## Demo accounts

The seed script creates fictional accounts with the same demo password, `DemoPass123!`. Use one of these accounts to visit each role portal:

| Role | Demo email |
| --- | --- |
| Student | `student.cs.001@demo.invalid` |
| Faculty | `faculty.cs.1@demo.invalid` |
| Dean | `dean.cs@demo.invalid` |
| Principal | `principal@demo.invalid` |

These reserved `.invalid` addresses and credentials are for local demonstration only. Do not use them or the development JWT key in a deployed environment.

To stop the services, run `docker compose down`. To remove the local database volume and its demo data, run `docker compose down -v`.

## Run the API without Docker

From `backend`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://student_success:change_me_for_local_development@localhost:5432/student_success"
python -m alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

PostgreSQL must be available at the configured URL. To run the API tests, use `pytest` from `backend`.

For the frontend, open a second PowerShell terminal in `frontend` and run:

```powershell
npm install
npm run dev
```

During development, Vite proxies `/auth`, `/portals`, `/student`, `/faculty`, `/analytics`, and `/health` to the backend. This keeps browser requests same-origin if Vite chooses a different frontend port. The default proxy target is `http://127.0.0.1:8000`; if the API uses another port, set `VITE_PROXY_TARGET` before starting Vite (for example, `$env:VITE_PROXY_TARGET = "http://127.0.0.1:8001"`). The demo accounts only work after running the migrations and seed steps above.

## Authentication

- `POST /auth/register` creates a **student-only** account. Faculty, dean, and principal accounts must be provisioned by the institution; a client cannot register itself with an elevated role.
- `POST /auth/login` accepts an email and password.
- `POST /auth/refresh` rotates a refresh token. A rotated or logged-out refresh token cannot be reused.
- `POST /auth/logout` revokes the submitted refresh token; include the access token as a bearer token.
- `GET /auth/me` returns the authenticated user's profile. `GET /auth/departments` supplies department options for student registration.
- The sample `/portals/student`, `/portals/faculty`, `/portals/dean`, and `/portals/principal` endpoints require their matching role.

The server hashes passwords with bcrypt. Access tokens expire after 15 minutes and refresh tokens after 7 days by default; configure these with `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS`. The browser keeps the access token in memory and the rotating refresh token in tab-scoped `sessionStorage`. Set a private `JWT_SECRET_KEY` and `FRONTEND_ORIGIN` in `.env` before deployment. `FRONTEND_ORIGIN` accepts a comma-separated list; local HTTP origins on `localhost` and `127.0.0.1` are also allowed on alternate Vite ports for development.

## Student portal (Phase 3)

After signing in as a student, the `/student` portal shows enrolled courses, recorded attendance and marks, and the student's latest risk assessment with its observed factors. `/student/journey` shows the student's own enrollment, attendance, assessment, intervention, and faculty-feedback events. `/student/feedback` shows feedback from faculty, a form for rating an enrolled course and its assigned faculty member, and previously submitted feedback.

The student API derives `student_id` exclusively from the authenticated account. Student endpoints do not accept a student ID in their path or request body. Feedback submissions are checked against the authenticated student's enrollments and the course's assigned faculty member.

To migrate an existing database after updating, run `docker compose exec api python -m alembic upgrade head`. The API test suite includes student-to-student data-isolation and feedback ownership checks.

## Faculty portal (Phase 4)

Faculty accounts can open `/faculty` to view assigned courses, enrolled students, attendance, marks and assessments, risk factors, open alerts, student notes, interventions, and submitted course feedback. The portal provides attendance marking, assessment creation, mark entry, notes, and intervention assignment forms. Each screen includes loading, empty, and recoverable error states.

Faculty API operations derive the acting faculty member from the authenticated user. Course reads and writes require ownership of that course, and student reads and writes require an enrollment in a course assigned to that faculty member. Attendance and mark updates are scoped to the assigned course as well. Attendance dates and intervention start dates cannot be in the future; attendance is unique per student/course/date; marks cannot exceed their assessment maximum. Attendance, mark, student-note, and intervention creates/updates write an audit event in the same database transaction.

The faculty API is under `/faculty`: `/dashboard`, `/courses/{course_id}/students`, `/attendance`, `/courses/{course_id}/assessments`, `/courses/{course_id}/marks`, `/students/{student_id}/notes`, `/students/{student_id}/interventions`, `/at-risk`, `/alerts`, and `/feedback`. Changes that update attendance, marks, and notes use `PUT` endpoints under those resources. Faculty isolation and input validation are covered by backend tests.

## Data integration (Phase 4)

Separate PostgreSQL source tables capture academic, overall/subject attendance, LMS, engagement, placement, skills, and feedback records. The seeded fictional feeds deliberately include nulls, duplicate rows, inconsistent and unmatched student identifiers, and out-of-range values. For an existing seeded database, run `python -m app.seed_integration` from `backend`; for a fresh database, `python -m app.seed` includes these sources. The source-only seed refuses to add duplicates if any integration source table is already populated.

`GET /analytics/data-integration` combines these feeds into a unified student view and returns a quality report with ingested/cleaned row counts, null imputations, duplicates removed, out-of-range values, and unresolved IDs. Deans see only their department; principals see the institution; student and faculty roles are denied. Identifier matching, validation/imputation rules, example API use, and limitations are documented in [docs/DATA_INTEGRATION.md](./docs/DATA_INTEGRATION.md).

## Success scores and segmentation (Phases 5–6)

`GET /analytics/success-scores` returns weighted 0–100 scores, academic and placement category scores and risk flags, cohort-relative drivers, data completeness, and confidence labels. `GET /analytics/risk-flags` returns both risk flags and their drivers. `GET /analytics/segments` assigns exactly one primary segment and suggested action per student. All three require a dean or principal: deans see their own department; principals see the institution. Indicator weights, normalization, thresholds, segment rules, and caveats are documented in [docs/SUCCESS_SCORE.md](./docs/SUCCESS_SCORE.md).

## Dean and principal dashboards (Phase 7)

The dean and principal portals open the interactive dashboard at `/dean` and `/principal`. Overview includes score and risk KPIs, a score distribution, department risk counts, and data-derived insights. Segment actions, searchable/filterable/sortable student records, per-student score/risk drivers, completeness/confidence, and data-quality metrics are available in the dashboard sections. Dashboard visualizations use Recharts and the existing scoped analytics endpoints. Login offers seeded Dean and Principal demo shortcuts; all accounts use the fictional `DemoPass123!` password.

## Database compatibility

The application, SQLAlchemy models, and Alembic migrations target PostgreSQL via `postgresql+psycopg`; the Compose setup starts PostgreSQL 16. The automated endpoint tests use an in-memory SQLite database with SQLite's `StaticPool` solely as a lightweight **test fixture**. There is no SQLite application configuration or SQLite-specific SQL in the application or migrations. For production-like integration verification, apply migrations and run tests against a PostgreSQL instance using `DATABASE_URL`.

## Project layout

- `backend/app/api`: API routes
- `backend/app/core`: settings and database setup
- `backend/app/models`: SQLAlchemy domain models
- `backend/app/repositories`: persistence boundary
- `backend/app/schemas`: Pydantic API schemas
- `backend/app/services`: business-logic boundary
- `backend/alembic`: database migrations
- `backend/tests`: backend tests
- `frontend/src`: React application

The schema establishes the core institution, coursework, student journey, source integration, analytics, and audit entities. Authentication and role-specific access, student and faculty workflows, explainable success/risk scoring, segmentation, and dean/principal dashboards are in place; intervention effectiveness and remaining hardening are planned for later project phases.
