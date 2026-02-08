# AI-Gateway 重命名 + Phase 1 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 将项目从 Gemini-Gateway 重命名为 AI-Gateway，并实现 Phase 1 的管理接口功能

**Architecture:** 统一 AI 网关支持多 Provider（Gemini + g4f），提供 OpenAI/Claude 双协议兼容，非流式响应

**Tech Stack:** FastAPI, Python 3.11, gemini-webapi, g4f, Pydantic, Loguru

---

## 背景信息

### 项目结构
```
app/
├── main.py              # FastAPI 入口
├── auth/middleware.py   # 认证中间件
├── config/
│   ├── settings.py      # Pydantic 配置
│   └── manager.py       # 配置管理
├── providers/
│   ├── base.py          # Provider 基类
│   ├── gemini.py        # Gemini 实现
│   └── g4f.py           # g4f 实现
├── routes/
│   ├── openai.py        # OpenAI 协议
│   ├── claude.py        # Claude 协议
│   └── admin.py         # 管理接口
└── services/
    ├── logger.py        # 日志服务
    ├── model_registry.py
    └── stream.py
```

### 当前 Admin 路由状态
- `/health` - 已实现，返回简单状态
- `/admin/config/reload` - 已实现，但 ConfigManager 不完整
- `/admin/cookies` - ❌ 缺失
- `/admin/cookies/status` - ❌ 缺失
- `/admin/logging` - ❌ 缺失

### Provider 配置
- Gemini: cookie_path, auto_refresh, models, proxy
- g4f: base_url, providers, model_prefixes

---

## Task 1: 项目重命名

**Files:**
- Modify: `README.md`
- Modify: `docker-compose.yml`
- Modify: `docs/architecture.md`
- Modify: `docs/api-spec.md`
- Modify: `docs/config-examples.md`
- Modify: `docs/deployment.md`
- Modify: `docs/troubleshooting.md`

**Step 1: 更新 README.md**

将所有 "Gemini-Gateway" 替换为 "AI-Gateway"，更新描述强调多 Provider 支持。

```markdown
# AI-Gateway

一个支持 OpenAI 和 Claude 双协议的 AI 模型网关，统一接入 Gemini、ChatGPT 及其他开源模型。
```

**Step 2: 更新 docker-compose.yml**

```yaml
services:
  ai-gateway:  # 原 gemini-gateway
    container_name: ai-gateway
    # ... rest unchanged
```

**Step 3: 更新各文档中的项目名称**

使用 sed 批量替换：
```bash
find docs/ -name "*.md" -exec sed -i 's/Gemini-Gateway/AI-Gateway/g' {} +
find docs/ -name "*.md" -exec sed -i 's/gemini-gateway/ai-gateway/g' {} +
```

**Step 4: 验证替换**

```bash
grep -r "Gemini-Gateway\|gemini-gateway" --include="*.md" --include="*.yml" --include="*.yaml" .
# 应该只匹配到历史记录或 git 相关，文档中不应再有
```

**Step 5: Commit**

```bash
git add README.md docker-compose.yml docs/
git commit -m "refactor: rename project from Gemini-Gateway to AI-Gateway

- Update all documentation references
- Update docker-compose service name
- Emphasize multi-provider support in README"
```

---

## Task 2: 实现 Cookie 管理接口

**Files:**
- Modify: `app/routes/admin.py`
- Modify: `app/providers/gemini.py` (如果需要 reload 方法)

**Step 1: 添加 Pydantic 模型**

```python
# app/routes/admin.py
from pydantic import BaseModel
from datetime import datetime

class CookieUpdate(BaseModel):
    __Secure_1PSID: str
    __Secure_1PSIDTS: str | None = None

class CookieStatus(BaseModel):
    has_psid: bool
    has_psidts: bool
    updated_at: str | None
    auto_refresh: bool
```

**Step 2: 实现 Cookie 更新接口**

```python
@router.post("/admin/cookies")
async def update_cookies(cookies: CookieUpdate):
    """更新 Gemini Cookie，立即生效"""
    global _gemini_provider
    
    if _gemini_provider is None:
        raise HTTPException(status_code=503, detail="Gemini provider not configured")
    
    # 保存到 cookie 文件
    cookie_data = {
        "__Secure-1PSID": cookies.__Secure_1PSID,
        "__Secure-1PSIDTS": cookies.__Secure_1PSIDTS or "",
        "updated_at": datetime.now().isoformat()
    }
    
    Path(_gemini_provider.cookie_path).write_text(
        json.dumps(cookie_data, indent=2), 
        encoding="utf-8"
    )
    
    # 重新初始化 provider
    _gemini_provider._initialized = False
    _gemini_provider._client = None
    await _gemini_provider._ensure_client()
    
    return {
        "status": "success",
        "message": "Cookies updated and provider reloaded",
        "timestamp": cookie_data["updated_at"]
    }
```

**Step 3: 实现 Cookie 状态查询**

```python
@router.get("/admin/cookies/status")
async def cookie_status():
    """查看 Cookie 状态（脱敏）"""
    global _gemini_provider
    
    if _gemini_provider is None:
        return CookieStatus(
            has_psid=False,
            has_psidts=False,
            updated_at=None,
            auto_refresh=False
        )
    
    try:
        cookie_path = _gemini_provider.cookie_path
        if not Path(cookie_path).exists():
            return CookieStatus(
                has_psid=False,
                has_psidts=False,
                updated_at=None,
                auto_refresh=getattr(_gemini_provider, 'auto_refresh', True)
            )
        
        data = json.loads(Path(cookie_path).read_text(encoding="utf-8"))
        return CookieStatus(
            has_psid=bool(data.get("__Secure-1PSID")),
            has_psidts=bool(data.get("__Secure-1PSIDTS")),
            updated_at=data.get("updated_at"),
            auto_refresh=getattr(_gemini_provider, 'auto_refresh', True)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read cookie status: {e}")
```

**Step 4: 运行测试**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python -c "from app.routes.admin import router; print('Import OK')"
```

**Step 5: Commit**

```bash
git add app/routes/admin.py
git commit -m "feat(admin): add cookie management endpoints

- POST /admin/cookies - update cookies and reload provider
- GET /admin/cookies/status - check cookie status (sanitized)"
```

---

## Task 3: 实现日志级别切换

**Files:**
- Modify: `app/services/logger.py`
- Modify: `app/routes/admin.py`

**Step 1: 完善 Logger 服务**

```python
# app/services/logger.py
import sys
from loguru import logger
from typing import Literal

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
        self.current_level = level.upper()
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
```

**Step 2: 添加日志切换接口**

```python
# app/routes/admin.py
from pydantic import BaseModel
from app.services.logger import LogLevel, log_manager

class LogLevelUpdate(BaseModel):
    level: LogLevel

@router.post("/admin/logging")
async def set_log_level(payload: LogLevelUpdate):
    """切换日志级别 (DEBUG/INFO/WARNING/ERROR)"""
    previous = log_manager.set_level(payload.level)
    return {
        "status": "success",
        "level": payload.level,
        "previous_level": previous
    }
```

**Step 3: 运行测试**

```bash
python -c "from app.services.logger import log_manager; log_manager.set_level('DEBUG'); print('Current:', log_manager.get_level())"
```

**Step 4: Commit**

```bash
git add app/services/logger.py app/routes/admin.py
git commit -m "feat(admin): add log level management

- Implement LogManager with dynamic level switching
- POST /admin/logging to change log level
- Support DEBUG/INFO/WARNING/ERROR levels"
```

---

## Task 4: 完善健康检查接口

**Files:**
- Modify: `app/routes/admin.py`
- Modify: `app/main.py` (传递 provider 实例)

**Step 1: 更新 configure 函数接收 providers**

```python
# app/routes/admin.py
from app.providers.gemini import GeminiProvider
from app.providers.g4f import G4FProvider

_gemini: GeminiProvider | None = None
_g4f: G4FProvider | None = None

def configure(manager: ConfigManager | None, gemini: GeminiProvider | None = None, g4f: G4FProvider | None = None) -> None:
    global _config_manager, _gemini, _g4f
    _config_manager = manager
    _gemini = gemini
    _g4f = g4f
```

**Step 2: 实现详细健康检查**

```python
@router.get("/health")
async def health():
    """健康检查，包含各 provider 状态"""
    providers = {}
    
    # Gemini 状态
    if _gemini is None:
        providers["gemini"] = "not_configured"
    else:
        try:
            # 简单检查：尝试加载 cookie
            _gemini.load_cookie_values(_gemini.cookie_path)
            providers["gemini"] = "ok"
        except Exception as e:
            providers["gemini"] = f"error: {type(e).__name__}"
    
    # g4f 状态
    if _g4f is None:
        providers["g4f"] = "not_configured"
    else:
        providers["g4f"] = "ok"
    
    overall = "healthy" if all(p == "ok" for p in providers.values() if p != "not_configured") else "degraded"
    
    return {
        "status": overall,
        "version": "1.0.0",
        "providers": providers
    }
```

**Step 3: 更新 main.py 传递 providers**

```python
# app/main.py
configure_admin(config_manager, gemini_provider, g4f_provider)
```

**Step 4: 测试健康检查**

```bash
python -c "from app.routes.admin import health; import asyncio; print(asyncio.run(health()))"
```

**Step 5: Commit**

```bash
git add app/routes/admin.py app/main.py
git commit -m "feat(admin): enhance health check endpoint

- Return detailed provider status (gemini/g4f)
- Check cookie validity for Gemini
- Overall status: healthy/degraded"
```

---

## Task 5: 更新 ConfigManager 支持完整配置

**Files:**
- Modify: `app/config/manager.py`
- Modify: `app/config/settings.py`

**Step 1: 扩展 ConfigManager 加载完整配置**

```python
# app/config/manager.py
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
```

**Step 2: Commit**

```bash
git add app/config/manager.py
git commit -m "feat(config): extend ConfigManager to load full configuration

- Support loading all settings sections from YAML
- Server, Auth, Gemini, G4F settings"
```

---

## 验证清单

完成所有任务后验证：

```bash
# 1. 检查重命名
grep -r "Gemini-Gateway" . --include="*.md" --include="*.py" --include="*.yml" 2>/dev/null || echo "Rename OK"

# 2. 检查 imports
python -c "
from app.routes.admin import router
from app.services.logger import log_manager
from app.config.manager import ConfigManager
print('All imports OK')
"

# 3. 检查 admin 路由
curl http://localhost:8022/health 2>/dev/null || echo "Server not running, but code OK"
```

---

## 提交历史

1. `refactor: rename project from Gemini-Gateway to AI-Gateway`
2. `feat(admin): add cookie management endpoints`
3. `feat(admin): add log level management`
4. `feat(admin): enhance health check endpoint`
5. `feat(config): extend ConfigManager to load full configuration`
