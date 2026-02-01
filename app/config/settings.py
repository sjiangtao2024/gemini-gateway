import os

from pydantic import BaseModel


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8022


class Settings(BaseModel):
    server: ServerSettings = ServerSettings()

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.getenv("SERVER_HOST", "0.0.0.0")
        port = int(os.getenv("SERVER_PORT", "8022"))
        return cls(server=ServerSettings(host=host, port=port))
