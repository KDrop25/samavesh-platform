# Conventions

## Backend
- New table: class in `app/models/<area>.py` inheriting `Base` (gives `id`, `created_at`), export in `app/models/__init__.py`. Add `__audited__ = True` for profiles, plans, decisions, grievances, compliance.
- Business failures: `raise AppError(status, "snake_case_code")`; the code is the i18n key suffix (`error.<code>` in both message files).
- Routers: `APIRouter(dependencies=[Depends(require_roles(...))])` for role-wide gates; object-level checks in `app/permissions.py`. Pydantic schemas live beside their router; request model field order = form field order (drives error order).
- Pure rules (overdue, planned-vs-delivered, working days, summaries) go in `app/rules/` with no DB/session access, each with a pytest test.
- Never put disability or grievance content in emails or audit values.
- `ponytail:` comments mark deliberate simplifications with their ceiling.

## Frontend
- Server Components fetch with `api()`; pages call `requireUser(...roles)`.
- Mutations: Server Action in `app/actions.ts` with signature `(state: FormState, form: FormData)`, returning `failure(t, result, form)` or `{ ok: true, message }`; render with `<Form>` + `<Field>`/`<RadioGroup>` from `components/Form.tsx` (handles error summary focus, aria wiring, value echo). Do not hand-roll forms.
- All visible text via `t("key")`; add every key to BOTH `messages/en.json` and `messages/hi.json`. Field label keys are `field.<api_field_name>`.
- Each page: `export const generateMetadata = titled("x.title")`, exactly one `<h1>`.
- Colours only through tokens (`bg-bg text-fg text-muted bg-surface border-border text-danger ...`) so all three themes work; sizes in rem.
- New page => add its path to `PUBLIC_PAGES`/`PAGES_BY_ROLE` in `tests/a11y.spec.ts` and to `NAV`/`SECTIONS` where relevant.
- In Playwright, scope alert/status lookups to `main` (Next's route announcer is also `role="alert"`).
