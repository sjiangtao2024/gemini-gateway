from fastapi.testclient import TestClient

from app.main import app


def test_models_endpoint():
    client = TestClient(app)
    resp = client.get("/v1/models", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 200
