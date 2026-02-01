from fastapi import APIRouter

router = APIRouter()

_gemini_models: list[str] = []
_g4f_models: list[str] = []


def configure(gemini_models: list[str], g4f_models: list[str]) -> None:
    global _gemini_models, _g4f_models
    _gemini_models = gemini_models
    _g4f_models = g4f_models


@router.get("/v1/claude/models")
async def list_models():
    models = _gemini_models + _g4f_models
    return {"data": [{"type": "model", "id": m, "display_name": m} for m in models]}
