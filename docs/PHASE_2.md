# Phase 2 — Project input

Implemented 2026-11-24. Status: automated and live API verification complete; local browser acceptance pending. No AI diagnosis or hosting deployment in this phase.

## User flow

Projects → New project → public GitHub URL or ZIP → terminal error/problem → Import project → private project workspace. Project name and problem are required. Branch, command, expected behaviour and reproduction steps are optional. Reproduction suggestions belong to Phase 3.

The workspace supports editable problem details, import status/retry, a filterable source-path list, read-only source with line numbers and 200-line paging, filename/content search (first 100 matches), skipped-file reasons, and confirmed deletion.

## Implementation and limits

- Imports run within a bounded request: 120-second import deadline and two imports per API process. No paid worker or Redis.
- A project is created before import. Pending/failed records can be retried without making another project; ZIP retries require selecting the file again.
- An optimistic database claim prevents overlapping imports/deletion. Interrupted importing/deleting leases can be reclaimed after three minutes.
- Public GitHub metadata resolves the chosen/default branch to an exact commit. Archive downloads use fixed GitHub hosts, no credentials, no redirects, and a streamed size bound. Rate limits return a retry message.
- Limits: 10 MiB compressed, 30 MiB expanded, 3,000 archive entries, 500 stored source files, 500 KiB per source file, three projects per account (including pending/failed).
- C/C++ including uppercase `.CPP`, JS/TS, Python and other common UTF-8 text formats are supported. This is source ingestion, not language-specific AI validation.
- No extraction to disk and no execution of imported commands/code. Reject unsafe paths, symlinks/special files, encrypted/nested archives and duplicate case-conflicting paths.
- Skip generated/dependency directories, known credential filenames, unsupported/binary/non-UTF-8 files and oversized individual files. Filtering is not a guarantee that every secret is removed.
- Source text is stored as one JSON bundle (maximum 45 MiB after serialization) in the private `project-sources` bucket. File metadata and skipped reasons live in the project record; bundling avoids hundreds of Storage requests per small import.
- All operations use verified user JWTs and the publishable key. RLS protects projects and Storage. No service-role key is needed.
- Storage objects have one fixed path per project. Delete removes Storage through its API before deleting the project record; a database guard prevents accidental orphaning. Failed cleanup remains retryable.
- JSON inputs are bounded before parsing; ZIP is streamed and bounded in its authenticated route. File viewer escapes source text; search treats input as literal text, not regex.

## Database migrations

Already applied to `sdaxmrozbifrgcpycmap`; do not manually reapply there:

- `20261124174201_phase_2_project_input.sql`
- `20261124174606_phase_2_storage_cleanup_guard.sql`
- `20261124175033_phase_2_storage_policy_qualification.sql`

The final migration qualifies outer Storage object names in correlated ownership checks. Live tests caught this issue before release. A CLI telemetry attempt was blocked by automatic review; migrations were applied with the connected Supabase tool and saved using the server's migration versions.

## Verification

- Frontend: 13 tests, including optional reproduction, auto import, quota errors, safe text rendering/search navigation, problem save, deletion confirmation, and ZIP retry.
- Backend: 44 tests, including archive safety/limits, GitHub host allowlist and pinned download, import/read/search/edit/delete, failure recovery, auth and ownership miss handling.
- TypeScript + production build passed. Existing non-blocking bundle-size advisory remains.
- Live importer fetched `rambrundavanam2206/TIC-TAC-TOE`, branch `master`, commit `90c3bb05ff7aebeb1fcd8b66abb17609b25b509f`; imported `TICTAC.CPP`. Its Queue code matches the supplied compiler log despite the local filename `d.cpp`.
- Real temporary authenticated accounts verified GitHub and ZIP imports into private Storage, reads/search, saved edits, cross-user access denial and project/file deletion.
- SQL ownership regression and Phase 2 quota/Storage/identity/orphan checks passed using rolled-back fixtures. Storage deletes are tested through the Storage API, not direct SQL.
- Security advisor: no database/Storage policy findings; existing Auth setting warns that leaked-password protection is disabled. [Supabase guidance](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection). No paid/auth setting was changed.
- Managed preview failed before browser startup with Node `uv_interface_addresses` / `ERR_SYSTEM_ERROR`; status confirmed stopped. Browser visual/mobile QA is unverified and requires local acceptance.
- A transient Auth 503 occurred during a later QA cleanup request; deletion was retried separately.
- GitHub Actions status is recorded after publishing the branch.

## Local manual acceptance

Use the same frontend/backend environment configuration as Phase 1. No model keys needed.

1. Sign in → Projects → New project.
2. Enter `Tic Tac Toe`, the supplied public repo URL, and the terminal error; leave reproduction empty. Import.
3. Confirm ready status, exact commit and `TICTAC.CPP` in the source list.
4. Open the file, search `Queue` or `cout`, and open a matching line.
5. Edit the problem details, save, refresh and reopen; confirm persistence.
6. Import a small ZIP. Confirm `.env`/dependency files are skipped, and invalid ZIPs produce clear errors with retry.
7. Verify the third-project limit and fourth-project rejection. Delete a project; confirm it disappears and a new slot becomes available.
8. Check mobile layout, source scrolling, logout protection and existing login flow.

Phase 2 is accepted only after the manual checks pass. AI analysis and rectification prompts remain Phase 3.
