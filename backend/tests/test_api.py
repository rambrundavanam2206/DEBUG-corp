import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app

URL = "https://phase-one.supabase.co"
USER = "11111111-1111-4111-8111-111111111111"
TOKEN = "test-session-token"
SETTINGS = Settings(supabase_url=URL, supabase_publishable_key="sb_publishable_test_only")
AUTH_USER = {"id": USER, "email": "test@example.com", "email_confirmed_at": "2026-11-24"}


@pytest.fixture
def client():
    with TestClient(create_app(SETTINGS)) as client:
        yield client


def auth_header():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_health_and_no_cache(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/api/me", "/api/projects"])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"}])
def test_missing_or_wrong_auth(client, path, headers):
    assert client.get(path, headers=headers).status_code == 401


@respx.mock
def test_invalid_session(client):
    respx.get(f"{URL}/auth/v1/user").mock(return_value=httpx.Response(401))
    response = client.get("/api/me", headers=auth_header())
    assert response.status_code == 401
    assert TOKEN not in response.text


@respx.mock
def test_verified_user_only(client):
    route = respx.get(f"{URL}/auth/v1/user").mock(return_value=httpx.Response(200, json=AUTH_USER))
    response = client.get("/api/me", headers=auth_header())
    assert response.json() == {"id": USER, "email": "test@example.com"}
    assert route.calls[0].request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert route.calls[0].request.headers["apikey"] == SETTINGS.supabase_publishable_key


@respx.mock
def test_unconfirmed_or_anonymous_rejected(client):
    route = respx.get(f"{URL}/auth/v1/user")
    route.mock(return_value=httpx.Response(200, json={**AUTH_USER, "email_confirmed_at": None}))
    assert client.get("/api/me", headers=auth_header()).status_code == 403
    route.mock(return_value=httpx.Response(200, json={**AUTH_USER, "is_anonymous": True}))
    assert client.get("/api/me", headers=auth_header()).status_code == 403


@respx.mock
def test_projects_forward_user_token_and_verified_owner(client):
    respx.get(f"{URL}/auth/v1/user").mock(return_value=httpx.Response(200, json=AUTH_USER))
    route = respx.get(f"{URL}/rest/v1/projects").mock(return_value=httpx.Response(200, json=[]))
    response = client.get("/api/projects?owner_id=someone-else", headers=auth_header())
    assert response.status_code == 200
    assert response.json() == []
    request = route.calls[0].request
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.url.params["owner_id"] == f"eq.{USER}"


@respx.mock
def test_upstream_failure_does_not_leak_details(client):
    respx.get(f"{URL}/auth/v1/user").mock(return_value=httpx.Response(500, text="private internal detail"))
    response = client.get("/api/me", headers=auth_header())
    assert response.status_code == 503
    assert "private internal detail" not in response.text


@respx.mock
def test_network_failure_returns_retryable_error(client):
    respx.get(f"{URL}/auth/v1/user").mock(side_effect=httpx.ConnectError("unreachable"))
    assert client.get("/api/me", headers=auth_header()).status_code == 503


@respx.mock
def test_bad_project_payload(client):
    respx.get(f"{URL}/auth/v1/user").mock(return_value=httpx.Response(200, json=AUTH_USER))
    respx.get(f"{URL}/rest/v1/projects").mock(return_value=httpx.Response(200, json={"unexpected": True}))
    assert client.get("/api/projects", headers=auth_header()).status_code == 503


def test_cors_allows_only_configured_frontend(client):
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}
    response = client.options("/api/me", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    headers["Origin"] = "https://untrusted.example"
    response = client.options("/api/me", headers=headers)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_secret_key_rejected_and_wildcard_cors_rejected():
    with pytest.raises(ValidationError):
        Settings(supabase_url=URL, supabase_publishable_key="sb_secret_not_allowed")
    with pytest.raises(ValidationError):
        Settings(supabase_url=URL, supabase_publishable_key="sb_publishable_test_only", cors_origins=["*"])
