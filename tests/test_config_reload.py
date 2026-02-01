from app.config.manager import ConfigManager


def test_config_reload(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("server:\n  host: 0.0.0.0\n  port: 8022\n")
    manager = ConfigManager(str(path))
    manager.load()
    assert manager.settings.server.port == 8022
    path.write_text("server:\n  host: 0.0.0.0\n  port: 9999\n")
    manager.reload()
    assert manager.settings.server.port == 9999
