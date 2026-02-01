import base64
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.providers.g4f import G4FProvider
from app.providers.gemini import GeminiProvider
from app.services.stream import stream_chunks

router = APIRouter()

_gemini: GeminiProvider | None = None
_g4f: G4FProvider | None = None
_gemini_models: list[str] = []


def configure(gemini: GeminiProvider | None, g4f: G4FProvider | None, gemini_models: list[str]) -> None:
    global _gemini, _g4f, _gemini_models
    _gemini = gemini
    _g4f = g4f
    _gemini_models = gemini_models


def _is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-")


@router.get("/v1/models")
async def list_models():
    data = [
        {"id": model, "object": "model", "owned_by": "google"}
        for model in _gemini_models
    ]
    if _g4f is not None:
        try:
            data.extend(await _g4f.list_models())
        except Exception:
            pass
    return {"object": "list", "data": data}


@router.post("/v1/chat/completions")
async def chat_completions(payload: dict):
    model = payload.get("model", "")
    messages = payload.get("messages", [])
    stream = bool(payload.get("stream"))
    if _is_gemini_model(model):
        if _gemini is None:
            raise HTTPException(status_code=503, detail="Gemini provider not configured")
        result = await _gemini.chat_completions(messages=messages, model=model)
        text = result.get("text", "")
        if stream:
            return StreamingResponse((chunk for chunk in stream_chunks([text])), media_type="text/event-stream")
        return {
            "id": "chatcmpl-gemini",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        }
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    if stream:
        raise HTTPException(status_code=501, detail="Streaming via g4f not implemented")
    return await _g4f.chat_completions(payload)


@router.post("/v1/images")
async def images(payload: dict):
    model = payload.get("model", "")
    prompt = payload.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt required")
    if not _is_gemini_model(model):
        raise HTTPException(status_code=501, detail="Image generation only supported for Gemini models")
    if _gemini is None:
        raise HTTPException(status_code=503, detail="Gemini provider not configured")
    images = await _gemini.generate_images(prompt=prompt, model=model)
    data: list[dict[str, Any]] = []
    for image in images:
        if isinstance(image, bytes):
            encoded = base64.b64encode(image).decode("utf-8")
        else:
            encoded = str(image)
        data.append({"b64_json": encoded})
    return {"created": 0, "data": data}
