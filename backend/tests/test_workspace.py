import json
from datetime import datetime, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from test_api import AUTH_USER, SETTINGS, TOKEN, URL, USER, auth_header
from test_imports import archive

from app.main import create_app

PID = "22222222-2222-4222-8222-222222222222"
BASE = f"/api/projects/{PID}"


@pytest.fixture
def setup():
    state = dict(
        id=PID,
        owner_id=USER,
        name="sample",
        source_type="zip",
        status="pending",
        branch="",
        repo_url="",
        problem="error",
        command="",
        expected="",
        reproduction="",
        manifest=[],
        skipped=[],
        import_error="",
        updated_at="2026-11-24T00:00:00+00:00",
    )
    with respx.mock as mock, TestClient(create_app(SETTINGS)) as client:
        mock.get(URL + "/auth/v1/user").respond(200, json=AUTH_USER)

        def db(request):
            assert request.headers["Authorization"] == f"Bearer {TOKEN}"
            if request.method != "POST":
                assert request.url.params["owner_id"] == f"eq.{USER}"
            if request.method == "PATCH":
                state.update(json.loads(request.content))
            if request.method == "DELETE":
                return httpx.Response(200, json=[state])
            return httpx.Response(200, json=[state])

        mock.route(url__startswith=URL + "/rest/v1/projects").mock(side_effect=db)
        storage = {"value": b"{}"}

        def store(request):
            if request.method == "POST":
                storage["value"] = request.content
            return httpx.Response(200, content=storage["value"])

        mock.route(url__startswith=URL + "/storage/v1/").mock(side_effect=store)
        yield client, state, mock, storage


def test_zip_read_search_edit_delete(setup):
    client, state, mock, storage = setup
    r = client.post(
        BASE + "/import",
        headers=auth_header(),
        content=archive([("app.CPP", "int main() {\nreturn 0;\n}")]),
    )
    assert r.status_code == 200, r.text
    assert state["status"] == "ready" and state["manifest"][0]["path"] == "app.CPP"
    r = client.get(BASE + "/file?path=app.CPP&start=2", headers=auth_header())
    assert r.json()["lines"][0] == "return 0;"
    assert (
        client.get(BASE + "/search?q=return", headers=auth_header()).json()["results"][0]["line"]
        == 2
    )
    assert client.get(BASE + "/file?path=../secret", headers=auth_header()).status_code == 404
    assert (
        client.patch(
            BASE + "/problem", headers=auth_header(), json={"problem": "updated"}
        ).status_code
        == 200
    )
    assert state["problem"] == "updated"
    assert client.delete(BASE, headers=auth_header()).json() == {"deleted": True}


def test_failed_zip_retries_without_duplicate_project(setup):
    client, state, _, _ = setup
    assert (
        client.post(BASE + "/import", headers=auth_header(), content=b"invalid").status_code == 422
    )
    assert state["status"] == "failed"
    assert (
        client.post(
            BASE + "/import", headers=auth_header(), content=archive([("a.py", "print(1)")])
        ).status_code
        == 200
    )
    assert state["status"] == "ready"


def test_active_import_cannot_be_deleted_or_retried(setup):
    client, state, _, _ = setup
    state.update(status="importing", operation_started=datetime.now(timezone.utc).isoformat())
    assert client.delete(BASE, headers=auth_header()).status_code == 409
    assert (
        client.post(
            BASE + "/import", headers=auth_header(), content=archive([("a.py", "1")])
        ).status_code
        == 409
    )


def test_owner_miss_never_reads_storage(setup):
    client, _, mock, _ = setup
    mock.route(url__startswith=URL + "/rest/v1/projects").respond(200, json=[])
    assert client.get(BASE + "/file?path=a.py", headers=auth_header()).status_code == 404
    assert not any("/storage/" in str(c.request.url) for c in mock.calls)


def test_missing_auth_mutations(setup):
    client, _, _, _ = setup
    assert client.delete(BASE).status_code == 401
    assert client.post(BASE + "/import", content=b"zip").status_code == 401


def test_storage_failure_keeps_retryable_project(setup):
    client, state, mock, _ = setup
    mock.route(url__startswith=URL + "/storage/v1/").respond(500)
    assert (
        client.post(
            BASE + "/import", headers=auth_header(), content=archive([("a.py", "1")])
        ).status_code
        == 503
    )
    assert state["status"] == "failed" and state["manifest"] == []
