import asyncio
import json
from datetime import datetime, timedelta, timezone

from agents.exceptions import MaxTurnsExceeded
from fastapi import HTTPException

from app.ai.context import Investigation, redact, snapshot_hash
from app.ai.investigator import investigate, rectification_prompt
from app.ai.providers import configuration, provider_model
from app.ai.schemas import AnalysisFailure
from app.services.workspace import Workspace

PROBLEM_FIELDS = ("problem", "command", "expected", "reproduction")


class Analyses:
    def __init__(self, request, user):
        self.workspace = Workspace(request, user)
        self.settings = request.app.state.settings
        self.slots = request.app.state.analysis_slots
        # Test injection is server-side only, never a user-controlled provider URL.
        self.factory = getattr(request.app.state, "analysis_model_factory", provider_model)

    async def recover(self, project_id):
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
        await self.workspace.rest(
            "PATCH",
            "analyses",
            params={
                "owner_id": f"eq.{self.workspace.user.id}",
                "status": "eq.running",
                "created_at": f"lt.{cutoff}",
            },
            json={
                "status": "failed",
                "error": "Analysis was interrupted. Retry to start a new bounded run.",
                "error_code": "interrupted",
            },
        )

    async def latest(self, project_id):
        project = await self.workspace.get(project_id)
        await self.recover(project_id)
        rows = await self.workspace.rest(
            "GET",
            "analyses",
            params={"project_id": f"eq.{project_id}", "order": "created_at.desc", "limit": "1"},
        )
        if not rows:
            return {"analysis": None}
        row = rows[0]
        row["stale"] = False
        if row["status"] in ("completed", "needs_context"):
            if project["status"] != "ready":
                row["stale"] = True
            else:
                files = await self.workspace.bundle(project_id)
                row["stale"] = (
                    snapshot_hash(files, {k: project[k] for k in PROBLEM_FIELDS})
                    != row["source_hash"]
                )
        return {"analysis": row}

    async def start(self, project_id):
        project = await self.workspace.get(project_id)
        if project["status"] != "ready":
            raise HTTPException(409, "Import the project before analysing it.")
        if not configuration(self.settings)["ready"]:
            raise HTTPException(503, configuration(self.settings)["message"])
        if self.slots.locked():
            raise HTTPException(429, "Another analysis is running. Please retry shortly.")
        async with self.slots:
            await self.recover(project_id)
            files = await self.workspace.bundle(project_id)
            problem = {k: project[k] for k in PROBLEM_FIELDS}
            digest = snapshot_hash(files, problem)
            state = Investigation({path: redact(content) for path, content in files.items()})
            if any(state.files[p] != files[p] for p in files):
                state.limitations.append(
                    "Potential credential values were redacted before analysis."
                )
            row = (
                await self.workspace.rest(
                    "POST",
                    "analyses",
                    json={
                        "project_id": str(project_id),
                        "owner_id": self.workspace.user.id,
                        "source_hash": digest,
                        "commit_sha": project["commit_sha"],
                        "problem_snapshot": {k: redact(v) for k, v in problem.items()},
                        "status": "running",
                    },
                )
            )[0]
            values = {}
            try:
                async with asyncio.timeout(110):
                    async with self.factory(self.settings, state) as model:
                        result = await investigate(model, state, problem)
                payload = result.model_dump()
                payload["rectification_prompt"] = rectification_prompt(
                    result, digest, project["commit_sha"]
                )
                payload["execution_verified"] = False
                payload["evidence_check"] = (
                    "Referenced paths, line ranges and exact excerpts matched the inspected snapshot. Diagnosis remains AI-generated."
                )
                if len(json.dumps(payload).encode()) > 100000:
                    raise AnalysisFailure(
                        "Result exceeded the saved-output limit.", "invalid_output"
                    )
                values = {
                    "status": "completed" if result.findings else "needs_context",
                    "result": payload,
                    "error": "",
                    "error_code": "",
                }
            except AnalysisFailure as exc:
                values = {"status": "failed", "error": str(exc), "error_code": exc.code}
            except (TimeoutError, MaxTurnsExceeded):
                values = {
                    "status": "failed",
                    "error": "Analysis reached its time or turn limit. Narrow the problem and retry.",
                    "error_code": "budget",
                }
            except Exception:
                # Provider bodies and SDK errors can contain source or credentials. Never echo them.
                values = {
                    "status": "failed",
                    "error": "Analysis could not complete. Check provider/model configuration and retry.",
                    "error_code": "analysis_failed",
                }
            values.update(provider=state.provider_used, model=state.model_used, usage=state.stats())
            updated = await self.workspace.rest(
                "PATCH",
                "analyses",
                params={"id": f"eq.{row['id']}", "status": "eq.running"},
                json=values,
            )
            if not updated:
                raise HTTPException(409, "Analysis state changed. Refresh the project.")
            current = await self.workspace.get(project_id)
            return {
                "analysis": {**updated[0], "stale": current["updated_at"] != project["updated_at"]}
            }
