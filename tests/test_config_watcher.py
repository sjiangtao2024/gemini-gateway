"""配置热重载测试"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.config.manager import ConfigManager
from app.config.watcher import ConfigReloadHandler, ConfigWatcher


class TestConfigReloadHandler:
    """测试配置重载处理器"""
    
    def test_handler_creation(self):
        """测试处理器创建"""
        manager = Mock(spec=ConfigManager)
        handler = ConfigReloadHandler(manager)
        
        assert handler.config_manager == manager
        assert handler._debounce_seconds == 1
    
    def test_handle_reload_detects_level_change(self):
        """测试检测到日志级别变化"""
        manager = Mock(spec=ConfigManager)
        handler = ConfigReloadHandler(manager)
        
        old = Mock()
        old.logging = Mock()
        old.logging.level = "INFO"
        
        new = Mock()
        new.logging = Mock()
        new.logging.level = "DEBUG"
        
        # 应该调用 log_manager.set_level
        with patch('app.config.watcher.log_manager') as mock_log:
            handler._handle_reload(old, new)
            mock_log.set_level.assert_called_once_with("DEBUG")


class TestConfigWatcher:
    """测试配置观察器"""
    
    def test_watcher_creation(self):
        """测试观察器创建"""
        manager = Mock(spec=ConfigManager)
        watcher = ConfigWatcher(manager)
        
        assert watcher.config_manager == manager
        assert watcher.observer is None
    
    def test_start_with_nonexistent_config(self):
        """测试配置文件不存在时启动"""
        manager = Mock(spec=ConfigManager)
        manager.path = "/nonexistent/config.yaml"
        
        watcher = ConfigWatcher(manager)
        
        # 不应该抛出异常
        watcher.start()
        assert watcher.observer is None
    
    def test_stop_without_start(self):
        """测试未启动时停止"""
        manager = Mock(spec=ConfigManager)
        watcher = ConfigWatcher(manager)
        
        # 不应该抛出异常
        watcher.stop()


class TestIntegration:
    """集成测试"""
    
    def test_config_manager_with_settings(self):
        """测试 ConfigManager 获取设置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
server:
  host: "127.0.0.1"
  port: 8080
logging:
  level: "DEBUG"
gemini:
  enabled: true
  models:
    - "gemini-2.5-pro"
""")
            f.flush()
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            manager.load()
            
            settings = manager.get_settings()
            assert settings.server.host == "127.0.0.1"
            assert settings.server.port == 8080
            assert settings.logging.level == "DEBUG"
            assert "gemini-2.5-pro" in settings.gemini.models
        finally:
            Path(config_path).unlink()
