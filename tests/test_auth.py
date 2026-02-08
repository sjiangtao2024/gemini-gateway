from fastapi.testclient import TestClient

from app.main import app
from app.auth.middleware import configure_auth


def test_health_no_auth_required():
    """健康检查端点始终不需要认证"""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_no_api_key_allows_all():
    """没有配置 API Key 时，所有端点都可以访问（开发模式）"""
    configure_auth("")  # 确保没有 API Key
    client = TestClient(app)
    
    # 未设置 API Key 时，API 端点可以访问
    resp = client.get("/v1/models")
    assert resp.status_code == 200


def test_api_key_required_when_set():
    """设置了 API Key 后，需要认证才能访问 API"""
    test_key = "test-api-key-12345"
    configure_auth(test_key)
    client = TestClient(app)
    
    # 没有认证时返回 401
    resp = client.get("/v1/models")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"
    
    # 使用 Bearer 格式认证
    resp = client.get("/v1/models", headers={"Authorization": f"Bearer {test_key}"})
    assert resp.status_code == 200
    
    # 使用 OpenAI 风格格式（直接 key）
    resp = client.get("/v1/models", headers={"Authorization": test_key})
    assert resp.status_code == 200
    
    # 使用 X-API-Key header
    resp = client.get("/v1/models", headers={"X-API-Key": test_key})
    assert resp.status_code == 200
    
    # 错误的 key 返回 401
    resp = client.get("/v1/models", headers={"Authorization": "Bearer wrong-key"})
    assert resp.status_code == 401


def test_static_files_no_auth():
    """静态文件不需要认证"""
    configure_auth("test-key")  # 设置 API Key
    client = TestClient(app)
    
    # 静态文件可以访问
    resp = client.get("/static/admin.html")
    assert resp.status_code == 200
    
    # 根路径可以访问
    resp = client.get("/")
    assert resp.status_code == 200