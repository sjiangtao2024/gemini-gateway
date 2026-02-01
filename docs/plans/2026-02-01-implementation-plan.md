# Gemini-Gateway Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI gateway that supports OpenAI + Claude protocols, Gemini + g4f providers, dynamic model aggregation, and OpenAI-compatible `/v1/images`.

**Architecture:** A FastAPI app routes OpenAI and Claude endpoints to provider adapters. Gemini uses `gemini-webapi` with cookie auth; g4f is used for web-based providers with provider/model prefix filtering and dynamic aggregation. Config is YAML + env overrides with hot reload. Streaming uses SSE.

**Tech Stack:** Python 3.11, FastAPI, Pydantic Settings, loguru, watchdog, httpx, gemini-webapi, g4f.

---

### Task 1: Create project skeleton and dependencies

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config/__init__.py`
- Create: `app/config/settings.py`
- Create: `app/config/manager.py`
- Create: `requirements.txt`

**Step 1: Write the failing test**

```python
# tests/test_settings.py
from app.config.settings import Settings

def test_settings_defaults():
    settings = Settings()
    assert settings.server.host == "0.0.0.0"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings.py::test_settings_defaults -v`
Expected: FAIL (ModuleNotFoundError or attribute error)

**Step 3: Write minimal implementation**

```python
# app/config/settings.py
from pydantic import BaseModel

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8022

class Settings(BaseModel):
    server: ServerSettings = ServerSettings()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings.py::test_settings_defaults -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/config/settings.py tests/test_settings.py app/__init__.py app/config/__init__.py app/main.py requirements.txt
git commit -m "feat: add base settings skeleton"
```

---

### Task 2: Implement config loading + env overrides

**Files:**
- Modify: `app/config/settings.py`
- Create: `tests/test_settings_env.py`

**Step 1: Write the failing test**

```python
import os
from app.config.settings import Settings

def test_env_override():
    os.environ["SERVER_HOST"] = "127.0.0.1"
    settings = Settings.from_env()
    assert settings.server.host == "127.0.0.1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_env.py::test_env_override -v`
Expected: FAIL (from_env not implemented)

**Step 3: Write minimal implementation**

```python
# app/config/settings.py
from pydantic import BaseModel

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8022

class Settings(BaseModel):
    server: ServerSettings = ServerSettings()

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.getenv("SERVER_HOST", "0.0.0.0")
        port = int(os.getenv("SERVER_PORT", "8022"))
        return cls(server=ServerSettings(host=host, port=port))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings_env.py::test_env_override -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/config/settings.py tests/test_settings_env.py
git commit -m "feat: add env overrides for settings"
```

---

### Task 3: Add config file loading + hot reload

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/config/manager.py`
- Create: `tests/test_config_reload.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_reload.py::test_config_reload -v`
Expected: FAIL (ConfigManager not implemented)

**Step 3: Write minimal implementation**

```python
# app/config/manager.py
import yaml
from app.config.settings import Settings, ServerSettings

class ConfigManager:
    def __init__(self, path: str):
        self.path = path
        self.settings = Settings()

    def load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        server = data.get("server", {})
        self.settings = Settings(server=ServerSettings(**server))

    def reload(self) -> None:
        self.load()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_reload.py::test_config_reload -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/config/manager.py tests/test_config_reload.py app/config/settings.py
git commit -m "feat: add config load and reload"
```

---

### Task 4: Add logging and auth middleware

**Files:**
- Create: `app/auth/__init__.py`
- Create: `app/auth/middleware.py`
- Create: `app/services/logger.py`
- Modify: `app/main.py`
- Create: `tests/test_auth.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_auth_required():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    resp = client.get("/v1/models")
    assert resp.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py::test_auth_required -v`
Expected: FAIL (auth not enforced)

**Step 3: Write minimal implementation**

```python
# app/auth/middleware.py
from fastapi import Request
from starlette.responses import JSONResponse

async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        return JSONResponse({"error": {"message": "Invalid token", "code": "invalid_token"}}, status_code=401)
    return await call_next(request)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py::test_auth_required -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/auth/middleware.py app/services/logger.py app/main.py tests/test_auth.py
git commit -m "feat: add auth middleware and logging"
```

---

### Task 5: Implement provider interfaces

**Files:**
- Create: `app/providers/__init__.py`
- Create: `app/providers/base.py`
- Create: `app/providers/gemini.py`
- Create: `app/providers/g4f.py`
- Create: `tests/test_provider_base.py`

**Step 1: Write the failing test**

```python
from app.providers.base import BaseProvider

def test_provider_name_property():
    class Dummy(BaseProvider):
        name = "dummy"
        async def chat_completions(self, *args, **kwargs):
            return {}
        async def list_models(self):
            return []
    assert Dummy().name == "dummy"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_provider_base.py::test_provider_name_property -v`
Expected: FAIL (BaseProvider not defined)

**Step 3: Write minimal implementation**

```python
# app/providers/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Union

class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def chat_completions(self, *args, **kwargs) -> Union[dict, AsyncIterator[dict]]:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[dict]:
        raise NotImplementedError
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_provider_base.py::test_provider_name_property -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/providers/base.py tests/test_provider_base.py app/providers/__init__.py app/providers/gemini.py app/providers/g4f.py
git commit -m "feat: add provider base interface"
```

---

### Task 6: Implement Gemini provider (text + images)

**Files:**
- Modify: `app/providers/gemini.py`
- Create: `tests/test_gemini_provider.py`

**Step 1: Write the failing test**

```python
import pytest
from app.providers.gemini import GeminiProvider

def test_gemini_requires_cookie_path():
    with pytest.raises(ValueError):
        GeminiProvider(cookie_path="")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gemini_provider.py::test_gemini_requires_cookie_path -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/providers/gemini.py
from app.providers.base import BaseProvider

class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, cookie_path: str):
        if not cookie_path:
            raise ValueError("cookie_path required")
        self.cookie_path = cookie_path

    async def chat_completions(self, *args, **kwargs):
        return {"id": "stub"}

    async def list_models(self):
        return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gemini_provider.py::test_gemini_requires_cookie_path -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/providers/gemini.py tests/test_gemini_provider.py
git commit -m "feat: add gemini provider skeleton"
```

---

### Task 7: Implement g4f provider + model aggregation

**Files:**
- Modify: `app/providers/g4f.py`
- Create: `app/services/model_registry.py`
- Create: `tests/test_model_registry.py`

**Step 1: Write the failing test**

```python
from app.services.model_registry import ModelRegistry

def test_prefix_filtering():
    registry = ModelRegistry(prefixes=["qwen-"])
    models = registry.filter_models(["qwen-2.5", "gpt-4o"])
    assert models == ["qwen-2.5"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_model_registry.py::test_prefix_filtering -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/services/model_registry.py
class ModelRegistry:
    def __init__(self, prefixes: list[str]):
        self.prefixes = prefixes

    def filter_models(self, models: list[str]) -> list[str]:
        if not self.prefixes:
            return models
        return [m for m in models if any(m.startswith(p) for p in self.prefixes)]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_model_registry.py::test_prefix_filtering -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/model_registry.py tests/test_model_registry.py app/providers/g4f.py
git commit -m "feat: add model registry and prefix filtering"
```

---

### Task 8: Implement OpenAI endpoints (`/v1/models`, `/v1/chat/completions`, `/v1/images`)

**Files:**
- Create: `app/routes/__init__.py`
- Create: `app/routes/openai.py`
- Modify: `app/main.py`
- Create: `tests/test_openai_routes.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_models_endpoint():
    client = TestClient(app)
    resp = client.get("/v1/models", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_openai_routes.py::test_models_endpoint -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/routes/openai.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": []}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_openai_routes.py::test_models_endpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/routes/openai.py app/routes/__init__.py app/main.py tests/test_openai_routes.py
git commit -m "feat: add openai models endpoint"
```

---

### Task 9: Implement Claude endpoints (`/v1/messages`, `/v1/claude/models`)

**Files:**
- Create: `app/routes/claude.py`
- Modify: `app/main.py`
- Create: `tests/test_claude_routes.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_claude_models_endpoint():
    client = TestClient(app)
    resp = client.get("/v1/claude/models", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_claude_routes.py::test_claude_models_endpoint -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/routes/claude.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/v1/claude/models")
async def list_models():
    return {"data": []}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_claude_routes.py::test_claude_models_endpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/routes/claude.py app/main.py tests/test_claude_routes.py
git commit -m "feat: add claude models endpoint"
```

---

### Task 10: Wire providers, streaming, and images

**Files:**
- Modify: `app/providers/gemini.py`
- Modify: `app/providers/g4f.py`
- Modify: `app/routes/openai.py`
- Modify: `app/routes/claude.py`
- Create: `app/services/stream.py`
- Create: `tests/test_streaming.py`

**Step 1: Write the failing test**

```python
from app.services.stream import stream_chunks

def test_stream_chunks():
    chunks = list(stream_chunks(["a", "b"]))
    assert chunks == ["a", "b"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_streaming.py::test_stream_chunks -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/services/stream.py
from typing import Iterable, Iterator

def stream_chunks(items: Iterable[str]) -> Iterator[str]:
    for item in items:
        yield item
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_streaming.py::test_stream_chunks -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/stream.py tests/test_streaming.py app/routes/openai.py app/routes/claude.py app/providers/gemini.py app/providers/g4f.py
git commit -m "feat: add streaming helper"
```

---

### Task 11: Add admin endpoints and health checks

**Files:**
- Create: `app/routes/admin.py`
- Modify: `app/main.py`
- Create: `tests/test_admin_routes.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_routes.py::test_health_endpoint -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/routes/admin.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "healthy"}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_routes.py::test_health_endpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/routes/admin.py app/main.py tests/test_admin_routes.py
git commit -m "feat: add admin health endpoint"
```

---

### Task 12: End-to-end verification

**Files:**
- Modify: `README.md` (run instructions)

**Step 1: Run unit tests**

Run: `pytest -v`
Expected: PASS

**Step 2: Run lint (if configured)**

Run: `ruff check .`
Expected: PASS (or skip if not installed)

**Step 3: Manual smoke checks**

Run:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8022
curl http://localhost:8022/health
```
Expected: `health` returns 200

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add verification steps"
```

---

## Verification Checklist

- [ ] `pytest -v` passes
- [ ] `/health` returns 200
- [ ] `/v1/models` returns filtered models
- [ ] `/v1/images` returns `b64_json`
- [ ] `/v1/messages` returns Claude-compatible response

