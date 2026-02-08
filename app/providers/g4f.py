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
    
    async def generate_images(self, prompt: str, model: str | None = None, n: int = 1) -> list[dict]:
        """使用 ChatGPT (g4f) 生成图像
        
        注意: ChatGPT 的图像生成是通过聊天界面触发的，
        我们发送特定的图像生成请求，然后解析返回的图像链接。
        
        Args:
            prompt: 图像生成提示词
            model: 图像模型名称（默认使用 ChatGPT 的 gpt-image）
            n: 生成图像数量
            
        Returns:
            图像数据列表，每个元素包含 url
        """
        try:
            images = []
            
            for _ in range(n):
                # 使用 ChatGPT 生成图像
                # 发送图像生成请求
                response = await self._client.chat.completions.create(
                    model="gpt-4o",  # 使用支持图像的模型
                    messages=[
                        {"role": "user", "content": f"Generate an image: {prompt}"}
                    ],
                    provider=g4f.Provider.OpenaiChat,
                )
                
                # 从响应中提取图像 URL
                # ChatGPT 通常会在回复中包含图像链接
                content = ""
                if hasattr(response, 'choices') and response.choices:
                    content = response.choices[0].message.content
                
                # 尝试从内容中提取图像 URL
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:png|jpg|jpeg|gif|webp)'
                urls = re.findall(url_pattern, content, re.IGNORECASE)
                
                if urls:
                    images.append({"url": urls[0]})
                else:
                    # 如果没有找到 URL，返回空内容提示
                    logger.warning(f"No image URL found in ChatGPT response: {content[:100]}")
                    images.append({"url": "", "error": "No image generated"})
            
            return images[:n]
        except Exception as e:
            logger.error(f"ChatGPT image generation error: {e}")
            raise
