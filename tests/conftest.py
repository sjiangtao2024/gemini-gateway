import pytest
from app.auth.middleware import configure_auth


@pytest.fixture(autouse=True)
def reset_auth():
    """每个测试前重置认证状态（无 API Key）"""
    configure_auth("")
    yield