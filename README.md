# Samavesh

An accessible platform for Indian higher-education institutions to record accommodation plans, track support delivered, monitor statutory compliance, manage approvals and handle grievances for specially abled students. Built to WCAG 2.1 Level AA.

## Setup

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22+, pnpm 11+.

```bash
# API (port 8210)
cd backend
cp .env.example .env          # development defaults work as they are
uv run python -m app.seed     # creates the database and demo data
uv run uvicorn app.main:app --port 8210 --reload

# Web (port 3210), in another terminal
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:3210.

### Tests

```bash
cd backend && uv run pytest              # business rules, RBAC coverage, encryption, audit immutability
cd frontend && pnpm test:e2e             # axe (WCAG 2.1 A + AA) on every page, in three themes and in Hindi, plus keyboard and flow tests
```

Set `TEST_DATABASE_URL` to a PostgreSQL URL to run the backend tests against PostgreSQL as well.

## Demo logins

Password for every account: **`Samavesh-Demo-2026`**

| Role | Email |
|---|---|
| Administrator | admin@samavesh.example.com |
| Nodal officer | nodal@samavesh.example.com |
| Grievance officer | grievance@samavesh.example.com |
| Support staff | staff@samavesh.example.com (assigned to Asha and Kavya) |
| Support staff | staff2@samavesh.example.com (assigned to Imran) |
| Student (adult) | student@samavesh.example.com (Asha Verma) |
| Student (adult) | student2@samavesh.example.com (Imran Sheikh) |
| Student (under 18) | minor@samavesh.example.com (Kavya Menon, consent gate applies) |
| Guardian | guardian@samavesh.example.com (linked to Kavya) |

Grievance tracking references that exist in the demo: `GRV-DEMO-RECV-2222`, `GRV-DEMO-REVW-2222`, `GRV-DEMO-LATE-2222` (auto-flagged), `GRV-DEMO-DONE-2222`, `GRV-DEMO-ESCL-2222`. They need no sign-in.

Emails are not sent in development. They appear at `/dev/outbox` (signed out, development only).

## Configuration

`backend/.env` (see `backend/.env.example`). In production set:

- `ENV=prod`, `SECRET_KEY` (32+ characters), `DATA_ENCRYPTION_KEYS` (`<id>:<base64 32-byte key>`; add an id to rotate).
- `DATABASE_URL` (PostgreSQL). `SMTP_*` for real email.
- `JOBS_SECRET` for the daily job endpoint. Leave empty to disable it.

Production refuses to start with the development secrets.

## Daily jobs

`POST /internal/jobs/run` with header `X-Jobs-Secret` sends reminders (compliance 7 days before due, plan review 7 days before) and flags grievances for escalation after the configured number of working days. It is idempotent, so running it twice in a day sends nothing new. Locally: `uv run python -m app.jobs`. `.github/workflows/cron.yml` calls it daily.

## Layout

```
backend/   FastAPI, SQLAlchemy 2, Alembic, pytest
  app/     models/, routers/, rules/ (pure business rules), permissions.py, audit.py, crypto.py
frontend/  Next.js 16 (App Router), TypeScript, Tailwind 4
  app/     pages and Server Actions;  components/Form.tsx is the only form primitive
  messages/ en.json and hi.json (every visible string)
  tests/   Playwright: a11y.spec.ts, keyboard.spec.ts, flows.spec.ts
```

## Known limits

- Hindi strings are drafted; have a fluent reader review them before a demo.
- The compliance checklist is seeded with illustrative RPwD Act 2016 and UGC references. Each is marked "verify against official text". This is not legal advice.
- Alembic migration files are not generated yet; development uses `create_all` through the seed script.
- Out of scope: medical assessment, legal advice, payments, machine learning.
