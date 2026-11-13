# Done criteria for any task

1. `uv run --directory backend pytest -q` green.
2. `pnpm typecheck` and `pnpm lint` clean in `frontend/`.
3. `pnpm test:e2e` green: axe zero violations on every listed page in light/dark/contrast + Hindi, keyboard and flow specs pass. New pages must be listed in `tests/a11y.spec.ts` first.
4. New UI strings exist in both message files.
5. If models changed: re-run `uv run python -m app.seed` (and extend the seed so the new screens have demo data).
6. Commit on the module branch; never push or deploy without the user's go-ahead.
