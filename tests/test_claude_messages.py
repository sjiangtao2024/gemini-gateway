from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_API_KEY


def test_claude_messages_requires_g4f():
    client = TestClient(app)
    resp = client.post(
        "/v1/messages",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"model": "claude-3-opus", "messages": []},
    )
    assert resp.status_code == 503
