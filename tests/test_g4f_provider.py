import httpx
import pytest

from app.providers.g4f import G4FProvider


@pytest.mark.anyio
async def test_list_models_filters_prefixes():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/providers":
            return httpx.Response(200, json=[{"id": "Qwen"}, {"id": "Other"}])
        if request.url.path == "/v1/providers/Qwen":
            return httpx.Response(200, json={"models": ["qwen-2.5", "gpt-4o"]})
        if request.url.path == "/v1/providers/Other":
            return httpx.Response(200, json={"models": ["foo-1"]})
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://g4f") as client:
        provider = G4FProvider(
            base_url="http://g4f",
            providers=["Qwen"],
            model_prefixes=["qwen-"],
            client=client,
        )
        models = await provider.list_models()

    assert [m["id"] for m in models] == ["qwen-2.5"]


@pytest.mark.anyio
async def test_chat_completions_proxy():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(200, json={"id": "chatcmpl-test"})
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://g4f") as client:
        provider = G4FProvider(base_url="http://g4f", client=client)
        resp = await provider.chat_completions({"model": "qwen-2.5", "messages": []})

    assert resp["id"] == "chatcmpl-test"
