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


def test_trace_is_owner_scoped_and_records_model_events(client, auth, teacher_b_token):
    project_id = client.post("/projects", json={"name": "轨迹测试"}, headers=auth).json()["id"]
    client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", FULL_CORPUS.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    client.post(
        f"/projects/{project_id}/discovery/narrate",
        json={"text": "轨迹叙述。"},
        headers=auth,
    )

    import time

    trace = None
    for _ in range(50):
        trace = client.get(f"/projects/{project_id}/trace", headers=auth).json()
        if any(event["event_type"] == "model.narration" for event in trace["events"]):
            break
        time.sleep(0.1)

    event_types = {event["event_type"] for event in trace["events"]}
    assert "model.gap_analysis" in event_types
    assert "model.build_draft" in event_types
    assert "model.narration" in event_types
    assert all(event["latency_ms"] is not None for event in trace["events"])
    assert trace["runs"][0]["model_calls"] >= 2

    other = {"Authorization": f"Bearer {teacher_b_token}"}
    denied = client.get(f"/projects/{project_id}/trace", headers=other)
    assert denied.status_code == 404
