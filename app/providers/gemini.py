from app.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, cookie_path: str):
        if not cookie_path:
            raise ValueError("cookie_path required")
        self.cookie_path = cookie_path

    async def chat_completions(self, *args, **kwargs):
        return {"id": "stub"}

    async def list_models(self) -> list[dict]:
        return []
