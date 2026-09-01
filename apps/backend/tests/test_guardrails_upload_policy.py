"""F011 TS-007/TS-003: upload boundary hardening and daily volume cap."""

import struct

import pytest

from conftest import make_token
from lessoncanvas.modules.product_validation import service as pv_service
from lessoncanvas.settings import get_settings


def create_project(client, headers) -> str:
    response = client.post("/projects", json={"name": "上传加固项目"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def upload(client, headers, project_id, name, data):
    return client.post(
        f"/projects/{project_id}/sources",
        files={"file": (name, data, "application/octet-stream")},
        data={"rights_acknowledged": "true"},
        headers=headers,
    )


def fake_bomb_docx(declared_uncompressed: int) -> bytes:
    """A tiny zip whose central directory declares a huge uncompressed size.

    Only the metadata matters for the guard: zipfile reads the central
    directory without inflating any entry.
    """
    name = b"bomb.bin"
    local = (
        struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,
            20,
            20,
            0,
            8,
            0,
            0,
            0,
            0,
            len(name),
            0,
        )
        + name
    )
    central = (
        struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,
            20,
            20,
            0,
            8,
            0,
            0,
            0,
            0,
            declared_uncompressed,
            len(name),
            0,
            0,
            0,
            0,
            0,
            0,
        )
        + name
    )
    eocd = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(central),
        len(local),
        0,
    )
    return local + central + eocd


def test_binary_renamed_txt_rejected_at_policy_boundary(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "notes.txt", b"\xff\xfe\x00\x10binary")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "REQUIREMENT"
    assert "does not match" in error["message"]


def test_text_renamed_pdf_rejected_at_policy_boundary(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "notes.pdf", b"plain text, not a pdf")
    assert response.status_code == 422
    assert "does not match" in response.json()["error"]["message"]


def test_pdf_head_renamed_docx_rejected_at_policy_boundary(client, auth):
    project_id = create_project(client, auth)
    response = upload(client, auth, project_id, "notes.docx", b"%PDF-1.7 fake")
    assert response.status_code == 422
    assert "does not match" in response.json()["error"]["message"]


def test_zip_bomb_docx_settles_failed_without_extraction(client, auth):
    from sqlalchemy import select

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import Source

    project_id = create_project(client, auth)
    bomb = fake_bomb_docx(500 * 1024 * 1024)
    assert len(bomb) < 10 * 1024  # the fixture itself stays tiny
    response = upload(client, auth, project_id, "bomb.docx", bomb)
    assert response.status_code == 201

    session = SessionLocal()
    source = session.scalars(select(Source).where(Source.project_id == project_id)).one()
    session.close()
    assert source.status == "failed"
    assert source.rejection_code == "PARSE_FAILED"
    assert "bounded extraction" in (source.rejection_message or "")


def test_docx_entry_count_guard(monkeypatch, tmp_path):
    import io

    import docx

    from lessoncanvas.modules.sources_grounding import parsing

    buffer = io.BytesIO()
    docx.Document().save(buffer)
    normal = buffer.getvalue()
    assert parsing.extract_text("a.docx", normal) == ""

    monkeypatch.setattr(parsing, "MAX_DOCX_ENTRIES", 2)
    with pytest.raises(parsing.ParseError, match="too many entries"):
        parsing.extract_text("a.docx", normal)


def test_daily_upload_volume_cap(client, auth, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_daily_bytes_per_workspace", 90 * 1024)

    project_id = create_project(client, auth)
    first = upload(client, auth, project_id, "a.txt", b"a" * (60 * 1024))
    assert first.status_code == 201
    second = upload(client, auth, project_id, "b.txt", b"b" * (60 * 1024))
    assert second.status_code == 429
    details = second.json()["error"]["details"]
    assert details["limit"] == "upload_daily"
    assert details["limit_value"] == 90 * 1024
    assert details["used"] > 90 * 1024

    usage = client.get("/account/usage", headers=auth).json()
    assert usage["upload_daily_bytes"]["used"] > 90 * 1024

    # The daily window is per workspace.
    other_headers = {"Authorization": f"Bearer {make_token('teacher_c')}"}
    other_project = create_project(client, other_headers)
    assert upload(client, other_headers, other_project, "c.txt", b"c" * 1024).status_code == 201


def test_evidence_document_content_type_must_match_declared():
    assert pv_service._content_matches("application/pdf", b"%PDF-1.7 x")
    assert not pv_service._content_matches("application/pdf", b"plain text")
    assert pv_service._content_matches("image/png", b"\x89PNG\r\n\x1a\nrest")
    assert not pv_service._content_matches("image/png", b"%PDF-1.7")
    assert pv_service._content_matches("text/plain", "中文文本".encode())
    assert not pv_service._content_matches(
        "text/plain", b"\xff\xfe\x00binary"
    )
