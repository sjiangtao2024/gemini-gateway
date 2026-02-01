from fastapi import FastAPI

from app.auth.middleware import auth_middleware
from app.routes.admin import router as admin_router
from app.routes.claude import router as claude_router
from app.routes.openai import router as openai_router

app = FastAPI()
app.middleware("http")(auth_middleware)
app.include_router(openai_router)
app.include_router(claude_router)
app.include_router(admin_router)
