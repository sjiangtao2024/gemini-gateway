from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": []}
