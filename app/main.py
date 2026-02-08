import asyncio
import os
from pathlib import Path

from fastapi import FastAPI

from app.auth.middleware import auth_middleware
from app.middlewares.logging import RequestLoggingMiddleware
from app.config.manager import ConfigManager
from app.config.watcher import ConfigWatcher
from app.config.settings import Settings
from app.providers.g4f import G4FProvider
from app.providers.gemini import GeminiProvider
from app.routes.admin import configure as configure_admin
from app.routes.admin import router as admin_router
from app.routes.claude import configure as configure_claude
from app.routes.claude import router as claude_router
from app.routes.files import configure as configure_files
from app.routes.files import router as files_router
from app.routes.openai import configure as configure_openai
from app.routes.openai import router as openai_router
from app.services.logger import logger, log_manager

config_manager = None
config_watcher = None
config_path = os.getenv("CONFIG_PATH", "")
if config_path and Path(config_path).exists():
    config_manager = ConfigManager(config_path)
    config_manager.load()
    
    # 如果有日志配置，设置文件日志
    settings = config_manager.get_settings()
    if settings.logging.file:
        log_manager.setup_file_logging(
            settings.logging.file,
            settings.logging.rotation,
            settings.logging.retention
        )
    
    # 启动配置热重载观察器
    config_watcher = ConfigWatcher(config_manager)
    config_watcher.start()

# 优先使用配置文件中的设置，否则使用环境变量
if config_manager:
    settings = config_manager.get_settings()
else:
    settings = Settings.from_env()

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
app.middleware("http")(auth_middleware)

app.include_router(openai_router)
app.include_router(claude_router)
app.include_router(admin_router)
app.include_router(files_router)


gemini_provider = None
if settings.gemini.enabled and settings.gemini.cookie_path:
    gemini_provider = GeminiProvider(
        cookie_path=settings.gemini.cookie_path,
        model=settings.gemini.models[0] if settings.gemini.models else None,
        proxy=settings.gemini.proxy,
        auto_refresh=settings.gemini.auto_refresh,
        timeout=settings.gemini.timeout,
    )

g4f_provider = None
if settings.g4f.enabled and settings.g4f.base_url:
    g4f_provider = G4FProvider(
        base_url=settings.g4f.base_url,
        providers=settings.g4f.providers,
        model_prefixes=settings.g4f.model_prefixes,
        timeout=settings.g4f.timeout,
    )

g4f_models: list[str] = []
if g4f_provider is not None:
    try:
        g4f_models = [m["id"] for m in (asyncio.run(g4f_provider.list_models()) or [])]
    except Exception:
        g4f_models = []

configure_openai(gemini_provider, g4f_provider, settings.gemini.models)
configure_claude(settings.gemini.models, g4f_models, gemini_provider, g4f_provider)
configure_files(gemini_provider)
configure_admin(config_manager, gemini_provider, g4f_provider)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global config_watcher
    if config_watcher:
        config_watcher.stop()
        logger.info("Application shutdown complete")
