# Phase 4: 稳定性与错误处理实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 提升服务稳定性，完善错误处理，添加请求日志和 Fallback 机制

**Architecture:** 
- 错误分类：区分网络错误、认证错误、限流错误
- Fallback：Gemini 失败时尝试 g4f
- 请求日志：记录请求路径、模型、耗时
- 超时控制：可配置超时时间

**Tech Stack:** FastAPI, Loguru, Time

---

## 背景信息

### 当前错误处理状态

当前代码中的错误处理比较简单，大多数是：
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Something failed: {e}")
```

### 目标错误分类

| 错误类型 | HTTP 状态码 | error.code | 场景 |
|---------|------------|-----------|------|
| 认证错误 | 401 | `authentication_error` | Cookie 过期、无效 |
| 限流错误 | 429 | `rate_limit_exceeded` | 请求过于频繁 |
| 模型不存在 | 404 | `model_not_found` | 模型名称错误 |
| Provider 错误 | 503 | `provider_error` | Gemini/g4f 服务不可用 |
| 请求错误 | 422 | `invalid_request_error` | 参数错误 |
| 内部错误 | 500 | `internal_error` | 未知错误 |

---

## Task 1: 创建错误处理模块

**Files:**
- Create: `app/utils/errors.py`

**Step 1: Create error classes**

```python
"""错误处理和分类模块"""
from typing import Any
from fastapi import HTTPException


class AI GatewayError(Exception):
    """基础错误类"""
    def __init__(self, message: str, code: str, status_code: int = 500, details: dict | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "type": self.code.replace("_", " "),
                "code": self.code,
                **self.details
            }
        }


class AuthenticationError(AI GatewayError):
    """认证错误 (Cookie 过期、无效 Token)"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "authentication_error", 401)


class RateLimitError(AI GatewayError):
    """限流错误"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "rate_limit_exceeded", 429)


class ModelNotFoundError(AI GatewayError):
    """模型不存在"""
    def __init__(self, model: str):
        super().__init__(
            f"Model '{model}' not found",
            "model_not_found",
            404,
            {"model": model}
        )


class ProviderError(AI GatewayError):
    """Provider 服务错误"""
    def __init__(self, provider: str, message: str):
        super().__init__(
            f"{provider} error: {message}",
            "provider_error",
            503,
            {"provider": provider}
        )


class InvalidRequestError(AI GatewayError):
    """请求参数错误"""
    def __init__(self, message: str):
        super().__init__(message, "invalid_request_error", 422)


def http_exception_from_error(error: AI GatewayError) -> HTTPException:
    """将自定义错误转换为 FastAPI HTTPException"""
    return HTTPException(
        status_code=error.status_code,
        detail=error.to_dict()
    )


def classify_exception(exc: Exception, provider: str = "unknown") -> AI GatewayError:
    """分类异常为具体的错误类型"""
    error_msg = str(exc).lower()
    
    # 认证相关
    if any(k in error_msg for k in ["cookie", "auth", "unauthorized", "401"]):
        return AuthenticationError(str(exc))
    
    # 限流相关
    if any(k in error_msg for k in ["rate limit", "too many", "429"]):
        return RateLimitError(str(exc))
    
    # 超时/连接错误
    if any(k in error_msg for k in ["timeout", "connection", "refused"]):
        return ProviderError(provider, str(exc))
    
    # 默认 Provider 错误
    return ProviderError(provider, str(exc))
```

**Step 2: Test imports**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -c "from app.utils.errors import AI GatewayError, AuthenticationError; print('Import OK')"
```

**Step 3: Commit**

```bash
git add app/utils/errors.py
git commit -m "feat(errors): add error classification module

- AI GatewayError base class with structured error info
- Specific error types: AuthenticationError, RateLimitError, etc.
- classify_exception function for automatic error classification"
```

---

## Task 2: 更新 Provider 错误处理

**Files:**
- Modify: `app/providers/gemini.py`

**Step 1: Update gemini.py with better error handling**

```python
# Add import at top
from app.utils.errors import classify_exception, AuthenticationError, ProviderError

# Update _ensure_client to handle auth errors better
async def _ensure_client(self) -> GeminiClient:
    if self._client is None:
        try:
            psid, psidts = self.load_cookie_values(self.cookie_path)
        except ValueError as e:
            raise AuthenticationError(f"Invalid cookie: {e}")
        except FileNotFoundError:
            raise AuthenticationError("Cookie file not found")
        
        self._client = GeminiClient(psid, psidts, proxy=self.proxy)
    
    if not self._initialized:
        try:
            await self._client.init(
                timeout=self.timeout,
                auto_close=self.auto_close,
                close_delay=self.close_delay,
                auto_refresh=self.auto_refresh,
            )
            self._initialized = True
        except Exception as e:
            raise classify_exception(e, "gemini")
    
    return self._client

# Update chat_completions with error handling
async def chat_completions(self, messages: list[dict], model: str | None = None, **kwargs) -> dict:
    try:
        client = await self._ensure_client()
        prompt = self._messages_to_prompt(messages)
        selected_model = model or self.model
        
        if selected_model:
            response = await client.generate_content(prompt, model=selected_model)
        else:
            response = await client.generate_content(prompt)
        
        return {"text": response.text, "images": response.images, "raw": response}
    except AI GatewayError:
        raise
    except Exception as e:
        raise classify_exception(e, "gemini")

# Update generate_images with error handling
async def generate_images(self, prompt: str, model: str | None = None) -> list[Any]:
    try:
        client = await self._ensure_client()
        selected_model = model or self.model
        
        if selected_model:
            response = await client.generate_content(prompt, model=selected_model)
        else:
            response = await client.generate_content(prompt)
        
        return list(response.images)
    except AI GatewayError:
        raise
    except Exception as e:
        raise classify_exception(e, "gemini")

# Update chat_completions_with_files with error handling
async def chat_completions_with_files(
    self,
    messages: list[dict],
    text: str,
    files: list[str],
    model: str | None = None
) -> dict:
    try:
        client = await self._ensure_client()
        
        # 构建提示词（包含历史消息上下文）
        context = self._messages_to_prompt(messages)
        if context:
            prompt = f"{context}\n\n{text}"
        else:
            prompt = text
        
        selected_model = model or self.model
        if selected_model:
            response = await client.generate_content(prompt, files=files, model=selected_model)
        else:
            response = await client.generate_content(prompt, files=files)
        
        return {"text": response.text, "images": response.images, "raw": response}
    except AI GatewayError:
        raise
    except Exception as e:
        raise classify_exception(e, "gemini")
```

**Step 2: Test imports**

```bash
python3 -c "from app.providers.gemini import GeminiProvider; print('Import OK')"
```

**Step 3: Commit**

```bash
git add app/providers/gemini.py
git commit -m "feat(gemini): enhance error handling

- Use classify_exception for automatic error classification
- Better authentication error handling
- Wrap all methods with error handling"
```

---

## Task 3: 更新路由错误处理

**Files:**
- Modify: `app/routes/openai.py`
- Modify: `app/routes/claude.py`

**Step 1: Update openai.py**

```python
# Add import
from app.utils.errors import AI GatewayError, http_exception_from_error, ModelNotFoundError

# Update _is_gemini_model to also check if model is in supported list
def _get_model_provider(model: str) -> str:
    """获取模型所属 provider"""
    if model.startswith("gemini-"):
        return "gemini"
    # g4f 模型列表可能动态变化，这里简化处理
    return "g4f"

# Add error handler wrapper
async def _handle_chat_request(model: str, messages: list, **kwargs):
    """统一处理聊天请求，支持 fallback"""
    provider = _get_model_provider(model)
    
    if provider == "gemini":
        if _gemini is None:
            raise ProviderError("gemini", "Provider not configured")
        
        try:
            return await _gemini.chat_completions(messages=messages, model=model)
        except AI GatewayError as e:
            # 如果 Gemini 失败，尝试 fallback 到 g4f
            if _g4f is not None and kwargs.get("fallback", False):
                logger.warning(f"Gemini failed: {e.message}, trying g4f fallback")
                # 转换模型名或直接使用 g4f 的等效模型
                return await _g4f.chat_completions({
                    "model": "gpt-4o",  # fallback 模型
                    "messages": messages
                })
            raise
    else:
        if _g4f is None:
            raise ProviderError("g4f", "Provider not configured")
        return await _g4f.chat_completions({
            "model": model,
            "messages": messages
        })
```

**Step 2: Update chat_completions to use error handler**

```python
@router.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest):
    model = payload.model
    
    try:
        # ... existing vision logic ...
        
    except AI GatewayError as e:
        raise http_exception_from_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in chat_completions")
        raise HTTPException(status_code=500, detail={
            "error": {
                "message": str(e),
                "type": "internal_error",
                "code": "internal_error"
            }
        })
```

**Step 3: Update claude.py similarly**

```python
# Add import
from app.utils.errors import AI GatewayError, http_exception_from_error

# Wrap messages endpoint with error handling
@router.post("/v1/messages")
async def messages(payload: ClaudeRequest):
    try:
        # ... existing logic ...
    except AI GatewayError as e:
        raise http_exception_from_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in messages")
        raise HTTPException(status_code=500, detail={
            "error": {
                "message": str(e),
                "type": "internal_error",
                "code": "internal_error"
            }
        })
```

**Step 4: Test imports**

```bash
python3 -c "from app.routes.openai import router; print('OpenAI import OK')"
python3 -c "from app.routes.claude import router; print('Claude import OK')"
```

**Step 5: Commit**

```bash
git add app/routes/openai.py app/routes/claude.py
git commit -m "feat(routes): add structured error handling

- Use AI GatewayError for consistent error responses
- Add fallback support for Gemini failures
- Standard error format across all endpoints"
```

---

## Task 4: 添加请求日志中间件

**Files:**
- Create: `app/middlewares/logging.py`
- Modify: `app/main.py`

**Step 1: Create logging middleware**

```python
"""请求日志中间件"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.logger import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录请求信息的中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求开始
        client_host = request.client.host if request.client else "unknown"
        logger.debug(f"Request started: {request.method} {request.url.path} from {client_host}")
        
        try:
            response = await call_next(request)
            
            # 计算耗时
            process_time = time.time() - start_time
            
            # 记录请求完成
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
            )
            
            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} - ERROR - {process_time:.3f}s - {str(e)}"
            )
            raise
```

**Step 2: Register middleware in main.py**

```python
# Add import
from app.middlewares.logging import RequestLoggingMiddleware

# Add after app creation
app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
app.middleware("http")(auth_middleware)
```

**Step 3: Test imports**

```bash
python3 -c "from app.middlewares.logging import RequestLoggingMiddleware; print('Import OK')"
python3 -c "from app.main import app; print('Main import OK')"
```

**Step 4: Commit**

```bash
git add app/middlewares/logging.py app/main.py
git commit -m "feat(middleware): add request logging middleware

- Log all requests with method, path, status code, and duration
- Add X-Process-Time header to responses
- Separate debug and info level logging"
```

---

## Task 5: 添加超时配置

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/providers/gemini.py`

**Step 1: Add timeout to settings**

```python
# app/config/settings.py

class GeminiSettings(BaseModel):
    enabled: bool = True
    cookie_path: str = ""
    auto_refresh: bool = True
    models: List[str] = Field(default_factory=list)
    proxy: str | None = None
    timeout: int = 30  # 新增：超时时间（秒）

class G4FSettings(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:1337"
    providers: List[str] = Field(default_factory=list)
    model_prefixes: List[str] = Field(default_factory=list)
    timeout: float = 30.0  # 新增：超时时间（秒）
```

**Step 2: Update from_env to read timeout**

```python
@classmethod
def from_env(cls) -> "Settings":
    # ... existing code ...
    return cls(
        server=ServerSettings(host=host, port=port),
        auth=AuthSettings(bearer_token=bearer_token),
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

**Step 3: Update gemini.py to use settings timeout**

```python
# In __init__, use settings timeout
def __init__(
    self,
    cookie_path: str,
    model: str | None = None,
    proxy: str | None = None,
    timeout: int = 30,  # Use this instead of hardcoded
    auto_close: bool = False,
    close_delay: int = 300,
    auto_refresh: bool = True,
) -> None:
    # ... existing code ...
    self.timeout = timeout
```

**Step 4: Update main.py to pass timeout**

```python
if settings.gemini.enabled and settings.gemini.cookie_path:
    gemini_provider = GeminiProvider(
        cookie_path=settings.gemini.cookie_path,
        model=settings.gemini.models[0] if settings.gemini.models else None,
        proxy=settings.gemini.proxy,
        auto_refresh=settings.gemini.auto_refresh,
        timeout=settings.gemini.timeout,  # Add this
    )
```

**Step 5: Commit**

```bash
git add app/config/settings.py app/providers/gemini.py app/main.py
git commit -m "feat(config): add configurable timeout settings

- Add timeout to GeminiSettings and G4FSettings
- Read from environment variables
- Pass timeout to provider initialization"
```

---

## Task 6: 添加错误处理测试

**Files:**
- Create: `tests/test_errors.py`

**Step 1: Create test file**

```python
"""错误处理测试"""
import pytest
from app.utils.errors import (
    AI GatewayError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ProviderError,
    InvalidRequestError,
    classify_exception,
    http_exception_from_error
)

class TestErrors:
    """测试错误类"""
    
    def test_base_error(self):
        """测试基础错误类"""
        err = AI GatewayError("test message", "test_code", 400, {"detail": "info"})
        
        assert err.message == "test message"
        assert err.code == "test_code"
        assert err.status_code == 400
        assert err.details == {"detail": "info"}
    
    def test_error_to_dict(self):
        """测试错误转字典"""
        err = AuthenticationError("Invalid token")
        result = err.to_dict()
        
        assert result["error"]["message"] == "Invalid token"
        assert result["error"]["code"] == "authentication_error"
        assert result["error"]["type"] == "authentication error"
    
    def test_authentication_error_defaults(self):
        """测试认证错误默认值"""
        err = AuthenticationError()
        
        assert err.status_code == 401
        assert err.code == "authentication_error"
    
    def test_rate_limit_error(self):
        """测试限流错误"""
        err = RateLimitError()
        
        assert err.status_code == 429
        assert err.code == "rate_limit_exceeded"
    
    def test_model_not_found_error(self):
        """测试模型不存在错误"""
        err = ModelNotFoundError("gemini-99")
        
        assert err.status_code == 404
        assert "gemini-99" in err.message
        assert err.details["model"] == "gemini-99"
    
    def test_provider_error(self):
        """测试 Provider 错误"""
        err = ProviderError("gemini", "Connection timeout")
        
        assert err.status_code == 503
        assert "gemini" in err.message
        assert err.details["provider"] == "gemini"
    
    def test_invalid_request_error(self):
        """测试请求错误"""
        err = InvalidRequestError("Missing required field")
        
        assert err.status_code == 422
        assert err.code == "invalid_request_error"


class TestExceptionClassification:
    """测试异常分类"""
    
    def test_classify_auth_error(self):
        """测试分类认证错误"""
        exc = Exception("Cookie expired")
        err = classify_exception(exc)
        
        assert isinstance(err, AuthenticationError)
    
    def test_classify_rate_limit(self):
        """测试分类限流错误"""
        exc = Exception("Rate limit exceeded")
        err = classify_exception(exc)
        
        assert isinstance(err, RateLimitError)
    
    def test_classify_timeout(self):
        """测试分类超时错误"""
        exc = Exception("Connection timeout")
        err = classify_exception(exc, "gemini")
        
        assert isinstance(err, ProviderError)
        assert err.details["provider"] == "gemini"
    
    def test_classify_generic(self):
        """测试分类通用错误"""
        exc = Exception("Something went wrong")
        err = classify_exception(exc, "test")
        
        assert isinstance(err, ProviderError)


class TestHTTPException:
    """测试 HTTP 异常转换"""
    
    def test_http_exception_from_error(self):
        """测试转换为 FastAPI HTTPException"""
        err = AuthenticationError("Invalid token")
        http_exc = http_exception_from_error(err)
        
        from fastapi import HTTPException
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 401
        assert "error" in http_exc.detail
```

**Step 2: Run tests**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -m pytest tests/test_errors.py -v
```

**Step 3: Commit**

```bash
git add tests/test_errors.py
git commit -m "test(errors): add error handling tests

- Test all error classes
- Test exception classification
- Test HTTP exception conversion"
```

---

## 验证清单

完成所有任务后验证：

```bash
# 1. 检查所有导入
python3 -c "
from app.utils.errors import AI GatewayError
from app.middlewares.logging import RequestLoggingMiddleware
from app.providers.gemini import GeminiProvider
print('✅ All imports OK')
"

# 2. 运行测试
python3 -m pytest tests/test_errors.py -v

# 3. 检查主应用
python3 -c "from app.main import app; print('✅ Main app OK')"
```

---

## 提交历史

1. `feat(errors): add error classification module`
2. `feat(gemini): enhance error handling`
3. `feat(routes): add structured error handling`
4. `feat(middleware): add request logging middleware`
5. `feat(config): add configurable timeout settings`
6. `test(errors): add error handling tests`

---

## 预期结果

完成后：

1. **错误响应格式统一**:
```json
{
  "error": {
    "message": "Cookie expired",
    "type": "authentication_error",
    "code": "authentication_error"
  }
}
```

2. **请求日志**: 每个请求记录方法和耗时

3. **可配置超时**: 通过环境变量 `GEMINI_TIMEOUT` 和 `G4F_TIMEOUT` 配置
