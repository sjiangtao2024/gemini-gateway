from pydantic import BaseModel


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8022


class Settings(BaseModel):
    server: ServerSettings = ServerSettings()
