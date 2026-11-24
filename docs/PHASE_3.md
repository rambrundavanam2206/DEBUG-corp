# Phase 3 — AI debugging

Status: implementation and automated verification complete; real-provider diagnosis quality and local browser acceptance pending. Do not mark this phase accepted until a real configured provider passes the user checklist.

## Implemented

- Authenticated Analyze issue action for imported projects; missing-config, running, failed, needs-context and completed states.
- OpenAI Agents SDK 0.26.0 with explicit Gemini/Groq Chat Completions clients. No OpenAI key, hosted tools, remote execution or OpenAI tracing. SDK/provider automatic retries are disabled.
- Main investigator with read-only list/search/line-range tools. The available specialists depend on source types; the main agent chooses whether to consult them. Specialists cannot delegate recursively.
- Up to two distinct specialist calls per investigation, sharing the same provider credentials and total budgets. C/C++ uses the general specialist when needed.
- JSON output parsed into bounded Pydantic models. Every finding requires actual paths, previously read line ranges and exact multiline source quotes. Invalid evidence or malformed output becomes a saved failure, not a published diagnosis.
- Source and logs are treated as untrusted data. No shell/network/edit tools are exposed. Known credential patterns are redacted while retaining line numbers; filtering cannot detect every secret.
- One consolidated rectification prompt assembled from accepted findings, suggested reproduction and local verification steps. Explicitly states that code was not executed/compiled/tested.
- Durable analysis records with RLS, source/problem snapshot hash, commit, provider/model, usage counters, result/error and timestamps. Source/problem changes mark old results stale.
- Status restoration/polling, bounded retry, evidence links into the source viewer, questions when context is insufficient, and read-only prompt text. Full history, copy/download polish and follow-up conversations remain Phase 4.

## Limits and recovery

- 12 total model attempts (including fallback), 18 tool calls, 48,000 bytes of tool output, 100,000 bytes of serialized system/input context per model call (plus fixed tool schemas).
- 3,000 output tokens per model call; main run at most seven turns, specialist run at most three.
- Reads: at most 120 complete lines and 8,000 source bytes per call. Search returns up to 20 literal matches; list returns 40 paths/page.
- 110-second investigation deadline; 25-second provider request timeout. Budget exhaustion is retryable with a more focused problem, not an unlimited continuation.
- One analysis at a time per API process and one running record per owner across processes. Database limits: 10 attempts/account/rolling 24 hours and 30 stored analyses/project; failed attempts also count. No direct analysis deletion endpoint in Phase 3.
- Interrupted running records older than three minutes are marked failed on the next analysis read/start. No durable background worker or automatic restart/resume.
- Fallback is off by default. When enabled, only a configured secondary provider can receive one failover on quota/network/server failure. Authentication/configuration errors do not trigger provider hopping.
- AI_FREE_TIER_CONFIRMED is operator acknowledgement, not an API billing check or hard provider spending cap. Both enabled accounts/models must actually be free-tier eligible; no paid resources/upgrades are provisioned.

## Configure on your PC

Keep existing Supabase values in **backend/.env**. Add fresh provider credentials there, never in GitHub, frontend variables or chat.

Minimal Gemini setup:

```dotenv
GEMINI_API_KEY=YOUR_FRESH_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
AI_PRIMARY_PROVIDER=gemini
AI_FALLBACK_ENABLED=false
AI_FREE_TIER_CONFIRMED=true
```

Only set the confirmation flag after checking your provider account/model eligibility. The model above is a documentation-verified starting candidate, not a live-tested quality guarantee. Gemini's official pricing listed free standard input/output and the model page listed function calling on 2026-11-24; quotas/account access can differ.

For Groq-only operation, set GROQ_API_KEY, GROQ_MODEL to a currently available function-calling text model from your account, and AI_PRIMARY_PROVIDER=groq. Do not assume an older model name still has free-tier access. For fallback, configure both providers/models and set AI_FALLBACK_ENABLED=true after confirming eligibility for both.

From the repository root:

```bash
uv sync --project backend --locked
uv run --directory backend --locked python scripts/check_ai.py
npm run dev
```

The first script checks configuration without inference and never prints keys. For an explicitly requested live synthetic C++ smoke test:

```bash
uv run --directory backend --locked python scripts/check_ai.py --live
```

This sends only the script's small synthetic fixture to the configured provider, validates returned evidence, and displays the result for quality review. A successful request alone does not prove every diagnosis is correct.

Restart the backend after changing environment values. Keys on the user's PC are not automatically available to the assistant's workspace. This workspace's configuration check reported no configured AI providers; no old/shared provider key was reused.

## Database

Migration `20261124181506_phase_3_analysis_records.sql` is already applied to the connected DEBUG-corp Supabase project. Do not reapply manually there. Project deletion cascades to owned analysis records.

## Verification evidence

- 70 backend tests passed, including existing phases, SDK tool delegation, exact evidence checks, malformed responses, missing files, source/tool/model budgets, mocked quota fallback, redaction, unknown-shell-tool failure, timeouts, API persistence and stale results.
- 18 frontend tests passed, including configuration gating, result/evidence rendering, source navigation, stale warning, needs-context response and quota failure.
- Actual Gemini/Groq Chat Completions adapter code tested with mocked HTTP transports through a full tool-call/result round trip. No real Gemini/Groq inference was performed.
- Known-bug fixtures use scripted responses to test orchestration/validation; they do not establish live-model reasoning quality.
- Live SQL checks passed: cross-user/anonymous denial, immutable snapshots, one-running-analysis constraint, daily quota and project-deletion cascade. Fixtures rolled back.
- TypeScript + production build passed; non-blocking bundle-size advisory remains.
- Security advisor: no analysis-table/RLS findings. Existing Auth leaked-password-protection warning remains; no paid/auth setting was changed. https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection
- Live Supabase API integration passed with a scripted SDK provider: actual GitHub import → investigation/evidence validation → saved result → reload → cross-user denial → changed-problem stale detection → project/source/analysis cleanup. No real model inference was performed. Temporary users and source objects were removed; sessions revoked.
- Browser visual/mobile QA not performed: managed preview infrastructure previously failed at startup with uv_interface_addresses and there is no evidence of recovery. User local acceptance is required.
- GitHub CI passed on implementation commit `71ba4e4`: backend, frontend and credential checks. Run: https://github.com/rambrundavanam2206/DEBUG-corp/actions/runs/45459930180 . The initially published lock file was incomplete; it was restored byte-for-byte from the tested local version before this successful run.

Injection tests verify the tool boundary and prompt/data separation; they cannot guarantee that any model is immune to prompt injection. Evidence validation checks reference integrity, not the semantic correctness of a suggested fix.

## Local acceptance checklist

1. Configure a fresh provider key, model and free-tier flag; restart backend. Configuration check should report ready without showing credentials.
2. Open the imported Tic Tac Toe project and save the supplied terminal error. Click Analyze issue.
3. Verify real findings for missing semicolons, missing condition parenthesis, incorrect cout operator and missing closing brace. Check all evidence against TICTAC.CPP. The d.cpp filename mismatch should be explained, not silently ignored.
4. Open an evidence link; check that the correct file and line appear.
5. Inspect suggested reproduction/verification and the rectification prompt. No claim that the server compiled or fixed the project should appear.
6. Refresh/reopen; confirm the result persists. Edit/save the error; confirm a stale-result warning until a new analysis is run.
7. Check a missing-key configuration and provider quota/error response. Neither should fabricate a successful result. Retry only after fixing configuration or waiting for quota.
8. Test a JS/TS/Python sample requiring another relevant subsystem; inspect reported specialist usage and diagnosis quality. Specialists are optional, not forced for every issue.
9. Check mobile layout and existing login/import/search/delete flows.

## References checked

- https://openai.github.io/openai-agents-python/models/
- https://openai.github.io/openai-agents-python/tools/
- https://ai.google.dev/gemini-api/docs/openai
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite
- https://ai.google.dev/gemini-api/docs/pricing
- https://console.groq.com/docs/openai
- https://console.groq.com/docs/models
- https://console.groq.com/docs/rate-limits
