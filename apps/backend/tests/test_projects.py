import uuid


def create_project(client, headers, name="必修一 Unit 1") -> dict:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_project_crud_owner_scoped(client, auth):
    created = create_project(client, auth, name="外研社必修一 Unit 3")

    listed = client.get("/projects", headers=auth).json()
    assert [p["id"] for p in listed] == [created["id"]]
    assert listed[0]["status"] == "active"

    fetched = client.get(f"/projects/{created['id']}", headers=auth)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "外研社必修一 Unit 3"

    deleted = client.delete(f"/projects/{created['id']}", headers=auth)
    assert deleted.status_code == 204

    assert client.get("/projects", headers=auth).json() == []
    missing = client.get(f"/projects/{created['id']}", headers=auth)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


def test_cross_account_non_disclosure(client, auth, teacher_b_token):
    created = create_project(client, auth)
    other = {"Authorization": f"Bearer {teacher_b_token}"}

    assert client.get("/projects", headers=other).json() == []

    for method in ("get", "delete"):
        response = getattr(client, method)(f"/projects/{created['id']}", headers=other)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    random_id = str(uuid.uuid4())
    indistinguishable = client.get(f"/projects/{random_id}", headers=other)
    assert indistinguishable.status_code == 404


def test_project_validation(client, auth):
    blank = client.post("/projects", json={"name": "   "}, headers=auth)
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "REQUIREMENT"

    too_long = client.post("/projects", json={"name": "x" * 61}, headers=auth)
    assert too_long.status_code == 422


def test_project_quota_enforced(client, auth):
    for index in range(5):
        create_project(client, auth, name=f"项目 {index}")
    response = client.post("/projects", json={"name": "第六个"}, headers=auth)
    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "QUOTA_EXCEEDED"
    assert error["correlation_id"]


def test_deleted_project_frees_quota(client, auth):
    ids = [create_project(client, auth, name=f"项目 {i}")["id"] for i in range(5)]
    assert client.delete(f"/projects/{ids[0]}", headers=auth).status_code == 204
    response = client.post("/projects", json={"name": "替补"}, headers=auth)
    assert response.status_code == 201
