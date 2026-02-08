from fastapi import Request
from starlette.responses import JSONResponse

# 配置中的 API Key（由 main.py 注入）
_api_key: str = ""


def configure_auth(api_key: str = ""):
    """配置认证中间件"""
    global _api_key
    _api_key = api_key


async def auth_middleware(request: Request, call_next):
    # 公开路径白名单
    public_paths = ["/health", "/", "/static/admin.html"]
    if request.url.path.startswith("/static/") or request.url.path in public_paths:
        return await call_next(request)
    
    # 如果没有配置 API Key，跳过认证（开发模式）
    if not _api_key:
        return await call_next(request)
    
    # 尝试多种方式获取 API Key
    provided_key = None
    
    # 方式1: Authorization: Bearer <api_key>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        provided_key = auth_header[7:].strip()
    # 方式2: Authorization: <api_key> (OpenAI 风格)
    elif auth_header and " " not in auth_header:
        provided_key = auth_header.strip()
    
    # 方式3: X-API-Key header
    if not provided_key:
        provided_key = request.headers.get("X-API-Key", "").strip()
    
    # 验证 API Key
    if provided_key != _api_key:
        return JSONResponse(
            {"error": {"message": "Invalid API key", "code": "invalid_api_key"}},
            status_code=401,
        )
    
    return await call_next(request)
