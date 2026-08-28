FULL_CORPUS = "\n".join(
    [
        "单元主题：环境保护与可持续发展",
        "课时数：6",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
    ]
)

PARTIAL_CORPUS = "单元主题：环境保护"


def setup_project(client, auth, corpus) -> str:
    project = client.post("/projects", json={"name": "简报测试"}, headers=auth)
    project_id = project.json()["id"]
    client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", corpus.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    started = client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    assert started.status_code == 200
    return project_id


def test_draft_created_from_discovery(client, auth):
    project_id = setup_project(client, auth, FULL_CORPUS)
    brief = client.get(f"/projects/{project_id}/brief", headers=auth)
    assert brief.status_code == 200
    body = brief.json()
    assert body["draft_revision"] == 1
    assert body["fields"]["unit_theme"]["value"] == "环境保护与可持续发展"
    assert body["confirmed_version"] is None


def test_patch_creates_new_revision_and_stale_conflict(client, auth):
    project_id = setup_project(client, auth, FULL_CORPUS)
    patched = client.patch(
        f"/projects/{project_id}/brief/draft",
        json={"fields": {"lesson_count": "8"}, "base_revision": 1},
        headers=auth,
    )
    assert patched.status_code == 200
    assert patched.json()["draft_revision"] == 2
    assert patched.json()["fields"]["lesson_count"]["value"] == "8"

    stale = client.patch(
        f"/projects/{project_id}/brief/draft",
        json={"fields": {"lesson_count": "9"}, "base_revision": 1},
        headers=auth,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_VERSION"


def test_confirm_requires_all_fields(client, auth):
    project_id = setup_project(client, auth, PARTIAL_CORPUS)
    status = client.get(f"/projects/{project_id}/discovery", headers=auth).json()
    posts = 0
    while status["status"] == "questioning" and posts < 10:
        posts += 1
        status = client.post(
            f"/projects/{project_id}/discovery/answers",
            json={"answers": {}},
            headers=auth,
        ).json()
    assert status["status"] == "draft_ready"

    confirm = client.post(f"/projects/{project_id}/brief/confirm", headers=auth)
    assert confirm.status_code == 422
    error = confirm.json()["error"]
    assert error["code"] == "REQUIREMENT"
    assert "lesson_count" in error["details"]["missing"]


def test_confirm_creates_immutable_version_idempotently(client, auth):
    project_id = setup_project(client, auth, FULL_CORPUS)
    first = client.post(f"/projects/{project_id}/brief/confirm", headers=auth)
    assert first.status_code == 200
    assert first.json()["version"] == 1

    second = client.post(f"/projects/{project_id}/brief/confirm", headers=auth)
    assert second.json()["version"] == 1

    patched = client.patch(
        f"/projects/{project_id}/brief/draft",
        json={"fields": {"unit_theme": "气候变化"}, "base_revision": 1},
        headers=auth,
    )
    assert patched.status_code == 200

    brief = client.get(f"/projects/{project_id}/brief", headers=auth).json()
    assert brief["confirmed_version"] == 1
    assert brief["confirmed_fields"]["unit_theme"]["value"] == "环境保护与可持续发展"
    assert brief["fields"]["unit_theme"]["value"] == "气候变化"


def test_concurrent_confirm_yields_single_version(client, auth):
    import threading

    from fastapi.testclient import TestClient

    from lessoncanvas import main

    project_id = setup_project(client, auth, FULL_CORPUS)
    results = []
    errors = []

    def confirm():
        try:
            local_client = TestClient(main.app)
            response = local_client.post(f"/projects/{project_id}/brief/confirm", headers=auth)
            results.append(response.json().get("version"))
        except Exception as error:  # pragma: no cover
            errors.append(error)

    threads = [threading.Thread(target=confirm) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert sorted(results) == [1, 1]


def test_normalize_fields_coerces_unknown_grounding_to_teacher_stated():
    from lessoncanvas.modules.discovery_planning.brief import _normalize_fields

    normalized = _normalize_fields(
        {
            "unit_theme": {"value": "环境保护", "grounding": "教师陈述"},
            "lesson_count": {"value": "6", "grounding": "unit-hints"},
            "student_context": {"value": None, "grounding": "anything"},
        }
    )
    assert normalized["unit_theme"]["grounding"] == "teacher-stated"
    assert normalized["lesson_count"]["grounding"] == "teacher-stated"
    assert normalized["student_context"]["grounding"] is None
    assert normalized["student_context"]["unresolved"] is True
