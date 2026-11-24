# DEBUGGER

A private workspace for investigating software errors and producing a rectification prompt for a local coding agent.

**Current implementation: Phase 1 foundation.** Email authentication, protected dashboard, user-scoped FastAPI endpoints, and database ownership policies are implemented. Imports and AI analysis are planned, not simulated.

- [Agreed roadmap](ROADMAP.md)
- [Phase 1 implementation and verification](docs/PHASE_1.md)

## Stack

React + Vite + TypeScript + Tailwind; Python + FastAPI; Supabase Auth + PostgreSQL. Planned model providers: Gemini/Groq, one key per provider. No model key or Supabase backend secret is needed for Phase 1.

## Run locally

Prerequisites: Git, Node.js 24, Python 3.12, and uv. Commands below run at the repository root.

```sh
npm ci
npm --prefix frontend ci
uv sync --project backend --locked
```

Copy `frontend/.env.example` to `frontend/.env.local` and `backend/.env.example` to `backend/.env`. Set your Supabase project URL and **publishable** key in both. Leave `VITE_API_URL` empty for the Vite development proxy. Do not put privileged credentials in any `VITE_` variable.

For a fresh Supabase project, apply `supabase/migrations/20261124141224_phase_1_foundation.sql` via your SQL editor/migration workflow. This migration is already applied to the connected DEBUG-corp project; do not reapply it there.

In Supabase **Authentication → URL Configuration**, set the development Site URL to `http://localhost:5173` and allow `http://localhost:5173/auth/callback` as a redirect. Preserve other required URLs. Keep email confirmation enabled. On hosted previews, use the exact preview origin instead of localhost. Confirm email provider delivery/SMTP settings before inviting real users. Free default email delivery can be restricted.

```sh
npm run dev
```

Open `http://localhost:5173`. FastAPI runs on `http://127.0.0.1:8000`; API documentation is at `/docs`. The development launcher stops both processes when interrupted. For separate terminals:

```sh
# Terminal 1
cd backend
uv run --locked uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
# Terminal 2, from repository root
npm --prefix frontend run dev
```

Use a real email you control for signup and confirmation. Do not share passwords in chat. Email-confirmed accounts can sign in. Page refresh restores the session; sign out clears the browser session. Supabase access JWTs may remain valid until expiry after logout; refresh tokens are revoked. This foundation does not claim immediate revocation of already-issued access tokens.

## API

| Route | Access | Purpose |
| --- | --- | --- |
| `GET /health` | Public | Process liveness; no upstream details |
| `GET /api/me` | Bearer token | Auth-verified ID/email |
| `GET /api/projects` | Bearer token | Up to 100 recent owned project records |

The backend verifies tokens against Supabase Auth `/auth/v1/user`. It forwards the user's JWT to PostgREST so RLS still applies. Auth outages return 503; invalid sessions return 401. No request token or password is logged by the app. CORS allows only explicitly configured origins. `profiles` is an optional schema foundation; profile editing and automatic profile creation are not implemented.

## Checks

```sh
npm --prefix frontend test
npm run build
uv run --directory backend --locked pytest -q
python scripts/check_secrets.py
```

`backend/uv.lock` and the npm lockfiles pin installations. GitHub Actions runs tests and builds without production credentials. `supabase/tests/ownership.sql` exercises real RLS with two synthetic users, including cross-user read/update/delete and ownership reassignment attempts; it rolls back all fixtures. Run it with an administrative SQL connection in a project where the migration is applied.

## Free-tier constraints

Phase 1 creates no paid hosting resources. Deployment is a later phase. The planned free MVP has bounded tasks in the API process and persisted status/results, not a separate paid Celery worker. Interrupted tasks will need retry. Free-tier usage and email/model quotas still apply. User code is never executed on the server in the MVP.

## Secret handling

Previously shared provider/backend secrets must be rotated. Enter replacements in backend environment settings only when a later phase needs them. Never put secrets in source code, screenshots, logs, issues, or pull requests. `.env.example` files are placeholders only.
