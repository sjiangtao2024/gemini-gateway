from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/claude/models")
async def list_models():
    return {"data": []}
