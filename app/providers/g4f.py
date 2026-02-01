from app.providers.base import BaseProvider


class G4FProvider(BaseProvider):
    name = "g4f"

    async def chat_completions(self, *args, **kwargs):
        return {"id": "stub"}

    async def list_models(self) -> list[dict]:
        return []
