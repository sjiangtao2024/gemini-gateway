from fastapi import Request
from starlette.responses import JSONResponse


async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        return JSONResponse(
            {"error": {"message": "Invalid token", "code": "invalid_token"}},
            status_code=401,
        )
    return await call_next(request)
