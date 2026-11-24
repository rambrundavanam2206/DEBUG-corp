from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None
    token: str


def unauthorized() -> HTTPException:
    return HTTPException(
        401, "Your session is invalid or expired. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    settings = request.app.state.settings
    # Verify remotely with Supabase Auth. Never trust an unverified JWT decode.
    try:
        response = await request.app.state.http.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {credentials.credentials}",
            },
        )
    except httpx.RequestError:
        raise HTTPException(503, "Authentication is temporarily unavailable. Please retry.") from None
    if response.status_code in (401, 403):
        raise unauthorized()
    if response.status_code != 200:
        raise HTTPException(503, "Authentication is temporarily unavailable. Please retry.")
    try:
        user = response.json()
        user_id = str(UUID(user["id"]))
    except (ValueError, KeyError, TypeError):
        raise HTTPException(503, "Authentication returned an invalid response.") from None
    if user.get("is_anonymous") or not user.get("email_confirmed_at"):
        raise HTTPException(403, "Confirm your email address before continuing.")
    return AuthenticatedUser(user_id, user.get("email"), credentials.credentials)
