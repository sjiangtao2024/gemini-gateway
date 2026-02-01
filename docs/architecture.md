# Gemini-Gateway 架构设计文档

## 1. 项目概述

### 1.1 项目目标
构建一个支持 OpenAI 和 Claude 双协议的 AI 模型网关，统一接入 Gemini 和 ChatGPT 模型，支持流式响应和配置热重载。

### 1.2 核心特性
- **双协议支持**: OpenAI (`/v1/chat/completions`) + Claude (`/v1/messages`)
- **多模型接入**: Gemini (主力) + ChatGPT (备选，通过 gpt4free)
- **模型透传**: 直接暴露 `gemini-2.5-pro`、`gpt-4o` 等真实模型名
- **流式响应**: SSE (Server-Sent Events) 支持
- **配置热重载**: 不重启服务即可更新配置
- **动态日志**: 运行时切换日志级别
- **Bearer 认证**: 标准 Token 认证

### 1.3 技术栈
| 组件 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | ^0.115 |
| Gemini 库 | gemini-webapi | ^1.17.3 |
| ChatGPT 库 | g4f | latest |
| 配置管理 | Pydantic Settings | ^2.0 |
| 文件监听 | watchdog | ^3.0 |
| 日志 | loguru | ^0.7 |
| 数据验证 | Pydantic | ^2.0 |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │   Codex CLI      │  │  Claude Code CLI │                    │
│  │  (OpenAI 协议)   │  │  (Claude 协议)   │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
└───────────┼─────────────────────┼───────────────────────────────┘
            │                     │
            ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API 网关层 (FastAPI)                       │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │    OpenAI 路由组         │  │      Claude 路由组           │  │
│  │  /v1/chat/completions   │  │  /v1/messages               │  │
│  │  /v1/models             │  │  /v1/claude/models          │  │
│  └──────────┬──────────────┘  └─────────────┬─────────────────┘  │
│             │                               │                    │
│             └───────────────┬───────────────┘                    │
│                             ▼                                   │
│              ┌─────────────────────────────┐                    │
│              │      协议转换/适配层         │                    │
│              │  - OpenAI → 统一内部格式    │                    │
│              │  - Claude → 统一内部格式    │                    │
│              └──────────────┬──────────────┘                    │
│                             ▼                                   │
│              ┌─────────────────────────────┐                    │
│              │       模型路由引擎          │                    │
│              │  - 模型名解析               │                    │
│              │  - Provider 选择            │                    │
│              │  - 流式/非流式分发          │                    │
│              └──────────────┬──────────────┘                    │
└─────────────────────────────┼───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Gemini     │    │   ChatGPT    │    │   Claude     │
│  Provider    │    │  Provider    │    │  Provider    │
│              │    │  (gpt4free)  │    │  (gpt4free)  │
│ gemini-webapi│    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 关键类/函数 |
|------|------|-------------|
| `routes/openai.py` | OpenAI 协议端点 | `chat_completions()`, `list_models()` |
| `routes/claude.py` | Claude 协议端点 | `messages()`, `list_models()` |
| `routes/admin.py` | 管理接口 | `update_cookies()`, `reload_config()` |
| `providers/base.py` | Provider 抽象基类 | `BaseProvider` |
| `providers/gemini.py` | Gemini 实现 | `GeminiProvider` |
| `providers/g4f.py` | GPT4Free 实现 | `G4FProvider` |
| `services/router.py` | 模型路由 | `ModelRouter` |
| `services/stream.py` | 流式处理 | `StreamHandler` |
| `services/cookie.py` | Cookie 管理 | `CookieManager` |
| `config/manager.py` | 配置管理+热重载 | `ConfigManager` |
| `auth/middleware.py` | 认证中间件 | `auth_middleware()` |

---

## 3. 配置系统设计

### 3.1 配置文件结构

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8022
  
auth:
  bearer_token: "your-secure-token-here"  # Bearer Token 认证
  
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
  file: "/app/logs/gateway.log"
  rotation: "10 MB"
  
gemini:
  enabled: true
  cookie_path: "/app/cookies/gemini.json"
  auto_refresh: true  # 自动刷新 __Secure-1PSIDTS
  models:
    - "gemini-2.5-pro"
    - "gemini-2.5-flash"
    - "gemini-3.0-pro"
    - "gemini-2.0-flash"
  
g4f:
  enabled: true
  models:
    - "gpt-4o"
    - "gpt-4o-mini"
    - "claude-3-opus"
    - "claude-3-sonnet"
    # 以下为示例占位，需按 g4f provider 当前支持的 model id 填写
    - "deepseek-*"
    - "qwen-*"
    - "grok-*"
  fallback:
    enabled: true
    max_retries: 2
    timeout: 30
  # 说明：g4f 的模型可用性依赖 provider 状态，部分模型可能需要 API Key 或 Cookies
  # 建议：通过 g4f /v1/providers 查询可用 provider 与模型列表后再配置
```

### 3.2 热重载实现

**原理**: 使用 `watchdog` 监听配置文件变化，触发配置重新加载。

```python
# config/manager.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloader(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == CONFIG_PATH:
            logger.info("Config file changed, reloading...")
            config_manager.reload()
            # 重新初始化相关组件
            provider_manager.reload()
            
# 启动监听
observer = Observer()
observer.schedule(ConfigReloader(), path=config_dir, recursive=False)
observer.start()
```

**热重载范围**:
- ✅ 可以热重载: `logging.level`, `auth.bearer_token`, `gemini.cookie_path`
- ❌ 需要重启: `server.host`, `server.port`（监听地址变更）

### 3.3 配置验证

使用 Pydantic 进行类型验证:

```python
from pydantic import BaseSettings, Field

class GatewayConfig(BaseSettings):
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8022, env="SERVER_PORT")
    bearer_token: str = Field(..., env="BEARER_TOKEN")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    gemini_cookie_path: str = Field(default="/app/cookies/gemini.json")
```

---

## 4. 认证设计

### 4.1 Bearer Token 认证

**请求头格式**:
```
Authorization: Bearer <token>
```

**FastAPI 实现**:
```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if token != config.bearer_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

# 在路由中使用
@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    token: str = Depends(verify_token)
):
    ...
```

### 4.2 与客户端兼容性

**OpenAI 客户端**:
```python
from openai import OpenAI
client = OpenAI(
    base_url="http://gateway:8022/v1",
    api_key="your-secure-token-here"  # 这会被作为 Bearer Token
)
```

**Claude Code CLI**:
```bash
export ANTHROPIC_BASE_URL=http://gateway:8022
export ANTHROPIC_API_KEY=your-secure-token-here
claude
```

---

## 5. 日志系统设计

### 5.1 日志级别动态切换

**实现方案**: 使用 Loguru 的 `level()` 方法动态调整

```python
# services/logger.py
from loguru import logger
import sys

class LogManager:
    def __init__(self):
        self.current_level = "INFO"
        
    def set_level(self, level: str):
        """动态切换日志级别"""
        level = level.upper()
        logger.remove()
        logger.add(
            sys.stdout,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
        )
        self.current_level = level
        logger.info(f"Log level changed to {level}")

# 通过 API 切换
@app.post("/admin/logging")
async def set_log_level(level: str):
    log_manager.set_level(level)
    return {"status": "success", "level": level}
```

### 5.2 日志格式

**开发模式 (DEBUG)**:
```
2026-01-31 14:30:25 | DEBUG    | Request: POST /v1/chat/completions | model=gemini-2.5-pro
2026-01-31 14:30:25 | DEBUG    | Routing to Gemini provider
2026-01-31 14:30:26 | INFO     | Response: 200 OK | tokens=150 | time=1.2s
```

**生产模式 (INFO)**:
```
2026-01-31 14:30:25 | INFO | POST /v1/chat/completions | gemini-2.5-pro | 200 | 1.2s
```

---

## 6. Provider 设计

### 6.1 Provider 基类

```python
# providers/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Union

class BaseProvider(ABC):
    @abstractmethod
    async def chat_completions(
        self,
        messages: list[dict],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Union[dict, AsyncIterator[dict]]:
        """非流式或流式聊天完成"""
        pass
    
    @abstractmethod
    async def list_models(self) -> list[dict]:
        """列出支持的模型"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass
```

### 6.2 模型路由表

```python
# 不映射，直接透传
PROVIDER_ROUTES = {
    # Gemini 模型
    "gemini-2.5-pro": "gemini",
    "gemini-2.5-flash": "gemini",
    "gemini-3.0-pro": "gemini",
    "gemini-2.0-flash": "gemini",
    
    # G4F 模型
    "gpt-4o": "g4f",
    "gpt-4o-mini": "g4f",
    "gpt-4": "g4f",
    "claude-3-opus": "g4f",
    "claude-3-sonnet": "g4f",
    "claude-3-haiku": "g4f",
}

def get_provider(model: str) -> BaseProvider:
    provider_name = PROVIDER_ROUTES.get(model)
    if not provider_name:
        raise ValueError(f"Unsupported model: {model}")
    return provider_manager.get(provider_name)
```

### 6.3 Gemini Provider

```python
# providers/gemini.py
from gemini_webapi import GeminiClient

class GeminiProvider(BaseProvider):
    def __init__(self, cookie_path: str):
        self.cookie_path = cookie_path
        self.client = None
        
    async def initialize(self):
        cookies = load_cookies(self.cookie_path)
        self.client = GeminiClient(
            cookies["__Secure-1PSID"],
            cookies["__Secure-1PSIDTS"]
        )
        await self.client.init()
    
    async def chat_completions(self, messages, model, stream=False, **kwargs):
        # 转换消息格式
        prompt = self._convert_messages(messages)
        
        if stream:
            return self._stream_response(prompt, model)
        else:
            response = await self.client.generate_content(prompt, model=model)
            return self._format_response(response)
    
    async def _stream_response(self, prompt, model):
        response = await self.client.generate_content(prompt, model=model)
        # Gemini 不原生支持流式，模拟 SSE
        chunks = self._simulate_streaming(response.text)
        for chunk in chunks:
            yield self._format_stream_chunk(chunk)
```

---

## 7. 流式响应设计

### 7.1 SSE (Server-Sent Events) 格式

**OpenAI 格式**:
```
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", ...}

data: {"choices": [{"delta": {"content": "Hello"}}]}

data: [DONE]
```

**Claude 格式**:
```
event: message_start
data: {"type": "message_start", "message": {...}}

event: content_block_delta
data: {"type": "content_block_delta", "delta": {"text": "Hello"}}

event: message_stop
data: {"type": "message_stop"}
```

### 7.2 FastAPI SSE 实现

```python
from fastapi.responses import StreamingResponse

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    provider = get_provider(request.model)
    
    if request.stream:
        async def event_generator():
            async for chunk in provider.chat_completions(
                messages=request.messages,
                model=request.model,
                stream=True
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    else:
        response = await provider.chat_completions(...)
        return response
```

---

## 8. Cookie 管理设计

### 8.1 Cookie 存储格式

```json
{
  "__Secure-1PSID": "g.a000...",
  "__Secure-1PSIDTS": "sidts-CjEB...",
  "updated_at": "2026-01-31T14:30:00"
}
```

### 8.2 Cookie 管理接口

```python
# routes/admin.py

@app.post("/admin/cookies")
async def update_cookies(cookies: CookieUpdate):
    """
    手动更新 Gemini Cookie
    无需重启服务，立即生效
    """
    cookie_manager.save(cookies.dict())
    
    # 重新初始化 Gemini Provider
    await provider_manager.reload_gemini()
    
    return {
        "status": "success",
        "message": "Cookies updated and provider reloaded"
    }

@app.get("/admin/cookies/status")
async def cookie_status():
    """查看 Cookie 状态（脱敏）"""
    cookies = cookie_manager.load()
    return {
        "has_psid": bool(cookies.get("__Secure-1PSID")),
        "has_psidts": bool(cookies.get("__Secure-1PSIDTS")),
        "updated_at": cookies.get("updated_at"),
        "auto_refresh": config.gemini.auto_refresh
    }
```

### 8.3 自动刷新机制

```python
# gemini-webapi 内置自动刷新 __Secure-1PSIDTS
# 每 9 分钟自动刷新一次
# 无需额外实现
```

---

## 9. 部署设计

### 9.1 Docker 配置

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app/ ./app/
COPY config/ ./config/

# 创建目录
RUN mkdir -p /app/logs /app/cookies

# 非 root 用户运行
RUN useradd -m -u 1000 gateway && \
    chown -R gateway:gateway /app
USER gateway

EXPOSE 8022

CMD ["python", "-m", "app.main"]
```

### 9.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  gemini-gateway:
    build: .
    container_name: gemini-gateway
    ports:
      - "8022:8022"
    volumes:
      # 配置文件（热重载）
      - ./config/config.yaml:/app/config/config.yaml:ro
      # Cookie 文件
      - ./cookies:/app/cookies
      # 日志目录
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8022/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 9.3 树莓派 5 优化

```yaml
# docker-compose.rpi.yml
version: '3.8'

services:
  gemini-gateway:
    build: .
    # 资源限制
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
    # 使用轻量级基础镜像
    # 已在 Dockerfile 中使用 python:3.11-slim
```

---

## 10. API 端点汇总

### 10.1 OpenAI 兼容端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/models` | GET | 列出可用模型 |
| `/v1/chat/completions` | POST | 聊天完成（流式/非流式） |

### 10.2 Claude 兼容端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/claude/models` | GET | 列出可用模型（Claude 格式） |
| `/v1/messages` | POST | 消息完成（流式/非流式） |

### 10.3 管理端点

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 否 |
| `/admin/config/reload` | POST | 触发配置重载 | Bearer |
| `/admin/cookies` | POST | 更新 Cookie | Bearer |
| `/admin/cookies/status` | GET | Cookie 状态 | Bearer |
| `/admin/logging` | POST | 切换日志级别 | Bearer |

---

## 11. 开发计划

### Phase 1: 基础框架 (3 天)
- [ ] 项目结构搭建
- [ ] 配置系统（含热重载）
- [ ] 日志系统（动态级别）
- [ ] Bearer 认证中间件

### Phase 2: Gemini Provider (2 天)
- [ ] GeminiProvider 实现
- [ ] Cookie 管理
- [ ] 流式响应模拟

### Phase 3: OpenAI 协议 (2 天)
- [ ] `/v1/models` 端点
- [ ] `/v1/chat/completions` 端点
- [ ] 流式/非流式支持
- [ ] Codex CLI 兼容性测试

### Phase 4: Claude 协议 (2 天)
- [ ] `/v1/claude/models` 端点
- [ ] `/v1/messages` 端点
- [ ] 流式/非流式支持
- [ ] Claude Code CLI 兼容性测试

### Phase 5: G4F Provider (2 天)
- [ ] G4FProvider 实现
- [ ] 模型路由优化
- [ ] Fallback 机制

### Phase 6: 部署与文档 (2 天)
- [ ] Dockerfile
- [ ] Docker Compose
- [ ] 使用文档
- [ ] 测试用例

**总计: 约 2 周**

---

## 12. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| gemini-webapi 更新 | 中 | 锁定版本，定期升级测试 |
| gpt4free 不稳定 | 中 | 实现 fallback，监控可用性 |
| Cookie 过期 | 高 | 自动刷新 + 手动更新接口 |
| 流式响应延迟 | 中 | 优化 SSE 实现，使用缓冲 |
| 树莓派性能 | 低 | 资源限制，单账号设计 |

---

## 13. 附录

### 13.1 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CONFIG_PATH` | 配置文件路径 | `/app/config/config.yaml` |
| `COOKIE_PATH` | Cookie 文件路径 | `/app/cookies/gemini.json` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `BEARER_TOKEN` | 认证 Token | 必填 |

### 13.2 相关链接

- gemini-webapi: https://github.com/HanaokaYuzu/Gemini-API
- gpt4free: https://github.com/xtekky/gpt4free
- FastAPI: https://fastapi.tiangolo.com/
- OpenAI API: https://platform.openai.com/docs/api-reference
- Claude API: https://docs.anthropic.com/claude/reference

---

*文档版本: 1.0*
*生成日期: 2026-01-31*
*作者: Claude Code*
