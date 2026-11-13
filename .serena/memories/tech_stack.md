# Tech stack

- Backend: Python 3.12 (uv, `.python-version`), FastAPI 0.162 / Starlette 1.x, SQLAlchemy 2.1 (sync sessions), Pydantic 2.14, pydantic-settings, PyJWT, `cryptography` (AES-256-GCM), psycopg 3, Alembic. Tests: pytest + httpx2 (`TestClient`).
- DB: SQLite locally, PostgreSQL in prod (Neon). Enums stored as VARCHAR (`native_enum=False`); all datetimes via `UTCDateTime` (tz-aware on both).
- Frontend: Next.js 16.4 (App Router, Turbopack, `proxy.ts` replaces middleware), React 19, TypeScript, Tailwind 4 (`@theme inline` + CSS variables, no config file), pnpm. No UI/component, i18n, or validation library by design.
- E2E: `@playwright/test` + `@axe-core/playwright`.
- Next docs are bundled: read `frontend/node_modules/next/dist/docs/` before using a Next API (see `frontend/AGENTS.md`).
- Gotchas: `email-validator` rejects `.test`/reserved domains (use `example.com`); `hashlib.scrypt` needs `maxmem` raised; Alembic migrations are generated once before deploy - dev/test use `create_all` via `app.seed`.
