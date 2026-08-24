from sqlalchemy import func, select

from lessoncanvas.models import SourceChunk


def create_project(client, headers) -> str:
    response = client.post("/projects", json={"name": "来源测试项目"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def upload(client, headers, project_id, name, data, ack="true"):
    return client.post(
        f"/projects/{project_id}/sources",
        files={"file": (name, data, "application/octet-stream")},
        data={"rights_acknowledged": ack},
        headers=headers,
    )


def test_txt_source_becomes_ready_with_chunks(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "unit-notes.txt", b"hello teaching material")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["rights_acknowledged"] is True

    listed = client.get(f"/projects/{project_id}/sources", headers=auth).json()
    assert [s["status"] for s in listed] == ["ready"]

    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    chunk_count = session.scalar(
        select(func.count(SourceChunk.id)).where(SourceChunk.source_id == listed[0]["id"])
    )
    session.close()
    assert chunk_count == 1


def test_disallowed_format_rejected(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "notes.exe", b"MZ")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "REQUIREMENT"
    assert "not allowed" in error["message"]


def test_oversize_rejected(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "big.txt", b"x" * (21 * 1024 * 1024))
    assert response.status_code == 422
    assert "size limit" in response.json()["error"]["message"]


def test_missing_rights_acknowledgement_rejected(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "notes.txt", b"content", ack="false")
    assert response.status_code == 422
    assert "rights" in response.json()["error"]["message"]


def test_source_count_limit_enforced(client, auth):
    project_id = create_project(client, auth)
    for index in range(10):
        response = upload(client, auth, project_id, f"n{index}.txt", b"content")
        assert response.status_code == 201, response.text
    response = upload(client, auth, project_id, "n10.txt", b"content")
    assert response.status_code == 422
    assert "limit" in response.json()["error"]["message"]


def test_student_data_rejected_before_grounding(client, auth):
    project_id = create_project(client, auth)
    payload = "本次考试学生姓名：张三 成绩：90 班级排名：1 身份证号：110101200001011234".encode()
    response = upload(client, auth, project_id, "grades.txt", payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rejected"
    assert body["rejection_code"] == "STUDENT_DATA"

    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    chunk_count = session.scalar(
        select(func.count(SourceChunk.id)).where(SourceChunk.source_id == body["id"])
    )
    session.close()
    assert chunk_count == 0


def test_corrupt_pdf_fails_parsing(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "broken.pdf", b"%PDF-1.4 not really")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["rejection_code"] == "PARSE_FAILED"


def test_source_delete_and_cross_account_non_disclosure(client, auth, teacher_b_token):
    project_id = create_project(client, auth)
    created = upload(client, auth, project_id, "notes.txt", b"content").json()

    other = {"Authorization": f"Bearer {teacher_b_token}"}
    denied = client.get(f"/projects/{project_id}/sources/{created['id']}", headers=other)
    assert denied.status_code == 404

    deleted = client.delete(f"/projects/{project_id}/sources/{created['id']}", headers=auth)
    assert deleted.status_code == 204
    assert client.get(f"/projects/{project_id}/sources", headers=auth).json() == []
