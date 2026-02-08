from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_API_KEY


def test_images_requires_prompt():
    client = TestClient(app)
    resp = client.post(
        "/v1/images",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"model": "gemini-2.5-pro"},
    )
    assert resp.status_code == 422
