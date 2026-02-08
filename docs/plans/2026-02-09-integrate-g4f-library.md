# 集成 g4f 库实施方案

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 将 g4f 从 HTTP API 调用改为直接导入 Python 库使用

**Changes:**
1. 修改 `app/providers/g4f.py` - 使用 `import g4f` 直接调用
2. 简化配置 - 移除 `base_url` 配置
3. 更新 `docker-compose.yml` - 移除 g4f 服务
4. 更新文档

---

## 任务1: 重写 G4FProvider

**Files:**
- Modify: `app/providers/g4f.py`

**Step 1: 重写为直接使用 g4f 库**

```python
from __future__ import annotations

import g4f
from g4f.client import AsyncClient
from typing import Any

from app.providers.base import BaseProvider
from app.services.logger import logger


class G4FProvider(BaseProvider):
    name = "g4f"

    def __init__(
        self,
        providers: list[str] | None = None,
        model_prefixes: list[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.providers = providers or []
        self.model_prefixes = model_prefixes or []
        self.timeout = timeout
        self._client = AsyncClient()
        
        # 映射 provider 名称到 g4f Provider 类
        self._provider_map = self._build_provider_map()
    
    def _build_provider_map(self) -> dict[str, Any]:
        """构建 provider 名称到 g4f Provider 类的映射"""
        provider_map = {}
        for provider_name in dir(g4f.Provider):
            provider_class = getattr(g4f.Provider, provider_name)
            if isinstance(provider_class, type) and hasattr(provider_class, 'label'):
                # 使用 provider 名称和 label 作为 key
                provider_map[provider_name.lower()] = provider_class
                if hasattr(provider_class, 'label'):
                    provider_map[provider_class.label.lower().replace(' ', '')] = provider_class
        return provider_map
    
    def _get_provider(self, model: str) -> Any | None:
        """根据模型名获取对应的 g4f Provider"""
        # 根据模型前缀判断 provider
        provider_mapping = {
            'gpt-': g4f.Provider.OpenaiChat,  # ChatGPT
            'qwen': g4f.Provider.Qwen,         # 通义千问
            'kimi': None,  # Kimi 可能需要特定 provider
            'glm': g4f.Provider.GLM,           # 智谱
            'minimax': None,  # MiniMax 可能需要特定 provider
            'grok': g4f.Provider.Grok,         # Grok
        }
        
        for prefix, provider in provider_mapping.items():
            if prefix in model.lower():
                return provider
        
        # 默认使用 OpenaiChat
        return g4f.Provider.OpenaiChat
    
    async def list_models(self) -> list[dict]:
        """列出支持的模型"""
        # g4f 支持的所有模型
        models = []
        
        # 添加常见模型
        common_models = [
            # ChatGPT
            "gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo",
            # 国内模型
            "qwen-2.5", "qwen-turbo", "qwen-max",
            "kimi-k1", "kimi-1.5",
            "glm-4", "glm-4v",
            "minimax-01",
            # 其他
            "grok-2", "grok-2-mini",
            "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
        ]
        
        # 根据配置的 prefixes 过滤
        if self.model_prefixes:
            filtered = [m for m in common_models 
                       if any(m.startswith(p) for p in self.model_prefixes)]
        else:
            filtered = common_models
        
        return [{"id": model, "object": "model", "owned_by": "g4f"} 
                for model in filtered]
    
    async def chat_completions(self, payload: dict) -> dict:
        """调用 g4f 生成对话"""
        model = payload.get("model", "gpt-4o")
        messages = payload.get("messages", [])
        
        # 获取 provider
        provider = self._get_provider(model)
        
        try:
            # 使用 g4f 直接调用
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                provider=provider,
                # 可以添加更多参数
            )
            
            # 转换为 OpenAI 格式
            return {
                "id": f"chatcmpl-g4f-{id(response)}",
                "object": "chat.completion",
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.choices[0].message.content if hasattr(response, 'choices') else str(response)
                    },
                    "finish_reason": "stop"
                }]
            }
        except Exception as e:
            logger.error(f"g4f error: {e}")
            raise
```

### Step 2: 更新 config/settings.py

移除 `base_url` 配置：

```python
class G4FSettings(BaseModel):
    enabled: bool = False
    # 移除 base_url，不再需要
    providers: List[str] = Field(default_factory=list)
    model_prefixes: List[str] = Field(default_factory=list)
    timeout: float = 30.0
```

更新 `from_env`：
```python
# 移除 g4f_base_url = os.getenv("G4F_BASE_URL", "http://localhost:1337")
```

### Step 3: 更新 main.py

修改初始化逻辑：
```python
if settings.g4f.enabled:
    g4f_provider = G4FProvider(
        # 移除 base_url=settings.g4f.base_url,
        providers=settings.g4f.providers,
        model_prefixes=settings.g4f.model_prefixes,
        timeout=settings.g4f.timeout,
    )
```

### Step 4: 更新 docker-compose.yml

移除 g4f 相关环境变量和挂载：
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - CONFIG_PATH=/app/config/config.yaml
  - GEMINI_COOKIE_PATH=/app/data/gemini/cookies.json
  # 移除 G4F_ENABLED, G4F_BASE_URL

volumes:
  # ...
  # 如果不用 g4f 的 har_and_cookies，也可以移除这些挂载
  # 或者保留供 g4f 库内部使用
```

### Step 5: 更新文档

更新配置示例和部署说明。

---

## 验证

```python
# 测试代码
from app.providers.g4f import G4FProvider

provider = G4FProvider()

# 测试列出模型
models = await provider.list_models()
print(models)

# 测试对话
result = await provider.chat_completions({
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
})
print(result)
```
