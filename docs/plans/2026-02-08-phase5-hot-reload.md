# Phase 5: 配置热重载实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 实现配置文件热重载，使用 watchdog 监听配置文件变化并自动重新加载

**Architecture:** 
- 使用 watchdog 监听配置文件目录
- 配置文件变化时自动重新加载
- 支持热重载的范围：日志级别、Cookie 路径、模型列表等

**Tech Stack:** FastAPI, watchdog, threading

---

## 背景信息

### 当前 ConfigManager 状态

```python
class ConfigManager:
    def __init__(self, path: str):
        self.path = path
        self.settings = Settings()

    def load(self) -> None:
        """从 YAML 加载完整配置"""
        # ... 加载逻辑

    def reload(self) -> None:
        """热重载配置"""
        self.load()
```

### 需要热重载的配置项

| 配置项 | 热重载支持 | 实现方式 |
|--------|-----------|---------|
| `logging.level` | ✅ | 调用 log_manager.set_level() |
| `auth.bearer_token` | ✅ | 更新内存中的配置 |
| `gemini.cookie_path` | ✅ | 重新初始化 Provider |
| `gemini.models` | ✅ | 更新模型列表 |
| `g4f.*` | ✅ | 更新配置 |
| `server.host/port` | ❌ | 需要重启服务 |

---

## Task 1: 创建热重载观察器

**Files:**
- Create: `app/config/watcher.py`

**Step 1: Create watcher module**

```python
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
        # 日志级别变化
        if old.logging.level != new.logging.level:
            prev = log_manager.set_level(new.logging.level)
            logger.info(f"Log level reloaded: {prev} -> {new.logging.level}")
        
        # 其他配置变化日志
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
```

**Step 2: Test imports**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -c "from app.config.watcher import ConfigWatcher; print('Import OK')"
```

**Step 3: Commit**

```bash
git add app/config/watcher.py
git commit -m "feat(config): add config hot-reload watcher

- ConfigWatcher class using watchdog
- ConfigReloadHandler with debounce
- Auto-reload logging level on config change"
```

---

## Task 2: 扩展 Logging 配置支持

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/services/logger.py`

**Step 1: Add LoggingSettings to settings.py**

```python
class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    file: str | None = None
    rotation: str = "10 MB"
    retention: str = "7 days"
```

**Step 2: Update Settings class**

```python
class Settings(BaseModel):
    server: ServerSettings = ServerSettings()
    auth: AuthSettings = AuthSettings()
    logging: LoggingSettings = LoggingSettings()  # 新增
    gemini: GeminiSettings = GeminiSettings()
    g4f: G4FSettings = G4FSettings()
```

**Step 3: Update from_env**

```python
log_level = os.getenv("LOG_LEVEL", "INFO")

return cls(
    server=ServerSettings(host=host, port=port),
    auth=AuthSettings(bearer_token=bearer_token),
    logging=LoggingSettings(level=log_level),  # 新增
    gemini=GeminiSettings(
        cookie_path=cookie_path,
        timeout=int(os.getenv("GEMINI_TIMEOUT", "30"))
    ),
    g4f=G4FSettings(
        enabled=g4f_enabled,
        base_url=g4f_base_url,
        providers=providers,
        model_prefixes=prefixes,
        timeout=float(os.getenv("G4F_TIMEOUT", "30.0"))
    ),
)
```

**Step 4: Update logger.py to support file logging**

```python
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
```

**Step 5: Test imports**

```bash
python3 -c "from app.config.settings import Settings; print('Settings import OK')"
python3 -c "from app.services.logger import log_manager; print('Logger import OK')"
```

**Step 6: Commit**

```bash
git add app/config/settings.py app/services/logger.py
git commit -m "feat(logging): add file logging and structured settings

- Add LoggingSettings with file, rotation, retention
- Support file logging in LogManager
- LOG_LEVEL environment variable support"
```

---

## Task 3: 集成热重载到主应用

**Files:**
- Modify: `app/main.py`

**Step 1: Add watcher initialization**

在文件顶部添加导入：
```python
from app.config.watcher import ConfigWatcher
```

在 `config_manager` 创建后添加 watcher：

```python
config_manager = None
config_watcher = None
config_path = os.getenv("CONFIG_PATH", "")
if config_path and Path(config_path).exists():
    config_manager = ConfigManager(config_path)
    config_manager.load()
    
    # 如果有日志配置，设置文件日志
    settings = config_manager.get_settings()
    if settings.logging.file:
        log_manager.setup_file_logging(
            settings.logging.file,
            settings.logging.rotation,
            settings.logging.retention
        )
    
    # 启动配置热重载观察器
    config_watcher = ConfigWatcher(config_manager)
    config_watcher.start()
```

**Step 2: Add shutdown handler**

在文件末尾添加（在 FastAPI 事件处理中）：

```python
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global config_watcher
    if config_watcher:
        config_watcher.stop()
        logger.info("Application shutdown complete")
```

**Step 3: Update settings initialization**

修改 settings 创建逻辑，优先使用 config_manager 的配置：

```python
# 优先使用配置文件中的设置，否则使用环境变量
if config_manager:
    settings = config_manager.get_settings()
else:
    settings = Settings.from_env()
```

**Step 4: Test imports**

```bash
python3 -c "from app.main import app; print('Main import OK')"
```

**Step 5: Commit**

```bash
git add app/main.py
git commit -m "feat(main): integrate config hot-reload watcher

- Start ConfigWatcher on application startup
- Set up file logging from config
- Stop watcher on application shutdown"
```

---

## Task 4: 更新部署文档

**Files:**
- Modify: `docs/config-examples.md`

**Step 1: Add logging config example**

在 `config.yaml` 示例中添加 logging 部分：

```yaml
# ============================================
# AI-Gateway 配置文件
# ============================================

server:
  host: "0.0.0.0"
  port: 8022

auth:
  bearer_token: "your-secure-token-here"

logging:
  level: "INFO"        # DEBUG, INFO, WARNING, ERROR
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
  file: "/app/logs/gateway.log"  # 可选：文件日志路径
  rotation: "10 MB"    # 日志轮转大小
  retention: "7 days"  # 日志保留时间

gemini:
  enabled: true
  cookie_path: "/app/cookies/gemini.json"
  auto_refresh: true
  timeout: 30          # 请求超时（秒）
  models:
    - "gemini-2.5-pro"
    - "gemini-2.5-flash"

g4f:
  enabled: false
  base_url: "http://localhost:1337"
  timeout: 30.0        # 请求超时（秒）
  providers: []
  model_prefixes: []
```

**Step 2: Add hot-reload documentation**

添加说明：

```markdown
## 热重载

以下配置项支持热重载（修改后无需重启服务）：

| 配置项 | 生效方式 |
|--------|---------|
| `logging.level` | 立即生效 |
| `logging.file` | 需手动重载或下次启动 |
| `auth.bearer_token` | 立即生效 |
| `gemini.models` | 立即生效 |
| `gemini.cookie_path` | 需调用 /admin/cookies/reload |
| `gemini.timeout` | 下次请求生效 |
| `g4f.timeout` | 下次请求生效 |

注意：`server.host` 和 `server.port` 修改后需要重启服务。
```

**Step 3: Commit**

```bash
git add docs/config-examples.md
git commit -m "docs(config): add logging and hot-reload documentation

- Add logging configuration example
- Document hot-reload capabilities
- Add timeout configuration"
```

---

## Task 5: 添加热重载测试

**Files:**
- Create: `tests/test_config_watcher.py`

**Step 1: Create test file**

```python
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
        from app.config.settings import Settings, LoggingSettings
        
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
```

**Step 2: Run tests**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -m pytest tests/test_config_watcher.py -v
```

**Step 3: Commit**

```bash
git add tests/test_config_watcher.py
git commit -m "test(config): add config watcher tests

- Test ConfigReloadHandler
- Test ConfigWatcher lifecycle
- Test integration with ConfigManager"
```

---

## 验证清单

完成所有任务后验证：

```bash
# 1. 检查所有导入
python3 -c "
from app.config.watcher import ConfigWatcher
from app.config.settings import Settings
print('✅ All imports OK')
"

# 2. 运行测试
python3 -m pytest tests/test_config_watcher.py -v

# 3. 检查主应用
python3 -c "from app.main import app; print('✅ Main app OK')"

# 4. 验证 watchdog 安装
python3 -c "import watchdog; print(f'watchdog version: {watchdog.__version__}')"
```

---

## 提交历史

1. `feat(config): add config hot-reload watcher`
2. `feat(logging): add file logging and structured settings`
3. `feat(main): integrate config hot-reload watcher`
4. `docs(config): add logging and hot-reload documentation`
5. `test(config): add config watcher tests`

---

## 预期结果

完成后：

1. **配置文件修改自动生效**：修改 `config.yaml` 后，日志级别等配置自动更新
2. **文件日志支持**：配置 `logging.file` 后，日志同时输出到文件
3. **零停机配置更新**：无需重启服务即可更新大部分配置
