from fastapi import FastAPI

from app.auth.middleware import auth_middleware
from app.config.settings import Settings
from app.providers.g4f import G4FProvider
from app.providers.gemini import GeminiProvider
from app.routes.admin import router as admin_router
from app.routes.claude import configure as configure_claude
from app.routes.claude import router as claude_router
from app.routes.openai import configure as configure_openai
from app.routes.openai import router as openai_router

settings = Settings.from_env()

app = FastAPI()
app.middleware("http")(auth_middleware)

app.include_router(openai_router)
app.include_router(claude_router)
app.include_router(admin_router)


gemini_provider = None
if settings.gemini.enabled and settings.gemini.cookie_path:
    gemini_provider = GeminiProvider(
        cookie_path=settings.gemini.cookie_path,
        model=settings.gemini.models[0] if settings.gemini.models else None,
        proxy=settings.gemini.proxy,
        auto_refresh=settings.gemini.auto_refresh,
    )

g4f_provider = None
if settings.g4f.enabled and settings.g4f.base_url:
    g4f_provider = G4FProvider(
        base_url=settings.g4f.base_url,
        providers=settings.g4f.providers,
        model_prefixes=settings.g4f.model_prefixes,
    )

configure_openai(gemini_provider, g4f_provider, settings.gemini.models)
configure_claude(settings.gemini.models, [])
