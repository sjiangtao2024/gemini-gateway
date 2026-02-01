import os
from typing import List

from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8022


class AuthSettings(BaseModel):
    bearer_token: str = ""


class GeminiSettings(BaseModel):
    enabled: bool = True
    cookie_path: str = ""
    auto_refresh: bool = True
    models: List[str] = Field(default_factory=list)
    proxy: str | None = None


class G4FSettings(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:1337"
    providers: List[str] = Field(default_factory=list)
    model_prefixes: List[str] = Field(default_factory=list)


class Settings(BaseModel):
    server: ServerSettings = ServerSettings()
    auth: AuthSettings = AuthSettings()
    gemini: GeminiSettings = GeminiSettings()
    g4f: G4FSettings = G4FSettings()

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.getenv("SERVER_HOST", "0.0.0.0")
        port = int(os.getenv("SERVER_PORT", "8022"))
        bearer_token = os.getenv("BEARER_TOKEN", "")
        cookie_path = os.getenv("COOKIE_PATH", "")
        g4f_base_url = os.getenv("G4F_BASE_URL", "http://localhost:1337")
        providers = [p for p in os.getenv("G4F_PROVIDERS", "").split(",") if p]
        prefixes = [p for p in os.getenv("G4F_MODEL_PREFIXES", "").split(",") if p]
        g4f_enabled = os.getenv("G4F_ENABLED", "false").lower() in {"1", "true", "yes"}
        return cls(
            server=ServerSettings(host=host, port=port),
            auth=AuthSettings(bearer_token=bearer_token),
            gemini=GeminiSettings(cookie_path=cookie_path),
            g4f=G4FSettings(
                enabled=g4f_enabled,
                base_url=g4f_base_url,
                providers=providers,
                model_prefixes=prefixes,
            ),
        )
