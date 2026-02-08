from fastapi.testclient import TestClient

from app.config.manager import ConfigManager
from app.main import app
from app.routes.admin import configure
from tests.conftest import TEST_API_KEY


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_reload_requires_manager():
    configure(None)
    client = TestClient(app)
    resp = client.post("/admin/config/reload", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert resp.status_code == 503


def test_reload_success(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("server:\n  host: 0.0.0.0\n  port: 8022\n")
    manager = ConfigManager(str(config_path))
    manager.load()
    configure(manager)
    client = TestClient(app)
    resp = client.post("/admin/config/reload", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert resp.status_code == 200