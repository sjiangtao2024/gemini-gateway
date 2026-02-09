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
        
        # 创建用于聊天的 client（默认 provider）
        self._client = AsyncClient()
        
        # 创建用于图像生成的 client，使用 OpenaiChat 作为 media_provider
        # 这样 gpt-image 会使用 ChatGPT/DALL-E 而不是 Pollinations
        self._image_client = AsyncClient(media_provider=g4f.Provider.OpenaiChat)
        
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
    
    def list_models(self) -> list[dict]:
        """列出支持的模型 - 从 g4f 库动态获取
        
        注意：此方法为同步方法，避免在模块级别使用 asyncio.run()
        """
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
    
    async def generate_images(self, prompt: str, model: str | None = None, n: int = 1, size: str = "1024x1024") -> list[dict]:
        """使用 g4f 生成图像
        
        使用 g4f.Client.images.generate() 方法生成图像
        优先使用 OpenaiChat (DALL-E 3) 生成高质量图像，需要有效的 HAR 文件
        如果没有 HAR 文件，回退到 Pollinations (免费但质量较低)
        
        Args:
            prompt: 图像生成提示词
            model: 图像模型名称（默认 'gpt-image'）
            n: 生成图像数量
            size: 图像尺寸，如 "1024x1024", "1792x1024", "1024x1792"
            
        Returns:
            图像数据列表，每个元素包含 b64_json 或 url
        """
        import base64
        import aiohttp
        import os
        from pathlib import Path
        
        # 确保使用绝对路径的 cookies 目录
        cookies_dir = "/app/har_and_cookies"
        g4f_cookies.set_cookies_dir(cookies_dir)
        
        # 使用 g4f Client 进行图像生成
        image_model = model or "gpt-image"
        
        # 检查是否有 HAR 文件（用于 OpenaiChat/DALL-E）
        # 注意：file_manager 保存 HAR 文件到 base_dir，不是 base_dir/har/
        har_dir = Path(cookies_dir)
        has_har = har_dir.exists() and any(har_dir.glob("*.har"))
        
        images = []
        
        for i in range(n):
            try:
                if has_har:
                    # 使用 OpenaiChat (DALL-E 3) 生成高质量图像
                    logger.info(f"Using OpenaiChat (DALL-E) for image generation. HAR files found.")
                    # 使用 download_media=True 让 g4f 自动下载图像到本地
                    response = await self._image_client.images.generate(
                        model=image_model,
                        prompt=prompt,
                        response_format=None,  # 让 g4f 处理下载
                        size=size,
                        download_media=True
                    )
                else:
                    # 没有 HAR 文件，使用默认 client（Pollinations，免费但质量较低）
                    logger.warning(f"No HAR file found in {har_dir} for OpenaiChat. Using Pollinations (lower quality). "
                                 f"Upload HAR file via /admin/files/har for high-quality DALL-E 3 images.")
                    response = await self._client.images.generate(
                        model=image_model,
                        prompt=prompt,
                        response_format="b64_json",
                        size=size
                    )
                
                # 提取图像数据
                if response.data and len(response.data) > 0:
                    image_data = response.data[0]
                    
                    if hasattr(image_data, 'b64_json') and image_data.b64_json:
                        # 计算图像大小
                        img_bytes = len(base64.b64decode(image_data.b64_json))
                        logger.info(f"Generated image size: {img_bytes / 1024:.2f} KB ({'DALL-E' if has_har else 'Pollinations'})")
                        images.append({"b64_json": image_data.b64_json})
                    elif hasattr(image_data, 'url') and image_data.url:
                        url = image_data.url
                        logger.info(f"Generated image URL: {url[:80]}...")
                        if url.startswith('data:image') and 'base64,' in url:
                            b64_data = url.split('base64,')[1]
                            images.append({"b64_json": b64_data})
                        elif url.startswith('/media/') or 'generated_media' in url:
                            # g4f 下载到本地的文件
                            # 路径可能是 /media/xxx.png 或 /app/generated_media/xxx.png
                            try:
                                if url.startswith('/media/'):
                                    media_path = Path('/app/generated_media') / Path(url).name
                                else:
                                    media_path = Path(url)
                                if not media_path.exists() and url.startswith('/media/'):
                                    # 尝试备用路径
                                    media_path = Path('/app') / url.lstrip('/')
                                if media_path.exists():
                                    with open(media_path, 'rb') as f:
                                        b64_data = base64.b64encode(f.read()).decode()
                                    img_bytes = len(base64.b64decode(b64_data))
                                    logger.info(f"Loaded local image: {img_bytes / 1024:.2f} KB")
                                    images.append({"b64_json": b64_data})
                                    # 清理临时文件
                                    media_path.unlink(missing_ok=True)
                                else:
                                    images.append({"url": url})
                            except Exception as e:
                                logger.error(f"Failed to read local image: {e}")
                                images.append({"url": url})
                        else:
                            images.append({"url": url})
                    else:
                        images.append({"url": "", "error": "No image data"})
                else:
                    images.append({"url": "", "error": "No image data"})
                        
            except Exception as e:
                logger.error(f"Image generation failed: {e}")
                images.append({"url": "", "error": str(e)})
        
        return images

