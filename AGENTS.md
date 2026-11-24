# DEBUGGER development

Read ROADMAP.md and docs/PHASE_1.md before continuing. Keep verified status separate from untested implementation. Work on one agreed phase at a time.

- React/Vite/TypeScript frontend; Python/FastAPI backend; Supabase Auth and PostgreSQL.
- Free-tier MVP only. No paid upgrades or automatic paid model fallback.
- Never commit .env files, provider keys, backend secrets, QA passwords, or access tokens.
- Phase 1 uses a Supabase publishable key and a user's access token, never a service-role key.
- Authenticate on the server and enforce ownership through RLS. Never trust user_metadata for authorization.
- Never run uploaded project code on the server in this MVP.
- Preserve user changes and the roadmap. Record verification evidence and pending checks.
- Tests: npm --prefix frontend test; npm run build; uv run --directory backend --locked pytest.
- Live database isolation tests: supabase/tests/ownership.sql (transaction, rolled back).
- Deployment is Phase 5; do not publish a partial phase as a finished product.
