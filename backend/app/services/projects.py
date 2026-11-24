import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError
from uuid import UUID
from datetime import datetime
from typing import Literal

from app.core.auth import AuthenticatedUser


class Project(BaseModel):
    id: UUID
    name: str
    source_type: Literal["zip", "github"]
    created_at: datetime
    updated_at: datetime


async def list_projects(request: Request, user: AuthenticatedUser) -> list[Project]:
    settings = request.app.state.settings
    try:
        response = await request.app.state.http.get(
            f"{settings.supabase_url}/rest/v1/projects",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {user.token}",
            },
            params={
                "select": "id,name,source_type,created_at,updated_at",
                "owner_id": f"eq.{user.id}",
                "order": "created_at.desc",
                "limit": "100",
            },
        )
    except httpx.RequestError:
        raise HTTPException(503, "Projects are temporarily unavailable. Please retry.") from None
    # The user JWT reaches PostgREST, so RLS applies in addition to the owner filter.
    if response.status_code in (401, 403):
        raise HTTPException(401, "Your session is invalid or expired. Please sign in again.")
    if response.status_code != 200:
        raise HTTPException(503, "Projects are temporarily unavailable. Please retry.")
    try:
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Expected project list")
        return [Project.model_validate(row) for row in payload]
    except (ValueError, TypeError, ValidationError):
        raise HTTPException(503, "Projects returned an invalid response.") from None
