from fastapi import APIRouter, HTTPException

from app.config.manager import ConfigManager

router = APIRouter()

_config_manager: ConfigManager | None = None


def configure(manager: ConfigManager | None) -> None:
    global _config_manager
    _config_manager = manager


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.post("/admin/config/reload")
async def reload_config():
    if _config_manager is None:
        raise HTTPException(status_code=503, detail="Config manager not configured")
    _config_manager.reload()
    return {"status": "success", "message": "Configuration reloaded"}
