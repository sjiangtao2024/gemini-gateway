import os
from typing import List

from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8022


class AuthSettings(BaseModel):
    bearer_token: str = ""


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    file: str | None = None
    rotation: str = "10 MB"
    retention: str = "7 days"


class GeminiSettings(BaseModel):
    enabled: bool = True
    cookie_path: str = ""
    auto_refresh: bool = True
    models: List[str] = Field(default_factory=list)
    proxy: str | None = None
    timeout: int = 30  # 超时时间（秒）


class G4FSettings(BaseModel):
    enabled: bool = False
    providers: List[str] = Field(default_factory=list)
    model_prefixes: List[str] = Field(default_factory=list)
    timeout: float = 30.0  # 超时时间（秒）


class Settings(BaseModel):
    server: ServerSettings = ServerSettings()
    auth: AuthSettings = AuthSettings()
    logging: LoggingSettings = LoggingSettings()
    gemini: GeminiSettings = GeminiSettings()
    g4f: G4FSettings = G4FSettings()

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.getenv("SERVER_HOST", "0.0.0.0")
        port = int(os.getenv("SERVER_PORT", "8022"))
        bearer_token = os.getenv("BEARER_TOKEN", "")
        cookie_path = os.getenv("COOKIE_PATH", "")
        providers = [p for p in os.getenv("G4F_PROVIDERS", "").split(",") if p]
        prefixes = [p for p in os.getenv("G4F_MODEL_PREFIXES", "").split(",") if p]
        g4f_enabled = os.getenv("G4F_ENABLED", "false").lower() in {"1", "true", "yes"}
        log_level = os.getenv("LOG_LEVEL", "INFO")
        return cls(
            server=ServerSettings(host=host, port=port),
            auth=AuthSettings(bearer_token=bearer_token),
            logging=LoggingSettings(level=log_level),
            gemini=GeminiSettings(
                cookie_path=cookie_path,
                timeout=int(os.getenv("GEMINI_TIMEOUT", "30"))
            ),
            g4f=G4FSettings(
                enabled=g4f_enabled,
                providers=providers,
                model_prefixes=prefixes,
                timeout=float(os.getenv("G4F_TIMEOUT", "30.0"))
            ),
        )
