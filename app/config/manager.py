import yaml
from pathlib import Path

from app.config.settings import Settings, ServerSettings, AuthSettings, GeminiSettings, G4FSettings


class ConfigManager:
    def __init__(self, path: str):
        self.path = path
        self.settings = Settings()

    def load(self) -> None:
        """从 YAML 加载完整配置"""
        path = Path(self.path)
        if not path.exists():
            return
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        # 构建完整 Settings
        self.settings = Settings(
            server=ServerSettings(**data.get("server", {})),
            auth=AuthSettings(**data.get("auth", {})),
            gemini=GeminiSettings(**data.get("gemini", {})),
            g4f=G4FSettings(**data.get("g4f", {}))
        )
    
    def reload(self) -> None:
        """热重载配置"""
        self.load()
        # 可以在这里触发日志级别更新等
    
    def get_settings(self) -> Settings:
        return self.settings
