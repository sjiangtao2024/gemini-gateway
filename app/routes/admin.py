import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.config.manager import ConfigManager
from app.providers.g4f import G4FProvider
from app.providers.gemini import GeminiProvider
from app.services.logger import LogLevel, log_manager
from app.services.file_manager import FileManager

router = APIRouter()
_config_manager: ConfigManager | None = None
_gemini: GeminiProvider | None = None
_g4f: G4FProvider | None = None
_file_manager: FileManager | None = None


class CookieUpdate(BaseModel):
    __Secure_1PSID: str
    __Secure_1PSIDTS: str | None = None


class CookieStatus(BaseModel):
    has_psid: bool
    has_psidts: bool
    updated_at: str | None
    auto_refresh: bool


class LogLevelUpdate(BaseModel):
    level: LogLevel


def configure(
    manager: ConfigManager | None,
    gemini: GeminiProvider | None = None,
    g4f: G4FProvider | None = None,
    file_manager: FileManager | None = None
) -> None:
    global _config_manager, _gemini, _g4f, _file_manager
    _config_manager = manager
    _gemini = gemini
    _g4f = g4f
    _file_manager = file_manager


@router.get("/health")
async def health():
    """健康检查，包含各 provider 状态"""
    providers = {}
    
    # Gemini 状态
    if _gemini is None:
        providers["gemini"] = "not_configured"
    else:
        try:
            # 简单检查：尝试加载 cookie
            _gemini.load_cookie_values(_gemini.cookie_path)
            providers["gemini"] = "ok"
        except Exception as e:
            providers["gemini"] = f"error: {type(e).__name__}"
    
    # g4f 状态
    if _g4f is None:
        providers["g4f"] = "not_configured"
    else:
        providers["g4f"] = "ok"
    
    # 整体状态：至少有一个 provider OK 即为 healthy
    configured = [v for v in providers.values() if v != "not_configured"]
    if configured and all(v == "ok" for v in configured):
        overall = "healthy"
    elif configured and any(v == "ok" for v in configured):
        overall = "degraded"
    else:
        overall = "unhealthy"
    
    return {
        "status": overall,
        "version": "1.0.0",
        "providers": providers
    }


@router.post("/admin/config/reload")
async def reload_config():
    if _config_manager is None:
        raise HTTPException(status_code=503, detail="Config manager not configured")
    _config_manager.reload()
    return {"status": "success", "message": "Configuration reloaded"}


@router.post("/admin/cookies")
async def update_cookies(cookies: CookieUpdate):
    """更新 Gemini Cookie，立即生效"""
    global _gemini

    if _gemini is None:
        raise HTTPException(status_code=503, detail="Gemini provider not configured")

    # 保存到 cookie 文件
    cookie_data = {
        "__Secure-1PSID": cookies.__Secure_1PSID,
        "__Secure-1PSIDTS": cookies.__Secure_1PSIDTS or "",
        "updated_at": datetime.now().isoformat()
    }

    Path(_gemini.cookie_path).write_text(
        json.dumps(cookie_data, indent=2),
        encoding="utf-8"
    )

    # 重新初始化 provider
    _gemini._initialized = False
    _gemini._client = None
    await _gemini._ensure_client()

    return {
        "status": "success",
        "message": "Cookies updated and provider reloaded",
        "timestamp": cookie_data["updated_at"]
    }


@router.get("/admin/cookies/status")
async def cookie_status():
    """查看 Cookie 状态（脱敏）"""
    global _gemini

    if _gemini is None:
        return CookieStatus(
            has_psid=False,
            has_psidts=False,
            updated_at=None,
            auto_refresh=False
        )

    try:
        cookie_path = _gemini.cookie_path
        if not Path(cookie_path).exists():
            return CookieStatus(
                has_psid=False,
                has_psidts=False,
                updated_at=None,
                auto_refresh=getattr(_gemini, 'auto_refresh', True)
            )

        data = json.loads(Path(cookie_path).read_text(encoding="utf-8"))
        return CookieStatus(
            has_psid=bool(data.get("__Secure-1PSID")),
            has_psidts=bool(data.get("__Secure-1PSIDTS")),
            updated_at=data.get("updated_at"),
            auto_refresh=getattr(_gemini, 'auto_refresh', True)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read cookie status: {e}")


@router.post("/admin/logging")
async def set_log_level(payload: LogLevelUpdate):
    """切换日志级别 (DEBUG/INFO/WARNING/ERROR)"""
    previous = log_manager.set_level(payload.level)
    return {
        "status": "success",
        "level": payload.level,
        "previous_level": previous
    }


@router.post("/admin/files/har")
async def upload_har(
    file: UploadFile = File(...),
    provider: str | None = Form(None)
):
    """上传 HAR 文件（自动验证）
    
    provider: 可选，如 'openai', 'google' 等，用于命名文件
    
    验证内容：
    - 是否为有效的 JSON 格式
    - 是否包含标准的 HAR 结构 (log.entries)
    - 对于 ChatGPT HAR，检查是否包含 authorization 头或 cookies
    """
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    try:
        result = await _file_manager.save_har(file, provider)
        return {
            "status": "success",
            "message": result.get("validation", {}).get("message", "HAR file uploaded successfully"),
            "data": result
        }
    except ValueError as e:
        # 验证失败，返回详细的错误信息
        error_msg = str(e)
        if "HAR validation failed" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg.replace("HAR validation failed: ", ""))
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save HAR: {e}")


@router.post("/admin/files/cookie")
async def upload_cookie(
    file: UploadFile = File(...),
    domain: str | None = Form(None)
):
    """上传 Cookie JSON 文件
    
    domain: 可选，如 'kimi.com', 'qwen.com' 等，用于命名文件
    """
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    try:
        result = await _file_manager.save_cookie(file, domain)
        return {
            "status": "success",
            "message": "Cookie file uploaded successfully",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookie: {e}")


@router.get("/admin/files")
async def list_files():
    """列出所有 HAR 和 Cookie 文件"""
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    return _file_manager.list_files()


@router.get("/admin/files/{file_type}/{filename}")
async def get_file_info(file_type: str, filename: str):
    """获取文件信息"""
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    if file_type not in ["har", "cookie"]:
        raise HTTPException(status_code=400, detail="file_type must be 'har' or 'cookie'")
    
    info = _file_manager.get_file_info(file_type, filename)
    if info:
        return {
            "status": "success",
            "data": info
        }
    else:
        raise HTTPException(status_code=404, detail="File not found")


@router.delete("/admin/files/{file_type}/{filename}")
async def delete_file(file_type: str, filename: str):
    """删除文件
    
    file_type: 'har' 或 'cookie'
    """
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    if file_type not in ["har", "cookie"]:
        raise HTTPException(status_code=400, detail="file_type must be 'har' or 'cookie'")
    
    success = _file_manager.delete_file(file_type, filename)
    if success:
        return {
            "status": "success",
            "message": f"{filename} deleted successfully"
        }
    else:
        raise HTTPException(status_code=404, detail="File not found")
