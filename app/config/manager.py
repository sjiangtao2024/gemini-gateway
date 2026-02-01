import yaml

from app.config.settings import Settings, ServerSettings


class ConfigManager:
    def __init__(self, path: str):
        self.path = path
        self.settings = Settings()

    def load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        server = data.get("server", {})
        self.settings = Settings(server=ServerSettings(**server))

    def reload(self) -> None:
        self.load()
