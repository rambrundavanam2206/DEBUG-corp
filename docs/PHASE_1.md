# Phase 1 — Foundation

Implementation date: 2026-11-24. Scope: authentication, protected dashboard, backend integration, and database ownership. No AI calls or paid services.

## Status

**Implemented and automated checks passed.** Manual browser visual QA and real email-confirmation delivery remain pending. Do not describe the hosted product or the complete five-phase project as finished.

## Implemented

- React/Vite/TypeScript/Tailwind UI: signup, login, confirmation state/callback, protected projects dashboard, account page, build-progress page and 404.
- Session restoration, logout, expired-session handling, request timeout and backend retry UI.
- Real empty state; no invented project or analysis results. Imports and analysis are explicitly planned.
- FastAPI health, verified current user and owned projects endpoints.
- Configuration validation, explicit CORS, non-cached responses and sanitized upstream errors.
- Backend calls Supabase Auth to verify access tokens; user JWT is forwarded to PostgREST.
- Optional profiles schema and projects schema, indexes, updated timestamps, RLS and explicit grants.
- No auth-user trigger, privileged profile function, service-role key, or model provider secret.
- Lockfiles, environment templates, local development launcher and GitHub Actions checks.

## Database applied

Project: `sdaxmrozbifrgcpycmap` (DEBUG-corp).
Migration: `20261124141224_phase_1_foundation.sql`.
This file's version matches the hosted migration history. Do not apply it again to that project.

RLS requires the JWT subject to match `profiles.id` or `projects.owner_id`. UPDATE includes USING and WITH CHECK. Anonymous/public roles have no table access. Profiles are optional and not automatically populated; profile editing is deferred.

## Verification evidence

| Check | Result |
| --- | --- |
| TypeScript + Vite production build | Passed; one non-blocking bundle-size advisory |
| Frontend integration tests | 8 passed: protection, restoration loading, password mismatch, confirmation state, login errors, empty state, offline retry and invalid session |
| Backend tests | 14 passed: health, auth, current user, JWT forwarding, owner filter, upstream errors, payload validation, CORS, secret-key rejection |
| Hosted SQL RLS checks | Passed; two synthetic users, CRUD isolation, owner transfer prevention, profile isolation and anonymous denial |
| Live Supabase password login | Passed with two temporary confirmed QA users |
| FastAPI + live Supabase Auth | Passed; correct identity for both access tokens |
| FastAPI + live PostgREST | Passed; only owner's project returned |
| Live REST protection | Cross-user updates and owner reassignment blocked; anonymous reads denied |
| Live refresh and logout | Refresh produced accepted token; logout revoked refresh |
| Supabase security advisor after migration | No findings |
| Test-account cleanup | Temporary QA users deleted; associated records cascade deleted |
| Real email confirmation delivery | Pending user-controlled email and Auth URL/email configuration |
| Browser visual/mobile QA | Blocked by managed preview startup: Node uv_interface_addresses error |
| GitHub Actions | Configured; remote run result must be checked after push |

The live API check used temporary test accounts provisioned only for validation; it does not prove the signup email delivery path. SQL ownership fixtures were rolled back. No test password or access token belongs in the repository.

## Remaining acceptance checks

1. In Supabase Authentication URL Configuration, allow the actual local/preview callback URL (`http://localhost:5173/auth/callback` for local development). Preserve existing production settings. See README.
2. Use an email you control to sign up, open its confirmation link, and sign in. Default email delivery may require SMTP configuration. Never disable confirmation solely to make the test pass.
3. Verify dashboard refresh, navigation, sign out, and responsive layout in a working browser preview. The current environment's preview infrastructure failed before a browser could open it; browser rendering is not claimed as verified.
4. Check GitHub Actions results once the branch is published.

## Security and operational limits

- Logout removes the browser session and revokes refresh tokens. Already-issued access JWTs can remain valid until expiry; immediate revocation is not implemented.
- The root health endpoint is process liveness, not a guarantee that Supabase is reachable.
- At most 100 recent projects are listed. Pagination and project operations belong to Phase 2.
- Previously exposed backend/provider secrets must be rotated before later use. Phase 1 did not use them.
- Free deployment and model quotas are respected; hosting deployment remains Phase 5.

## Next phase

Project inputs: safe ZIP handling, public GitHub imports, problem form and bounded source file listing/search/reading. Do not execute uploaded code.
