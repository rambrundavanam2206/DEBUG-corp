# DEBUGGER — Agreed Build Roadmap

Updated: 2026-11-24

This document records the agreed project plan. Read it when continuing development and update phase status with actual verification evidence. Do not mark a phase complete based only on implementation.

## Scope and constraints

- Build a real MVP within free-tier limits; no paid resource upgrades without explicit user approval.
- Input: project ZIP or public GitHub repository, error/logs, reproduction steps, expected behaviour.
- Main agent investigates and delegates to relevant frontend/backend/database specialists.
- Output: evidence-based diagnosis and ONE rectification prompt with file references and verification steps.
- User's local coding agent verifies current code, applies the fix, and runs tests. Accept follow-up errors and updated code.
- Initial focus: JavaScript/TypeScript and Python projects.
- Do not execute uploaded code on the server in this MVP. Live telemetry, dependency graphs and sandboxed fix validation are later scope.

## Phases

| Phase | Deliverables | Completion check | Status |
| --- | --- | --- | --- |
| 1. Foundation | Repository structure, React UI, FastAPI, Supabase login, database access policies | Login and frontend/backend connection work; access policies verified | Accepted — automated/API/RLS/CI passed; user reported all local manual checks passed (2026-11-24). |
| 2. Project input | ZIP upload, public GitHub import, error/reproduction form, file search/read | Sample project safely imports and source files can be read | Pending |
| 3. AI debugging | Main agent first; relevant sub-agents; Gemini/Groq integration | Known bugs produce useful diagnoses supported by evidence | Pending |
| 4. Results & follow-up | Rectification prompt, copy/download, history, progress, retry | Complete upload-to-diagnosis-to-prompt flow works | Pending |
| 5. Deployment | Vercel + Render free setup, limits, cleanup, end-to-end testing | Complete workflow passes on hosted site | Pending |

## Technology decisions

- Frontend: React, Vite, TypeScript, Tailwind CSS.
- Backend: Python, FastAPI, Pydantic.
- Agents: OpenAI Agents SDK with configurable Gemini/Groq integration; verify adapter and tool-calling compatibility.
- One API key per provider, shared by agents using that provider.
- Supabase Auth, PostgreSQL and private Storage with ownership-based access policies.
- Hosting: Vercel frontend, Render free web service backend, Supabase free-tier resources subject to account eligibility.
- Free MVP: bounded analysis tasks in the API service, persisted status/results, limited concurrency and explicit retry after interruptions. No separate paid Celery worker; Redis/Celery deferred.
- Quota exhaustion must produce a clear retry message; never silently switch to paid inference.
- Code: https://github.com/rambrundavanam2206/DEBUG-corp
- Supabase project reference: sdaxmrozbifrgcpycmap

## Credential handling

Never commit secret keys. Previously shared secrets must be rotated. Ask the user to enter replacement keys in backend environment settings when required; provide the exact location and variable names. The user agreed to supply them there. Frontend receives only public configuration.

## Continuation notes

The user authorized phased implementation and testing, continuing between phases without repeated approval within agreed scope. GitHub, Vercel and Render plugins are connected; Supabase project access is verified. Phase 1 implementation and evidence are recorded in docs/PHASE_1.md. Phase 1 is accepted as of 2026-11-24: automated/API/RLS/CI evidence plus user-reported local manual acceptance checks. Phase 2 is next; hosted deployment remains Phase 5.
