from __future__ import annotations

from pathlib import Path
from typing import Any

import g4f
from g4f.client import AsyncClient
from g4f import cookies as g4f_cookies

from app.providers.base import BaseProvider
from app.services.logger import logger

# 默认 cookie 目录
default_cookies_dir = "/app/har_and_cookies"
if Path(default_cookies_dir).exists():
    g4f_cookies.set_cookies_dir(default_cookies_dir)
    logger.info(f"g4f cookies directory set to: {default_cookies_dir}")


class G4FProvider(BaseProvider):
    """G4F Provider - 直接使用 g4f 库
    
    Cookie/HAR 文件管理:
    - 默认读取 /app/har_and_cookies 目录
    - 支持 .har 和 .json 格式
    - 通过 /admin/files/har 和 /admin/files/cookie 接口上传
    """
    name = "g4f"

    def __init__(
        self,
        providers: list[str] | None = None,
        model_prefixes: list[str] | None = None,
        timeout: float = 30.0,
        cookies_dir: str | None = None,
    ) -> None:
        self.providers = providers or []
        self.model_prefixes = model_prefixes or []
        self.timeout = timeout
        self._client = AsyncClient()
        
        # 如果指定了 cookie 目录，设置它
        if cookies_dir and Path(cookies_dir).exists():
            g4f_cookies.set_cookies_dir(cookies_dir)
            logger.info(f"g4f cookies directory updated to: {cookies_dir}")
    
    def _get_provider(self, model: str) -> Any | None:
        """根据模型名获取对应的 g4f Provider"""
        # 根据模型前缀判断 provider
        model_lower = model.lower()
        
        if 'gpt-' in model_lower or 'chatgpt' in model_lower:
            return g4f.Provider.OpenaiChat
        elif 'qwen' in model_lower:
            return g4f.Provider.Qwen
        elif 'glm' in model_lower:
            return g4f.Provider.GLM
        elif 'grok' in model_lower:
            return g4f.Provider.Grok
        elif 'claude' in model_lower:
            return g4f.Provider.Claude
        elif 'deepseek' in model_lower:
            return g4f.Provider.DeepSeek
        
        # 默认使用 OpenaiChat
        return g4f.Provider.OpenaiChat
    
    async def list_models(self) -> list[dict]:
        """列出支持的模型"""
        # 常见模型列表
        common_models = [
            # ChatGPT
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
            # 国内模型
            "qwen-2.5", "qwen-turbo", "qwen-max", "qwen-coder",
            "kimi-k1", "kimi-1.5",
            "glm-4", "glm-4v", "glm-4-flash",
            "minimax-01",
            # 其他
            "grok-2", "grok-2-mini",
            "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
            "deepseek-chat", "deepseek-coder",
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
            )
            
            # 提取内容
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            else:
                content = str(response)
            
            # 转换为 OpenAI 格式
            return {
                "id": f"chatcmpl-g4f",
                "object": "chat.completion",
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }]
            }
        except Exception as e:
            logger.error(f"g4f chat_completions error: {e}")
            raise
