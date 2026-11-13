# Samavesh platform - core

Multi-role accessibility-first platform (accommodation plans, provision, compliance, approvals, grievances). WCAG 2.1 AA failures are build failures.

## Source map
- `backend/app/` FastAPI. `main.py` mounts routers; `deps.py` auth/RBAC; `audit.py` append-only log; `crypto.py` encrypted column types; `models/`; `routers/`; `rules/` pure business rules; `seed.py` demo data.
- `frontend/` Next.js 16 App Router. `app/actions.ts` all Server Actions; `lib/` api/session/i18n/form helpers; `components/Form.tsx` the only form primitive; `messages/{en,hi}.json`; `tests/` Playwright.

## Invariants
- Browser never calls the API for pages. Next server calls API with `Authorization: Bearer <jwt>`; JWT lives in httpOnly cookie on the Next origin. Exception: file upload/download (short-lived signed token, direct to API).
- Every API route depends on `current_user` unless listed in `PUBLIC` in `backend/tests/test_auth.py` (test enforces). Frontend guards are UX only.
- Sensitive columns use `EncryptedText/JSON/Bytes`; audit log never stores their values.
- Audit actor comes from `db.info["actor"]` (set by `current_user`), NOT a contextvar (sync deps run in separate threadpool contexts).
- Grievance writes must set actor `(None, "complainant")` so audit cannot leak identity.
- Ports: web 3210, API 8210 (3000/8000 are used by other local projects on this machine).
- Build plan + data model: `C:\Users\karan\.claude\plans\pasted-content-id-a6bd-i-m-building-toasty-fog.md`.

## Further memories
- Versions and library choices: `mem:tech_stack`
- Run/test commands: `mem:suggested_commands`; done-criteria per task: `mem:task_completion`
- Code patterns for adding endpoints, pages, forms, strings: `mem:conventions`
