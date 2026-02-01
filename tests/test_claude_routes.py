from fastapi.testclient import TestClient

from app.main import app


def test_claude_models_endpoint():
    client = TestClient(app)
    resp = client.get("/v1/claude/models", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 200
