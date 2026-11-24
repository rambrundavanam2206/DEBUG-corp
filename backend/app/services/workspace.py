import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services.imports import MAX_BUNDLE, download_github, github_repo, inspect_zip


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_type: str = Field(pattern="^(zip|github)$")
    repo_url: str = Field(default="", max_length=300)
    branch: str = Field(default="", max_length=200)
    problem: str = Field(min_length=1, max_length=30000)
    command: str = Field(default="", max_length=1000)
    expected: str = Field(default="", max_length=5000)
    reproduction: str = Field(default="", max_length=5000)


class ProblemInput(BaseModel):
    problem: str = Field(min_length=1, max_length=30000)
    command: str = Field(default="", max_length=1000)
    expected: str = Field(default="", max_length=5000)
    reproduction: str = Field(default="", max_length=5000)


class Workspace:
    def __init__(self, request, user):
        self.http = request.app.state.http
        self.base = request.app.state.settings.supabase_url
        self.user = user
        self.headers = {
            "apikey": request.app.state.settings.supabase_publishable_key,
            "Authorization": f"Bearer {user.token}",
            "Prefer": "return=representation",
        }

    async def rest(self, method, path="projects", **kwargs):
        try:
            response = await self.http.request(
                method, f"{self.base}/rest/v1/{path}", headers=self.headers, **kwargs
            )
        except httpx.RequestError:
            raise HTTPException(503, "Project storage is unavailable. Please retry.") from None
        if response.status_code in (401, 403):
            raise HTTPException(403, "Project access denied or session expired.")
        if response.status_code >= 400:
            if "project_limit" in response.text:
                raise HTTPException(
                    409, "You can keep up to 3 projects. Delete one before importing another."
                )
            raise HTTPException(503, "Project operation failed. Please retry.")
        return response.json() if response.content else None

    async def get(self, project_id):
        rows = await self.rest(
            "GET",
            params={
                "id": f"eq.{project_id}",
                "owner_id": f"eq.{self.user.id}",
                "select": "*",
                "limit": "1",
            },
        )
        if not rows:
            raise HTTPException(404, "Project not found.")
        return rows[0]

    async def create(self, data):
        if not data.name.strip() or not data.problem.strip():
            raise HTTPException(422, "Project name and problem description are required.")
        if data.source_type == "github":
            github_repo(data.repo_url)
        return (
            await self.rest(
                "POST",
                json={**data.model_dump(), "name": data.name.strip(), "owner_id": self.user.id},
            )
        )[0]

    async def patch(self, project_id, values, extra=None):
        return await self.rest(
            "PATCH",
            params={"id": f"eq.{project_id}", "owner_id": f"eq.{self.user.id}", **(extra or {})},
            json=values,
        )

    def object_path(self, project_id):
        return f"{self.user.id}/{project_id}/source.json"

    async def remove_object(self, project_id):
        try:
            response = await self.http.request(
                "DELETE",
                f"{self.base}/storage/v1/object/project-sources",
                headers=self.headers,
                json={"prefixes": [self.object_path(project_id)]},
            )
        except httpx.RequestError:
            raise HTTPException(503, "File cleanup failed. Retry deletion.") from None
        if response.status_code not in (200, 204, 404):
            raise HTTPException(503, "File cleanup failed. Retry deletion.")

    async def claim(self, project_id, action):
        project = await self.get(project_id)
        stamp = datetime.now(timezone.utc)
        if (
            project["status"] in ("importing", "deleting")
            and project.get("operation_started")
            and datetime.fromisoformat(project["operation_started"]) > stamp - timedelta(minutes=3)
        ):
            raise HTTPException(
                409, "An operation is in progress. Retry after three minutes if it was interrupted."
            )
        if action == "importing" and project["status"] == "ready":
            raise HTTPException(409, "This project is already imported.")
        rows = await self.patch(
            project_id,
            {"status": action, "operation_started": stamp.isoformat(), "import_error": ""},
            {"updated_at": f"eq.{project['updated_at']}"},
        )
        if not rows:
            raise HTTPException(409, "Project changed. Refresh and retry.")
        return rows[0]

    async def import_project(self, project_id, archive=None):
        project = await self.claim(project_id, "importing")
        try:
            async with asyncio.timeout(120):
                branch, commit = project["branch"], ""
                if project["source_type"] == "github":
                    archive, branch, commit = await download_github(project["repo_url"], branch)
                elif archive is None:
                    raise HTTPException(422, "Select a ZIP file to import or retry.")
                files, skipped = await run_in_threadpool(inspect_zip, archive)
                bundle = json.dumps(files, ensure_ascii=False).encode()
                if len(bundle) > MAX_BUNDLE:
                    raise HTTPException(413, "Source bundle is too large.")
                manifest = [
                    {
                        "path": path,
                        "size": len(content.encode()),
                        "lines": len(content.splitlines()),
                    }
                    for path, content in sorted(files.items())
                ]
                response = await self.http.post(
                    f"{self.base}/storage/v1/object/project-sources/{self.object_path(project_id)}",
                    headers={
                        **self.headers,
                        "Content-Type": "application/json",
                        "x-upsert": "true",
                    },
                    content=bundle,
                    timeout=45,
                )
                if response.status_code not in (200, 201):
                    raise HTTPException(503, "Source storage failed. Retry the import.")
                await self.patch(
                    project_id,
                    {
                        "status": "ready",
                        "manifest": manifest,
                        "skipped": skipped,
                        "branch": branch,
                        "commit_sha": commit,
                        "import_error": "",
                    },
                )
                return await self.get(project_id)
        except (HTTPException, httpx.RequestError, TimeoutError) as exc:
            message = (
                exc.detail
                if isinstance(exc, HTTPException)
                else "Import interrupted. Please retry."
            )
            try:
                await self.remove_object(project_id)
            except HTTPException:
                message += " File cleanup pending; retry or delete this project."
            await self.patch(
                project_id,
                {"status": "failed", "import_error": message, "manifest": [], "skipped": []},
            )
            raise HTTPException(
                exc.status_code if isinstance(exc, HTTPException) else 503, message
            ) from None

    async def bundle(self, project_id):
        project = await self.get(project_id)
        if project["status"] != "ready":
            raise HTTPException(409, "Import must finish before reading source files.")
        try:
            async with self.http.stream(
                "GET",
                f"{self.base}/storage/v1/object/authenticated/project-sources/{self.object_path(project_id)}",
                headers=self.headers,
            ) as response:
                if response.status_code != 200:
                    raise HTTPException(503, "Source files unavailable. Please retry.")
                chunks, total = [], 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_BUNDLE:
                        raise HTTPException(413, "Stored source exceeds limits.")
                    chunks.append(chunk)
            data = json.loads(b"".join(chunks))
            if (
                not isinstance(data, dict)
                or len(data) > 500
                or any(not isinstance(k, str) or not isinstance(v, str) for k, v in data.items())
            ):
                raise ValueError()
            return data
        except (httpx.RequestError, ValueError):
            raise HTTPException(503, "Source files unavailable or invalid.") from None

    async def delete(self, project_id):
        await self.claim(project_id, "deleting")
        try:
            await self.remove_object(project_id)
            await self.rest(
                "DELETE", params={"id": f"eq.{project_id}", "owner_id": f"eq.{self.user.id}"}
            )
        except HTTPException:
            await self.patch(
                project_id,
                {"status": "failed", "import_error": "Deletion incomplete. Retry deletion."},
            )
            raise
