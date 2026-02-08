import sys
from typing import Literal
from loguru import logger

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

class LogManager:
    def __init__(self, level: LogLevel = "INFO"):
        self.current_level = level
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        logger.remove()
        logger.add(
            sys.stdout,
            level=self.current_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
            colorize=True
        )
    
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

def setup_logging(level: str = "INFO") -> None:
    """初始化日志（兼容旧代码）"""
    log_manager.set_level(level)  # type: ignore
