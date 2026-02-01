from fastapi.testclient import TestClient

from app.main import app


def test_claude_messages_requires_g4f():
    client = TestClient(app)
    resp = client.post(
        "/v1/messages",
        headers={"Authorization": "Bearer test"},
        json={"model": "claude-3-opus", "messages": []},
    )
    assert resp.status_code == 503
