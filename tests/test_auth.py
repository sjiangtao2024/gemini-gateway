from fastapi.testclient import TestClient

from app.main import app


def test_auth_required():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    resp = client.get("/v1/models")
    assert resp.status_code == 401
