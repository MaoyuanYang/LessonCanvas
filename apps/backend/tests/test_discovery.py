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

PARTIAL_CORPUS = "\n".join(["单元主题：环境保护", "课时数：4"])


def create_project(client, auth) -> str:
    response = client.post("/projects", json={"name": "发现测试"}, headers=auth)
    assert response.status_code == 201
    return response.json()["id"]


def add_source(client, auth, project_id, text) -> None:
    response = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", text.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    assert response.status_code == 201


def test_questions_target_only_gaps_within_limits(client, auth):
    project_id = create_project(client, auth)
    add_source(client, auth, project_id, PARTIAL_CORPUS)
    started = client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "questioning"
    fields = {q["field"] for q in body["questions"]}
    assert "unit_theme" not in fields
    assert "lesson_count" not in fields
    assert 0 < len(body["questions"]) <= 3

    answered = client.post(
        f"/projects/{project_id}/discovery/answers",
        json={"answers": {"student_context": "高二，中等水平"}},
        headers=auth,
    )
    assert answered.status_code == 200
    fields_after = {q["field"] for q in answered.json()["questions"]}
    assert "student_context" not in fields_after


def test_no_gaps_produces_immediate_draft(client, auth):
    project_id = create_project(client, auth)
    add_source(client, auth, project_id, FULL_CORPUS)
    started = client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    body = started.json()
    assert body["status"] == "draft_ready"
    assert body["questions"] == []
    assert body["draft"]["unit_theme"]["unresolved"] is False


def test_round_cap_marks_unresolved(client, auth):
    project_id = create_project(client, auth)
    add_source(client, auth, project_id, "没有结构化字段的内容")
    status = client.post(f"/projects/{project_id}/discovery/start", headers=auth).json()
    answers_posts = 0
    while status["status"] == "questioning" and answers_posts < 10:
        answers_posts += 1
        status = client.post(
            f"/projects/{project_id}/discovery/answers",
            json={"answers": {}},
            headers=auth,
        ).json()
    assert status["status"] == "draft_ready"
    assert status["round_count"] == 6
    unresolved = [field for field, value in status["draft"].items() if value["unresolved"]]
    assert unresolved


def test_duplicate_start_reuses_active_run(client, auth):
    project_id = create_project(client, auth)
    add_source(client, auth, project_id, PARTIAL_CORPUS)
    first = client.post(f"/projects/{project_id}/discovery/start", headers=auth).json()
    second = client.post(f"/projects/{project_id}/discovery/start", headers=auth).json()
    assert first["run_id"] == second["run_id"]


def test_provider_failure_preserves_state_and_retry_resumes(client, auth, monkeypatch):
    from lessoncanvas.adapters import model as model_adapter
    from lessoncanvas.modules.discovery_planning import graph as discovery_graph

    class Failing:
        def complete(self, system, user):
            raise model_adapter.ModelProviderError("down")

    monkeypatch.setattr(discovery_graph, "get_model_adapter", lambda: Failing())

    project_id = create_project(client, auth)
    add_source(client, auth, project_id, PARTIAL_CORPUS)
    failed = client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "PROVIDER_TRANSIENT"

    status = client.get(f"/projects/{project_id}/discovery", headers=auth).json()
    assert status["status"] == "provider_failed"

    monkeypatch.setattr(discovery_graph, "get_model_adapter", model_adapter.get_model_adapter)
    retried = client.post(f"/projects/{project_id}/discovery/retry", headers=auth)
    assert retried.status_code == 200
    assert retried.json()["status"] == "questioning"


def test_discovery_cross_account_non_disclosure(client, auth, teacher_b_token):
    project_id = create_project(client, auth)
    other = {"Authorization": f"Bearer {teacher_b_token}"}
    response = client.post(f"/projects/{project_id}/discovery/start", headers=other)
    assert response.status_code == 404
