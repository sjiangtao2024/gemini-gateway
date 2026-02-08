from fastapi import Request
from starlette.responses import JSONResponse


async def auth_middleware(request: Request, call_next):
    # 公开路径白名单
    public_paths = ["/health", "/", "/static/admin.html"]
    if request.url.path.startswith("/static/") or request.url.path in public_paths:
        return await call_next(request)
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        return JSONResponse(
            {"error": {"message": "Invalid token", "code": "invalid_token"}},
            status_code=401,
        )
    return await call_next(request)
