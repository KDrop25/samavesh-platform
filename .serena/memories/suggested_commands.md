# Commands (Windows, PowerShell)

Backend (run from `backend/` or pass `--directory backend`):
- `uv run python -m app.seed` - DROP + recreate all tables, load demo data (password `Samavesh-Demo-2026`)
- `uv run uvicorn app.main:app --port 8210 --reload --reload-dir app`
- `uv run pytest -q` ; Postgres run: set `TEST_DATABASE_URL`

Frontend (from `frontend/`):
- `pnpm dev` (port 3210) ; `pnpm typecheck` ; `pnpm lint`
- `pnpm test:e2e` (all) ; `pnpm test:a11y` ; `pnpm test:keyboard` - Playwright starts/reuses both servers
- After adding routes: `pnpm exec next typegen` so `PageProps<"/path">` resolves

Shell notes: PowerShell 5.1 has no `&&`; use `;`. `pnpm pkg set` cannot set script names containing `:`.
