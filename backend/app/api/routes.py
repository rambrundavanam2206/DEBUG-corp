from fastapi import APIRouter, Depends, Request
from app.core.auth import AuthenticatedUser, current_user
from app.services.projects import Project, list_projects

router = APIRouter(prefix="/api")


@router.get("/me")
async def me(user: AuthenticatedUser = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email}


@router.get("/projects", response_model=list[Project])
async def projects(request: Request, user: AuthenticatedUser = Depends(current_user)):
    return await list_projects(request, user)
