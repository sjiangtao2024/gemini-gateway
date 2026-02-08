import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.manager import ConfigManager
from app.providers.gemini import GeminiProvider

router = APIRouter()

_config_manager: ConfigManager | None = None
_gemini: GeminiProvider | None = None


class CookieUpdate(BaseModel):
    __Secure_1PSID: str
    __Secure_1PSIDTS: str | None = None


class CookieStatus(BaseModel):
    has_psid: bool
    has_psidts: bool
    updated_at: str | None
    auto_refresh: bool


def configure(manager: ConfigManager | None, gemini: GeminiProvider | None = None) -> None:
    global _config_manager, _gemini
    _config_manager = manager
    _gemini = gemini


@router.get("/health")
async def health():
    return {"status": "healthy"}


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
