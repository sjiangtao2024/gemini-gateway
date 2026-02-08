import pytest

from app.providers.g4f import G4FProvider


@pytest.mark.anyio
async def test_list_models_filters_prefixes():
    """测试模型列表和前缀过滤"""
    provider = G4FProvider(
        providers=["Qwen", "OpenaiChat"],
        model_prefixes=["qwen-", "gpt-"],
    )
    models = await provider.list_models()
    
    # 应该只返回匹配前缀的模型
    model_ids = [m["id"] for m in models]
    assert all(m.startswith(("qwen-", "gpt-")) for m in model_ids)
    assert "qwen-2.5" in model_ids
    assert "gpt-4o" in model_ids


@pytest.mark.anyio
async def test_list_models_no_prefixes():
    """测试没有前缀过滤时返回所有模型"""
    provider = G4FProvider()
    models = await provider.list_models()
    
    # 应该返回所有常见模型
    model_ids = [m["id"] for m in models]
    assert "gpt-4o" in model_ids
    assert "qwen-2.5" in model_ids


def test_get_provider_mapping():
    """测试 provider 自动映射"""
    provider = G4FProvider()
    
    # ChatGPT
    assert provider._get_provider("gpt-4o") is not None
    assert provider._get_provider("gpt-3.5-turbo") is not None
    
    # Qwen
    assert provider._get_provider("qwen-2.5") is not None
    
    # GLM
    assert provider._get_provider("glm-4") is not None
    
    # Grok
    assert provider._get_provider("grok-2") is not None


@pytest.mark.anyio
async def test_provider_initialization():
    """测试 Provider 初始化"""
    provider = G4FProvider(
        providers=["Qwen"],
        model_prefixes=["qwen-"],
        timeout=60.0,
    )
    
    assert provider.providers == ["Qwen"]
    assert provider.model_prefixes == ["qwen-"]
    assert provider.timeout == 60.0
    assert provider._client is not None
