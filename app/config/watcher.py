"""配置热重载观察器"""
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from app.config.manager import ConfigManager
from app.services.logger import logger, log_manager


class ConfigReloadHandler(FileSystemEventHandler):
    """配置文件变化处理器"""
    
    def __init__(self, config_manager: ConfigManager, reload_callback=None):
        self.config_manager = config_manager
        self.reload_callback = reload_callback
        self._last_reload = 0
        self._debounce_seconds = 1  # 防抖时间
    
    def on_modified(self, event):
        if not isinstance(event, FileModifiedEvent):
            return
        
        # 只处理配置文件
        if Path(event.src_path).name != Path(self.config_manager.path).name:
            return
        
        # 防抖：避免短时间内多次重载
        now = time.time()
        if now - self._last_reload < self._debounce_seconds:
            return
        self._last_reload = now
        
        logger.info(f"Config file changed: {event.src_path}")
        
        try:
            old_settings = self.config_manager.get_settings()
            self.config_manager.reload()
            new_settings = self.config_manager.get_settings()
            
            # 处理热重载
            self._handle_reload(old_settings, new_settings)
            
            if self.reload_callback:
                self.reload_callback(old_settings, new_settings)
                
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
    
    def _handle_reload(self, old: "Settings", new: "Settings"):
        """处理具体的重载逻辑"""
        from app.config.settings import Settings
        
        # 日志级别变化
        if hasattr(old, 'logging') and hasattr(new, 'logging'):
            if old.logging.level != new.logging.level:
                prev = log_manager.set_level(new.logging.level)
                logger.info(f"Log level reloaded: {prev} -> {new.logging.level}")
        
        # 其他配置变化日志
        if hasattr(old, 'gemini') and hasattr(new, 'gemini'):
            if old.gemini.models != new.gemini.models:
                logger.info(f"Gemini models reloaded: {old.gemini.models} -> {new.gemini.models}")
            
            if old.gemini.cookie_path != new.gemini.cookie_path:
                logger.info(f"Cookie path changed: {new.gemini.cookie_path}")
        
        logger.info("Configuration reloaded successfully")


class ConfigWatcher:
    """配置热重载观察器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.observer: Observer | None = None
        self.handler: ConfigReloadHandler | None = None
    
    def start(self, reload_callback=None):
        """启动观察器"""
        if self.observer:
            return
        
        config_path = Path(self.config_manager.path)
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return
        
        watch_dir = config_path.parent
        self.handler = ConfigReloadHandler(self.config_manager, reload_callback)
        
        self.observer = Observer()
        self.observer.schedule(self.handler, str(watch_dir), recursive=False)
        self.observer.start()
        
        logger.info(f"Config watcher started for: {watch_dir}")
    
    def stop(self):
        """停止观察器"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Config watcher stopped")
