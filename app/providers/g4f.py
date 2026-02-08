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
        """列出支持的模型 - 从 g4f 库动态获取"""
        models = []
        
        # 从 g4f.Provider.OpenaiChat 获取最新模型列表
        try:
            from g4f.Provider.openai.models import models as openai_models
            models.extend(openai_models)
        except Exception:
            # 如果获取失败，使用默认列表
            models = [
                "gpt-5-2", "gpt-5-2-instant", "gpt-5-2-thinking",
                "gpt-5-1", "gpt-5-1-instant", "gpt-5-1-thinking",
                "gpt-5", "gpt-5-instant", "gpt-5-thinking",
                "gpt-4", "gpt-4.1", "gpt-4.1-mini", "gpt-4.5",
                "gpt-4o", "gpt-4o-mini",
                "o1", "o1-mini", "o3-mini", "o3-mini-high", "o4-mini", "o4-mini-high",
            ]
        
        # 根据配置的 prefixes 过滤
        if self.model_prefixes:
            filtered = [m for m in models 
                       if any(m.startswith(p) for p in self.model_prefixes)]
        else:
            filtered = models
        
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
        """使用 g4f 生成图像
        
        使用 BingCreateImages (DALL-E 3) 或 OpenaiChat 生成图像
        
        Args:
            prompt: 图像生成提示词
            model: 图像模型名称（如 'dall-e-3', 'gpt-image'）
            n: 生成图像数量
            
        Returns:
            图像数据列表，每个元素包含 b64_json
        """
        import base64
        import aiohttp
        
        # 支持的图像模型映射
        image_model = model or "dall-e-3"
        
        # 选择 provider
        if image_model in ["dall-e-3", "dalle3", "dall-e"]:
            provider = g4f.Provider.BingCreateImages
        else:
            # 使用 OpenaiChat 的图像功能
            provider = g4f.Provider.OpenaiChat
        
        images = []
        
        for i in range(n):
            try:
                # 使用 create_async 生成图像
                if hasattr(provider, 'create_async'):
                    response_text = await provider.create_async(
                        model=image_model,
                        messages=[{"role": "user", "content": f"Create an image: {prompt}"}],
                        timeout=int(self.timeout),
                    )
                    
                    # 从响应中提取图像 URL
                    import re
                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:png|jpg|jpeg|gif|webp)'
                    urls = re.findall(url_pattern, response_text, re.IGNORECASE)
                    
                    if urls:
                        # 下载图像并转换为 base64
                        async with aiohttp.ClientSession() as session:
                            async with session.get(urls[0], timeout=30) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    b64_data = base64.b64encode(image_bytes).decode('utf-8')
                                    images.append({"b64_json": b64_data})
                                else:
                                    images.append({"url": urls[0]})
                    else:
                        # 如果没有找到 URL，可能是 base64 数据或其他格式
                        if response_text.startswith('data:image'):
                            # 已经是 data URI
                            images.append({"url": response_text})
                        else:
                            logger.warning(f"No image found in response: {response_text[:100]}")
                            images.append({"url": "", "error": "No image generated"})
                else:
                    #  Fallback: 使用 chat.completions
                    response = await self._client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": f"Generate an image: {prompt}"}],
                        provider=provider,
                    )
                    
                    content = ""
                    if hasattr(response, 'choices') and response.choices:
                        content = response.choices[0].message.content
                    
                    # 尝试提取图像 URL
                    import re
                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:png|jpg|jpeg|gif|webp)'
                    urls = re.findall(url_pattern, content, re.IGNORECASE)
                    
                    if urls:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(urls[0], timeout=30) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    b64_data = base64.b64encode(image_bytes).decode('utf-8')
                                    images.append({"b64_json": b64_data})
                                else:
                                    images.append({"url": urls[0]})
                    else:
                        images.append({"url": "", "error": "No image generated"})
                        
            except Exception as e:
                logger.error(f"Image generation attempt {i+1} failed: {e}")
                images.append({"url": "", "error": str(e)})
        
        return images
