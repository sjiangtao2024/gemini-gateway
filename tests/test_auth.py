from fastapi.testclient import TestClient

from app.main import app
from app.auth.middleware import configure_auth
from tests.conftest import TEST_API_KEY


def test_health_no_auth_required():
    """健康检查端点始终不需要认证"""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_api_key_required():
    """设置了 API Key 后，需要认证才能访问 API"""
    client = TestClient(app)
    
    # 没有认证时返回 401
    resp = client.get("/v1/models")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"
    
    # 使用 Bearer 格式认证
    resp = client.get("/v1/models", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
    assert resp.status_code == 200
    
    # 使用 OpenAI 风格格式（直接 key）
    resp = client.get("/v1/models", headers={"Authorization": TEST_API_KEY})
    assert resp.status_code == 200
    
    # 使用 X-API-Key header
    resp = client.get("/v1/models", headers={"X-API-Key": TEST_API_KEY})
    assert resp.status_code == 200
    
    # 错误的 key 返回 401
    resp = client.get("/v1/models", headers={"Authorization": "Bearer wrong-key"})
    assert resp.status_code == 401


def test_static_files_no_auth():
    """静态文件不需要认证"""
    client = TestClient(app)
    
    # 静态文件可以访问
    resp = client.get("/static/admin.html")
    assert resp.status_code == 200
    
    # 根路径可以访问
    resp = client.get("/")
    assert resp.status_code == 200


def test_server_requires_api_key():
    """服务器必须配置 API Key"""
    configure_auth("")  # 清空 API Key
    client = TestClient(app)
    
    resp = client.get("/v1/models")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "server_config_error"