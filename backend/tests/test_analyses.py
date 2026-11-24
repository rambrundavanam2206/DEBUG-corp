import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_ai import FILES, ScriptModel, call, diagnosis, output
from test_api import AUTH_USER, SETTINGS, URL, USER, auth_header

from app.ai.providers import BoundedModel
from app.main import create_app

PID = "22222222-2222-4222-8222-222222222222"
AID = "33333333-3333-4333-8333-333333333333"
BASE = f"/api/projects/{PID}"


@pytest.fixture
def setup():
    settings = SETTINGS.model_copy(
        update={
            "gemini_api_key": SecretStr("test-key"),
            "gemini_model": "test-model",
            "ai_free_tier_confirmed": True,
        }
    )
    project = {
        "id": PID,
        "status": "ready",
        "problem": "C++ compiler error",
        "command": "",
        "expected": "",
        "reproduction": "",
        "commit_sha": "a" * 40,
        "updated_at": "2026-11-24T00:00:00Z",
    }
    rows = []
    script = [
        call("read_file", {"path": "TICTAC.CPP", "start_line": 1, "end_line": 12}),
        output(json.dumps(diagnosis())),
    ]
    app = create_app(settings)

    @asynccontextmanager
    async def factory(settings, state):
        yield BoundedModel([("gemini", "mock-model", ScriptModel(script))], state)

    app.state.analysis_model_factory = factory
    with respx.mock as mock, TestClient(app) as client:
        mock.get(URL + "/auth/v1/user").respond(200, json=AUTH_USER)
        mock.get(URL + "/rest/v1/projects").mock(
            side_effect=lambda request: httpx.Response(200, json=[project])
        )
        mock.get(
            URL + f"/storage/v1/object/authenticated/project-sources/{USER}/{PID}/source.json"
        ).respond(200, json=FILES)

        def db(request):
            assert request.headers["Authorization"] == auth_header()["Authorization"]
            if request.method == "POST":
                rows.append(
                    {
                        "id": AID,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "error": "",
                        "result": None,
                        "usage": {},
                        **json.loads(request.content),
                    }
                )
            if request.method == "PATCH":
                if "id" in request.url.params:
                    rows[0].update(json.loads(request.content))
                    return httpx.Response(200, json=rows)
                return httpx.Response(200, json=[])
            return httpx.Response(200, json=rows)

        mock.route(url__startswith=URL + "/rest/v1/analyses").mock(side_effect=db)
        yield client, app, project, rows, script, mock


def test_saved_analysis_and_stale_problem(setup):
    client, _, project, rows, _, _ = setup
    response = client.post(BASE + "/analysis", headers=auth_header())
    assert response.status_code == 200, response.text
    a = response.json()["analysis"]
    assert a["status"] == "completed" and not a["stale"]
    assert len(a["result"]["findings"]) == 6 and a["result"]["execution_verified"] is False
    assert a["usage"]["model_calls"] == 2 and len(a["source_hash"]) == 64
    assert client.get(BASE + "/analysis", headers=auth_header()).json()["analysis"]["id"] == AID
    project["problem"] = "changed error"
    assert client.get(BASE + "/analysis", headers=auth_header()).json()["analysis"]["stale"]


def test_failure_saved_without_provider_details(setup):
    client, _, _, rows, script, _ = setup
    script[:] = [RuntimeError("sensitive internal provider body")]
    response = client.post(BASE + "/analysis", headers=auth_header())
    assert response.json()["analysis"]["status"] == "failed"
    assert "sensitive internal" not in response.text
    assert rows[0]["error_code"] == "analysis_failed"


def test_invalid_evidence_saved_as_failure(setup):
    client, _, _, _, script, _ = setup
    script[:] = [output(json.dumps(diagnosis()))]
    response = client.post(BASE + "/analysis", headers=auth_header())
    assert response.json()["analysis"]["error_code"] == "invalid_evidence"


def test_missing_configuration_leaves_no_record(setup):
    client, app, _, rows, _, _ = setup
    app.state.settings.ai_free_tier_confirmed = False
    assert client.post(BASE + "/analysis", headers=auth_header()).status_code == 503
    assert not rows
    assert client.get("/api/ai/config", headers=auth_header()).json()["ready"] is False


def test_project_not_ready_and_other_user_miss(setup):
    client, _, project, rows, _, mock = setup
    project["status"] = "pending"
    assert client.post(BASE + "/analysis", headers=auth_header()).status_code == 409
    mock.get(URL + "/rest/v1/projects").respond(200, json=[])
    assert client.get(BASE + "/analysis", headers=auth_header()).status_code == 404
    assert client.post(BASE + "/analysis", headers=auth_header()).status_code == 404
    assert not rows


def test_quota_and_duplicate_running_are_safe(setup):
    client, _, _, _, _, mock = setup
    mock.route(url__startswith=URL + "/rest/v1/analyses").mock(
        side_effect=lambda request: (
            httpx.Response(200, json=[])
            if request.method == "PATCH"
            else httpx.Response(400, text="analysis_quota")
        )
    )
    assert client.post(BASE + "/analysis", headers=auth_header()).status_code == 429


def test_endpoints_require_auth(setup):
    client, *_ = setup
    assert client.get("/api/ai/config").status_code == 401
    assert client.get(BASE + "/analysis").status_code == 401
    assert client.post(BASE + "/analysis").status_code == 401


def test_timeout_saved_as_retryable_budget_failure(setup):
    client, _, _, _, script, _ = setup
    script[:] = [TimeoutError()]
    response = client.post(BASE + "/analysis", headers=auth_header())
    assert response.json()["analysis"]["error_code"] == "budget"
    assert response.json()["analysis"]["status"] == "failed"


def test_unknown_shell_tool_cannot_execute(setup):
    client, _, _, _, script, _ = setup
    script[:] = [call("shell", {"command": "do-not-run"})]
    response = client.post(BASE + "/analysis", headers=auth_header())
    assert response.json()["analysis"]["status"] == "failed"
    assert response.json()["analysis"]["result"] is None
