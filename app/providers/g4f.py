from __future__ import annotations

from typing import Any, Iterable

import httpx

from app.providers.base import BaseProvider
from app.services.model_registry import ModelRegistry


class G4FProvider(BaseProvider):
    name = "g4f"

    def __init__(
        self,
        base_url: str,
        providers: Iterable[str] | None = None,
        model_prefixes: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.providers = list(providers or [])
        self.registry = ModelRegistry(prefixes=model_prefixes or [])
        self._client = client
        self._timeout = timeout

    async def _get_json(self, path: str) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            resp = await client.get(path)
            resp.raise_for_status()
            return resp.json()

    async def _get_json_with_client(self, path: str) -> Any:
        if self._client is None:
            return await self._get_json(path)
        resp = await self._client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def list_models(self) -> list[dict]:
        providers = await self._get_json_with_client("/v1/providers")
        provider_ids = [p.get("id") for p in providers if p.get("id")]
        if self.providers:
            allowed = set(self.providers)
            provider_ids = [pid for pid in provider_ids if pid in allowed]
        models: list[str] = []
        for pid in provider_ids:
            details = await self._get_json_with_client(f"/v1/providers/{pid}")
            models.extend(details.get("models", []))
        filtered = self.registry.filter_models(models)
        return [{"id": model, "object": "model", "owned_by": "g4f"} for model in sorted(set(filtered))]

    async def chat_completions(self, *args, **kwargs) -> dict:
        return {"id": "stub"}
