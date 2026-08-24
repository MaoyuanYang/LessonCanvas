from fastapi.testclient import TestClient


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_health_reports_unavailable_database(monkeypatch):
    from lessoncanvas import main

    monkeypatch.setattr(main, "check_database", lambda: "unavailable")
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "unavailable"


def test_health_includes_correlation_id(client):
    response = client.get("/health", headers={"x-correlation-id": "trace-1"})
    assert response.headers["x-correlation-id"] == "trace-1"
