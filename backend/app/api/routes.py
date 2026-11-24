from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import AuthenticatedUser, current_user
from app.services.imports import MAX_ARCHIVE
from app.services.projects import Project, list_projects
from app.services.workspace import ProblemInput, ProjectInput, Workspace

router = APIRouter(prefix="/api")


@router.get("/me")
async def me(user: AuthenticatedUser = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email}


@router.get("/projects", response_model=list[Project])
async def projects(request: Request, user: AuthenticatedUser = Depends(current_user)):
    return await list_projects(request, user)


@router.post("/projects", status_code=201)
async def create_project(data: ProjectInput, request: Request, user=Depends(current_user)):
    return await Workspace(request, user).create(data)


@router.get("/projects/{project_id}")
async def get_project(project_id: UUID, request: Request, user=Depends(current_user)):
    return await Workspace(request, user).get(project_id)


@router.patch("/projects/{project_id}/problem")
async def update_problem(
    project_id: UUID, data: ProblemInput, request: Request, user=Depends(current_user)
):
    workspace = Workspace(request, user)
    await workspace.get(project_id)
    if not data.problem.strip():
        raise HTTPException(422, "Describe the problem or paste an error.")
    await workspace.patch(project_id, data.model_dump())
    return await workspace.get(project_id)


@router.post("/projects/{project_id}/import")
async def import_project(project_id: UUID, request: Request, user=Depends(current_user)):
    slots = request.app.state.import_slots
    if slots.locked():
        raise HTTPException(429, "Two imports are already running. Please retry shortly.")
    async with slots:
        workspace = Workspace(request, user)
        project = await workspace.get(project_id)
        archive = None
        if project["source_type"] == "zip":
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_ARCHIVE:
                    raise HTTPException(413, "ZIP exceeds 10 MB.")
                chunks.append(chunk)
            archive = b"".join(chunks)
        return await workspace.import_project(project_id, archive)


@router.get("/projects/{project_id}/file")
async def read_file(
    project_id: UUID,
    request: Request,
    path: str = Query(max_length=500),
    start: int = Query(1, ge=1),
    user=Depends(current_user),
):
    files = await Workspace(request, user).bundle(project_id)
    if path not in files:
        raise HTTPException(404, "File not found.")
    lines = files[path].splitlines()
    return {
        "path": path,
        "start": start,
        "total_lines": len(lines),
        "lines": lines[start - 1 : start + 199],
    }


@router.get("/projects/{project_id}/search")
async def search_files(
    project_id: UUID,
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    user=Depends(current_user),
):
    files = await Workspace(request, user).bundle(project_id)
    results = []
    for path, content in sorted(files.items()):
        if q.casefold() in path.casefold():
            results.append({"path": path, "line": 1, "text": "Filename match"})
        for number, line in enumerate(content.splitlines(), 1):
            if q.casefold() in line.casefold():
                results.append({"path": path, "line": number, "text": line[:300]})
            if len(results) >= 100:
                return {"results": results[:100], "truncated": True}
    return {"results": results, "truncated": False}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: UUID, request: Request, user=Depends(current_user)):
    await Workspace(request, user).delete(project_id)
    return {"deleted": True}
