import pytest
from app.auth.middleware import configure_auth

# 测试用的 API Key
TEST_API_KEY = "test-api-key-for-testing-only"


@pytest.fixture(autouse=True)
def setup_auth():
    """每个测试前设置测试 API Key"""
    configure_auth(TEST_API_KEY)
    yield


@pytest.fixture
def auth_headers():
    """提供测试认证 headers"""
    return {"Authorization": f"Bearer {TEST_API_KEY}"}