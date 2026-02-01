import os

from app.config.settings import Settings


def test_env_override():
    os.environ["SERVER_HOST"] = "127.0.0.1"
    settings = Settings.from_env()
    assert settings.server.host == "127.0.0.1"
