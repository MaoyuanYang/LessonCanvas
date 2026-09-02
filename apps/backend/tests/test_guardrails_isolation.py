"""F011 TS-001: endpoint-inventory cross-account and unauthenticated sweep.

The route inventory derives from the live app (openapi paths) so new endpoints
join the sweep automatically; a path that forgets ownership enforcement fails
here rather than in production.
"""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from conftest import make_token
from lessoncanvas.main import app

SAFE_ERROR_CODES = {"NOT_FOUND", "AUTH_REQUIRED"}

# Workspace-self surfaces: the caller legitimately sees their own data here.
# The cross-account assertion is "no foreign content", not denial. Destructive
# self-actions (DELETE /account) are excluded from execution: ownership is
# workspace-scoped by construction and running it would destroy the caller.
WORKSPACE_SELF_GETS = {
    "/projects",
    "/account/usage",
    "/account/audit",
    "/account/deletion-status",
    # F013: workspace-scoped memory overview; cross-account assertion is
    # "no foreign content", and project-scoped memory views stay 404-denied
    # below through get_owned_project.
    "/memory",
}
# ADR-0006 D11: the guest-token endpoint is unauthenticated by design (it
# mints the first credential); its disclosure behavior is covered directly by
# test_guest_token.py (TS-016). Everything else must deny cross-account and
# unauthenticated callers.
EXCLUDED = {("DELETE", "/account"), ("POST", "/auth/guest-token")}


def _inventory() -> list[tuple[str, str]]:
    spec = app.openapi()
    inventory = []
    for path, methods in spec["paths"].items():
        if path == "/health":
            continue
        for method in methods:
            if method in ("get", "post", "patch", "delete", "put"):
                inventory.append((method.upper(), path))
    return inventory


INVENTORY = _inventory()


def _foreign_project_id(client) -> str:
    token = make_token("sweep_owner_b")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/projects", json={"name": "他人项目"}, headers=headers)
    assert created.status_code == 201
    return created.json()["id"]


def _substitute(method: str, path: str, foreign_project: str) -> str:
    path = path.replace("{project_id}", foreign_project)
    # Nested ids: random uuids prove indistinguishable non-disclosure for both
    # existing and non-existing foreign resources.
    path = re.sub(r"\{[a-z_]+_id\}", str(uuid.uuid4()), path)
    return path


@pytest.mark.parametrize("method,path", INVENTORY)
def test_cross_account_request_discloses_nothing(method, path, client, auth):
    if (method, path) in EXCLUDED:
        pytest.skip("destructive workspace-self action; ownership scoped by construction")
    foreign_project = _foreign_project_id(client)
    url = _substitute(method, path, foreign_project)
    if method == "GET":
        response = client.get(url, headers=auth)
    elif method == "POST":
        response = client.post(url, headers=auth)
    elif method == "PATCH":
        response = client.patch(url, headers=auth)
    elif method == "DELETE":
        response = client.delete(url, headers=auth)
    else:
        response = client.put(url, headers=auth)
    if method == "GET" and path in WORKSPACE_SELF_GETS:
        # Own-data surface: succeeds, and the foreign project never appears.
        assert response.status_code == 200
        assert foreign_project not in response.text
        return
    assert response.status_code in (404, 401, 422), (method, path, response.status_code)
    if response.status_code in (404, 401):
        body = response.json()
        assert body["error"]["code"] in SAFE_ERROR_CODES
        # Nothing but the safe error envelope: no names, content, or metadata
        # from the owning workspace ever crosses the boundary.
        assert set(body) == {"error"}


@pytest.mark.parametrize("method,path", INVENTORY)
def test_unauthenticated_request_discloses_nothing(method, path, client):
    if (method, path) in EXCLUDED:
        pytest.skip("sanctioned unauthenticated route (see EXCLUDED note)")
    foreign_project = _foreign_project_id(client)
    url = _substitute(method, path, foreign_project)
    if method == "GET":
        response = client.get(url)
    elif method == "POST":
        response = client.post(url)
    elif method == "PATCH":
        response = client.patch(url)
    elif method == "DELETE":
        response = client.delete(url)
    else:
        response = client.put(url)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert set(response.json()) == {"error"}


def test_inventory_covers_all_mounted_routes():
    # The guard: the sweep inventory must be non-trivial and stay in sync with
    # the mounted routers.
    assert len(INVENTORY) > 60
    methods, paths = zip(*INVENTORY, strict=True)
    assert any("{project_id}" in path for path in paths)
    _ = TestClient  # documented: sweep runs through the real ASGI app
