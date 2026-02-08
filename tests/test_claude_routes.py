from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_API_KEY


def test_claude_models_endpoint():
    client = TestClient(app)
    resp = client.get("/v1/claude/models", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert resp.status_code == 200
