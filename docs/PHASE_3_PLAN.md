# Phase 3 — AI debugging implementation plan

Status: planned, not implemented. Phase 2 was accepted by the user on 2026-11-24.

## Goal

From an imported project and saved terminal error/problem, produce an evidence-based diagnosis, suggested reproduction steps, verification commands, and one consolidated rectification prompt. Imported source is inspected, never executed by the server. Phase 4 adds richer history, download/copy and follow-up flows.

## Build sequence

1. Provider configuration: backend-only Gemini/Groq credentials and explicit model identifiers. Use the OpenAI Agents SDK with provider-specific Chat Completions adapters after testing tool-calling/structured-output compatibility. No OpenAI API key is required for those adapters; disable SDK tracing to OpenAI.
2. Persist owned analysis records: project snapshot identity/commit and problem snapshot, state, timestamps, provider/model and bounded usage metadata, result/error. RLS ties every record to the authenticated owner. A changed problem or source requires a new analysis.
3. Read-only context tools: list files, bounded literal search and line-range reads from the imported bundle. Each tool remains project-scoped. Treat source, comments and pasted logs as untrusted data, not execution instructions.
4. Main investigator: start with the error and project inventory, inspect relevant code, and request missing context when necessary. Surface coverage limits and missing/local-only files; do not invent repository evidence.
5. Specialist delegation: invoke frontend, backend, database or general-language specialists only when relevant. C/C++ compiler errors use the general-language path. Specialists share the provider key, have bounded context/tools and return findings to the main investigator. No recursive specialist spawning.
6. Cross-check: validate referenced paths and line ranges against the exact source snapshot; require supporting excerpts. The main agent reconciles findings into one result. Invalid/missing evidence produces an explicit incomplete result or bounded repair attempt, not a fabricated confident answer.
7. Project UI: Analyze issue action, configuration/not-ready feedback, running state, bounded retry for interrupted/error states, root cause with linked evidence, suggested reproduction, clarifying questions and rectification prompt. Never label generated suggestions as verified execution.
8. Tests: fake-provider orchestration tests, tool isolation/bounds, injected instructions in code/logs, malformed output, provider failure/quota exhaustion, source mismatch, and known-bug fixtures. Finish with a real provider run on the user's C++ sample and manual UI acceptance.

## Free-tier controls

- One key per provider; both keys optional at startup, at least one configured provider required to run analysis.
- Proposed initial routing: Gemini primary; Groq fallback only when explicitly configured for free-tier use. A 429 can fall back once, otherwise stop with a retry message. No paid provider/model fallback.
- Model IDs are configuration, selected after checking provider availability, quotas and account eligibility. Never infer free billing from an API key.
- Bounded model calls, tool calls, source/context bytes, output tokens, concurrency and wall-clock time. No unlimited agent loop.
- Keep work in the FastAPI service and persist results/status; process interruption is recoverable via retry. No paid worker, Redis, or model fine-tuning.
- Provider errors and application logs must not reveal secrets. Source is sent only to the selected model provider; no source-bearing SDK traces.
- The user must rotate previously shared provider keys before use. Enter replacements in backend/.env locally, never chat, frontend variables or GitHub commits.

## Local provider prerequisites

Existing Supabase and GitHub configuration continues to work.

Planned backend environment names:

- GEMINI_API_KEY
- GROQ_API_KEY
- GEMINI_MODEL
- GROQ_MODEL
- AI_PRIMARY_PROVIDER
- AI_FALLBACK_ENABLED

Credentials go in backend/.env on the machine running FastAPI. Setting keys on the user's PC does not make them available to the assistant's workspace; assistant-side tests use mocks until securely configured, and real-provider tests can run on the user's PC. Never request keys in chat.

## Acceptance

- The supplied TICTAC.CPP Queue sample yields useful findings grounded in actual lines (the local compiler log calls it d.cpp).
- Missing semicolons, missing parenthesis, wrong stream operator and missing closing brace are detected from source, without claiming the code was compiled.
- A local filename/repository mismatch is explained rather than silently assumed.
- Larger JS/TS/Python fixtures cause only relevant specialist calls.
- Unsupported evidence, insufficient context, missing keys, provider quota failure and timeouts have clear UI states.
- Ownership and bounded execution tests pass, then the user verifies one real analysis end to end.

## Provider references checked during planning

- https://ai.google.dev/gemini-api/docs/openai
- https://console.groq.com/docs/openai
- https://openai.github.io/openai-agents-python/models/

Compatibility documentation is not a substitute for testing the selected live model.
