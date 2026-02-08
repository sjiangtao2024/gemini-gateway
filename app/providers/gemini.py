import json
from pathlib import Path
from typing import Any, Iterable

from gemini_webapi import GeminiClient

from app.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(
        self,
        cookie_path: str,
        model: str | None = None,
        proxy: str | None = None,
        timeout: int = 30,
        auto_close: bool = False,
        close_delay: int = 300,
        auto_refresh: bool = True,
    ) -> None:
        if not cookie_path:
            raise ValueError("cookie_path required")
        self.cookie_path = cookie_path
        self.model = model
        self.proxy = proxy
        self.timeout = timeout
        self.auto_close = auto_close
        self.close_delay = close_delay
        self.auto_refresh = auto_refresh
        self._client: GeminiClient | None = None
        self._initialized = False

    @staticmethod
    def load_cookie_values(path: str) -> tuple[str, str]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        psid = data.get("__Secure-1PSID")
        psidts = data.get("__Secure-1PSIDTS")
        if not psid:
            raise ValueError("__Secure-1PSID missing")
        if psidts is None:
            psidts = ""
        return psid, psidts

    async def _ensure_client(self) -> GeminiClient:
        if self._client is None:
            psid, psidts = self.load_cookie_values(self.cookie_path)
            self._client = GeminiClient(psid, psidts, proxy=self.proxy)
        if not self._initialized:
            await self._client.init(
                timeout=self.timeout,
                auto_close=self.auto_close,
                close_delay=self.close_delay,
                auto_refresh=self.auto_refresh,
            )
            self._initialized = True
        return self._client

    @staticmethod
    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "\n".join(part for part in parts if part)
        return ""

    @classmethod
    def _messages_to_prompt(cls, messages: Iterable[dict]) -> str:
        lines: list[str] = []
        for message in messages:
            role = message.get("role", "user")
            text = cls._extract_text(message.get("content"))
            if text:
                lines.append(f"{role}: {text}")
        return "\n".join(lines)

    async def chat_completions(self, messages: list[dict], model: str | None = None, **kwargs) -> dict:
        client = await self._ensure_client()
        prompt = self._messages_to_prompt(messages)
        selected_model = model or self.model
        if selected_model:
            response = await client.generate_content(prompt, model=selected_model)
        else:
            response = await client.generate_content(prompt)
        return {"text": response.text, "images": response.images, "raw": response}

    async def chat_completions_with_files(
        self,
        messages: list[dict],
        text: str,
        files: list[str],
        model: str | None = None
    ) -> dict:
        """支持文件上传的聊天完成"""
        client = await self._ensure_client()
        
        # 构建提示词（包含历史消息上下文）
        context = self._messages_to_prompt(messages)
        if context:
            prompt = f"{context}\n\n{text}"
        else:
            prompt = text
        
        selected_model = model or self.model
        if selected_model:
            response = await client.generate_content(prompt, files=files, model=selected_model)
        else:
            response = await client.generate_content(prompt, files=files)
        
        return {"text": response.text, "images": response.images, "raw": response}

    async def generate_images(self, prompt: str, model: str | None = None) -> list[Any]:
        client = await self._ensure_client()
        selected_model = model or self.model
        if selected_model:
            response = await client.generate_content(prompt, model=selected_model)
        else:
            response = await client.generate_content(prompt)
        return list(response.images)

    async def list_models(self) -> list[dict]:
        return []
