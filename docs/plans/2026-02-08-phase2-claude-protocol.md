# Phase 2: Claude 协议支持实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 实现 Claude 协议对 Gemini 模型的支持，让 Claude Code CLI 可以直接调用 Gemini

**Architecture:** Claude 协议请求 → 格式转换为 OpenAI 格式 → 调用对应 Provider → 结果转换回 Claude 格式

**Tech Stack:** FastAPI, Pydantic

---

## 背景信息

### 当前 app/routes/claude.py 状态
```python
from fastapi import APIRouter, HTTPException

from app.providers.g4f import G4FProvider

router = APIRouter()

_gemini_models: list[str] = []
_g4f_models: list[str] = []
_g4f: G4FProvider | None = None


def configure(gemini_models: list[str], g4f_models: list[str], g4f: G4FProvider | None) -> None:
    global _gemini_models, _g4f_models, _g4f
    _gemini_models = gemini_models
    _g4f_models = g4f_models
    _g4f = g4f


def _is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-")


@router.get("/v1/claude/models")
async def list_models():
    models = _gemini_models + _g4f_models
    return {"data": [{"type": "model", "id": m, "display_name": m} for m in models]}


@router.post("/v1/messages")
async def messages(payload: dict):
    model = payload.get("model", "")
    if _is_gemini_model(model):
        raise HTTPException(status_code=501, detail="Gemini not supported for Claude protocol")
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    return await _g4f.chat_completions(payload)
```

### Claude 协议格式

**请求格式:**
```json
{
  "model": "gemini-2.5-pro",
  "messages": [{"role": "user", "content": "Hello!"}],
  "system": "You are helpful",
  "max_tokens": 1024,
  "stream": false
}
```

**响应格式:**
```json
{
  "id": "msg_01X7...",
  "type": "message",
  "role": "assistant",
  "model": "gemini-2.5-pro",
  "content": [{"type": "text", "text": "Hello!"}],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 10, "output_tokens": 12}
}
```

### OpenAI 协议格式（用于 Provider 调用）

**请求:**
```json
{
  "model": "gemini-2.5-pro",
  "messages": [
    {"role": "system", "content": "You are helpful"},
    {"role": "user", "content": "Hello!"}
  ]
}
```

**响应:**
```json
{
  "choices": [{"message": {"role": "assistant", "content": "Hello!"}}]
}
```

---

## Task 1: 更新 Claude 路由配置

**Files:**
- Modify: `app/routes/claude.py`

**Step 1: 更新 configure 函数接收 Gemini Provider**

```python
from app.providers.gemini import GeminiProvider
from app.providers.g4f import G4FProvider

_gemini: GeminiProvider | None = None
_g4f: G4FProvider | None = None
_gemini_models: list[str] = []
_g4f_models: list[str] = []

def configure(
    gemini_models: list[str],
    g4f_models: list[str],
    gemini: GeminiProvider | None = None,
    g4f: G4FProvider | None = None
) -> None:
    global _gemini_models, _g4f_models, _gemini, _g4f
    _gemini_models = gemini_models
    _g4f_models = g4f_models
    _gemini = gemini
    _g4f = g4f
```

**Step 2: Test import**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -c "from app.routes.claude import router; print('Import OK')"
```

**Step 3: Commit**

```bash
git add app/routes/claude.py
git commit -m "refactor(claude): update configure to accept both providers

- Add GeminiProvider parameter to configure function
- Prepare for Gemini support in Claude protocol"
```

---

## Task 2: 实现 Claude ↔ OpenAI 格式转换

**Files:**
- Modify: `app/routes/claude.py`

**Step 1: 添加 Pydantic 模型**

```python
from pydantic import BaseModel
from typing import Literal

class ClaudeMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ClaudeRequest(BaseModel):
    model: str
    messages: list[ClaudeMessage]
    system: str | None = None
    max_tokens: int | None = None
    stream: bool = False

class ClaudeContent(BaseModel):
    type: Literal["text"] = "text"
    text: str

class ClaudeUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

class ClaudeResponse(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    model: str
    content: list[ClaudeContent]
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence"] = "end_turn"
    usage: ClaudeUsage
```

**Step 2: 实现转换函数**

```python
import uuid

def _claude_to_openai_messages(claude_req: ClaudeRequest) -> list[dict]:
    """将 Claude 请求转换为 OpenAI 格式"""
    messages = []
    
    # 处理 system prompt
    if claude_req.system:
        messages.append({"role": "system", "content": claude_req.system})
    
    # 转换 messages
    for msg in claude_req.messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    return messages

def _openai_to_claude_response(openai_result: dict, model: str) -> ClaudeResponse:
    """将 OpenAI 格式结果转换为 Claude 格式"""
    # 提取文本内容
    text = ""
    if "text" in openai_result:
        text = openai_result["text"]
    elif "choices" in openai_result and openai_result["choices"]:
        text = openai_result["choices"][0].get("message", {}).get("content", "")
    
    # 估算 token 数 (简化处理)
    input_tokens = len(str(openai_result.get("messages", []))) // 4
    output_tokens = len(text) // 4
    
    return ClaudeResponse(
        id=f"msg_{uuid.uuid4().hex[:24]}",
        model=model,
        content=[ClaudeContent(text=text)],
        usage=ClaudeUsage(input_tokens=input_tokens, output_tokens=output_tokens)
    )
```

**Step 3: Test import**

```bash
python3 -c "from app.routes.claude import router; print('Import OK')"
```

**Step 4: Commit**

```bash
git add app/routes/claude.py
git commit -m "feat(claude): add request/response format conversion

- Add ClaudeRequest, ClaudeResponse Pydantic models
- Implement _claude_to_openai_messages conversion
- Implement _openai_to_claude_response conversion"
```

---

## Task 3: 实现 /v1/messages 支持 Gemini

**Files:**
- Modify: `app/routes/claude.py`

**Step 1: 重写 messages 端点**

```python
@router.post("/v1/messages")
async def messages(payload: ClaudeRequest):
    """Claude 协议消息完成 - 支持 Gemini 和 g4f"""
    model = payload.model
    
    if _is_gemini_model(model):
        if _gemini is None:
            raise HTTPException(status_code=503, detail="Gemini provider not configured")
        
        # 转换为 OpenAI 格式并调用
        openai_messages = _claude_to_openai_messages(payload)
        result = await _gemini.chat_completions(
            messages=openai_messages,
            model=model
        )
        
        return _openai_to_claude_response(result, model)
    
    # g4f 模型
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    
    # g4f 可以直接接受 OpenAI 格式
    openai_payload = {
        "model": model,
        "messages": _claude_to_openai_messages(payload)
    }
    result = await _g4f.chat_completions(openai_payload)
    
    return _openai_to_claude_response(result, model)
```

**Step 2: Test import**

```bash
python3 -c "from app.routes.claude import router; print('Import OK')"
```

**Step 3: Commit**

```bash
git add app/routes/claude.py
git commit -m "feat(claude): implement /v1/messages with Gemini support

- Support gemini-* models via GeminiProvider
- Support other models via g4f provider
- Full request/response format conversion"
```

---

## Task 4: 更新 main.py 配置

**Files:**
- Modify: `app/main.py`

**Step 1: 更新 configure_claude 调用**

```python
# 原代码:
configure_claude(settings.gemini.models, g4f_models, g4f_provider)

# 改为:
configure_claude(settings.gemini.models, g4f_models, gemini_provider, g4f_provider)
```

**Step 2: Test import**

```bash
python3 -c "from app.main import app; print('Main import OK')"
```

**Step 3: Commit**

```bash
git add app/main.py
git commit -m "refactor(main): update configure_claude with both providers"
```

---

## Task 5: 添加单元测试

**Files:**
- Create: `tests/test_claude_format.py`

**Step 1: 创建测试文件**

```python
import pytest
from app.routes.claude import (
    ClaudeRequest, ClaudeMessage,
    _claude_to_openai_messages,
    _openai_to_claude_response
)

class TestClaudeFormatConversion:
    """测试 Claude ↔ OpenAI 格式转换"""
    
    def test_claude_to_openai_basic(self):
        """测试基本消息转换"""
        req = ClaudeRequest(
            model="gemini-2.5-pro",
            messages=[
                ClaudeMessage(role="user", content="Hello!")
            ]
        )
        
        result = _claude_to_openai_messages(req)
        
        assert result == [{"role": "user", "content": "Hello!"}]
    
    def test_claude_to_openai_with_system(self):
        """测试带 system prompt 的转换"""
        req = ClaudeRequest(
            model="gemini-2.5-pro",
            messages=[
                ClaudeMessage(role="user", content="Hello!")
            ],
            system="You are helpful"
        )
        
        result = _claude_to_openai_messages(req)
        
        assert result == [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello!"}
        ]
    
    def test_openai_to_claude_basic(self):
        """测试基本响应转换"""
        openai_result = {
            "text": "Hello! How can I help?"
        }
        
        result = _openai_to_claude_response(openai_result, "gemini-2.5-pro")
        
        assert result.model == "gemini-2.5-pro"
        assert result.role == "assistant"
        assert len(result.content) == 1
        assert result.content[0].text == "Hello! How can I help?"
        assert result.stop_reason == "end_turn"
    
    def test_openai_to_claude_from_choices(self):
        """测试从 choices 格式转换"""
        openai_result = {
            "choices": [
                {"message": {"role": "assistant", "content": "Sure!"}}
            ]
        }
        
        result = _openai_to_claude_response(openai_result, "gpt-4o")
        
        assert result.content[0].text == "Sure!"
```

**Step 2: 运行测试**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -m pytest tests/test_claude_format.py -v
```

**Step 3: Commit**

```bash
git add tests/test_claude_format.py
git commit -m "test(claude): add format conversion tests

- Test _claude_to_openai_messages with and without system prompt
- Test _openai_to_claude_response from different result formats"
```

---

## 验证清单

完成所有任务后验证：

```bash
# 1. 检查所有导入
python3 -c "
from app.routes.claude import router, ClaudeRequest, ClaudeResponse
from app.main import app
print('✅ All imports OK')
"

# 2. 运行测试
python3 -m pytest tests/test_claude_format.py -v

# 3. 检查代码风格
python3 -m py_compile app/routes/claude.py
python3 -m py_compile app/main.py
```

---

## 提交历史

1. `refactor(claude): update configure to accept both providers`
2. `feat(claude): add request/response format conversion`
3. `feat(claude): implement /v1/messages with Gemini support`
4. `refactor(main): update configure_claude with both providers`
5. `test(claude): add format conversion tests`

---

## 预期结果

完成后 Claude Code CLI 可以：

```bash
export ANTHROPIC_BASE_URL=http://localhost:8022
export ANTHROPIC_API_KEY=your-token
claude --model gemini-2.5-pro
```

正常工作。
