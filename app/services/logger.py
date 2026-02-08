import sys
from pathlib import Path
from typing import Literal
from loguru import logger

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

class LogManager:
    def __init__(self, level: LogLevel = "INFO"):
        self.current_level = level
        self.file_handler_id = None
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        logger.remove()
        # Console handler
        logger.add(
            sys.stdout,
            level=self.current_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
            colorize=True
        )
    
    def setup_file_logging(self, file_path: str, rotation: str = "10 MB", retention: str = "7 days"):
        """配置文件日志"""
        # 移除旧的文件 handler
        if self.file_handler_id is not None:
            try:
                logger.remove(self.file_handler_id)
            except:
                pass
        
        # 确保目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 添加新的文件 handler
        self.file_handler_id = logger.add(
            file_path,
            level=self.current_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            rotation=rotation,
            retention=retention,
            encoding="utf-8"
        )
        logger.info(f"File logging enabled: {file_path}")
    
    def set_level(self, level: LogLevel) -> str:
        """切换日志级别，返回之前的级别"""
        previous = self.current_level
        self.current_level = level.upper()  # type: ignore
        self._setup_logger()
        logger.info(f"Log level changed from {previous} to {level}")
        return previous
    
    def get_level(self) -> str:
        return self.current_level

# 全局实例
log_manager = LogManager("INFO")

def setup_logging(level: str = "INFO", file_path: str | None = None, rotation: str = "10 MB", retention: str = "7 days") -> None:
    """初始化日志（兼容旧代码）"""
    log_manager.set_level(level)  # type: ignore
    if file_path:
        log_manager.setup_file_logging(file_path, rotation, retention)
