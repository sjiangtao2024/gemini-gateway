from app.config.settings import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.server.host == "0.0.0.0"
