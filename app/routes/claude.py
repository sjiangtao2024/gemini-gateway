from fastapi import APIRouter, HTTPException

from app.providers.g4f import G4FProvider

router = APIRouter()

_gemini_models: list[str] = []
_g4f_models: list[str] = []
_g4f: G4FProvider | None = None


def configure(gemini_models: list[str], g4f_models: list[str], g4f: G4FProvider | None) -> None:
    global _gemini_models, _g4f_models, _g4f
    _gemini_models = gemini_models
    _g4f_models = g4f_models
    _g4f = g4f


def _is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-")


@router.get("/v1/claude/models")
async def list_models():
    models = _gemini_models + _g4f_models
    return {"data": [{"type": "model", "id": m, "display_name": m} for m in models]}


@router.post("/v1/messages")
async def messages(payload: dict):
    model = payload.get("model", "")
    if _is_gemini_model(model):
        raise HTTPException(status_code=501, detail="Gemini not supported for Claude protocol")
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    return await _g4f.chat_completions(payload)
