# API 接口规范

## 1. 认证

所有 API 请求（除健康检查外）都需要在请求头中携带 Bearer Token：

```
Authorization: Bearer <your-token>
```

Token 在 `config.yaml` 中配置：
```yaml
auth:
  bearer_token: "your-secure-token-here"
```

---

## 2. OpenAI 兼容端点

### 2.1 列出模型

**请求**:
```http
GET /v1/models
Authorization: Bearer <token>
```

**动态聚合流程（示意）**:
```
g4f /v1/providers  →  过滤 providers 白名单
        ↓
g4f /v1/providers/{id}  →  聚合 models
        ↓
前缀过滤 (g4f.model_prefixes)  →  /v1/models 响应
```

**响应（示例）**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gemini-2.5-pro",
      "object": "model",
      "created": 1677610602,
      "owned_by": "google"
    },
    {
      "id": "gpt-4o",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    },
    {
      "id": "qwen-*",
      "object": "model",
      "created": 1677610602,
      "owned_by": "g4f"
    },
    {
      "id": "kimi-*",
      "object": "model",
      "created": 1677610602,
      "owned_by": "g4f"
    },
    {
      "id": "glm-*",
      "object": "model",
      "created": 1677610602,
      "owned_by": "g4f"
    },
    {
      "id": "minimax-*",
      "object": "model",
      "created": 1677610602,
      "owned_by": "g4f"
    },
    {
      "id": "grok-*",
      "object": "model",
      "created": 1677610602,
      "owned_by": "g4f"
    }
  ]
}
```

> 说明：模型列表来自当前配置与 provider 可用性。网关会从 g4f `/v1/providers/{id}` 聚合模型，并按 `g4f.providers`（白名单）与 `g4f.model_prefixes`（前缀规则）过滤后返回。g4f 相关模型可能需要额外认证（API Key/Cookies）且会随 provider 状态变化。

### 2.2 聊天完成

**请求**:
```http
POST /v1/chat/completions
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "gemini-2.5-pro",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}
```

**响应（非流式）**:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gemini-2.5-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

**响应（流式）**:
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 ID，如 `gemini-2.5-pro` |
| `messages` | array | 是 | 消息列表 |
| `stream` | boolean | 否 | 是否流式响应，默认 `false` |
| `temperature` | float | 否 | 采样温度 (0-2)，Gemini 不支持 |
| `max_tokens` | integer | 否 | 最大生成 token 数 |

### 2.3 图片生成（OpenAI 兼容）

**请求**:
```http
POST /v1/images
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "gemini-2.5-pro",
  "prompt": "A futuristic city at sunset",
  "n": 1,
  "size": "1024x1024",
  "response_format": "b64_json"
}
```

**响应（示例）**:
```json
{
  "created": 1677652288,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 图像模型 ID（由模型白名单与前缀规则控制） |
| `prompt` | string | 是 | 生成提示词 |
| `n` | integer | 否 | 生成数量，默认 1 |
| `size` | string | 否 | 图像尺寸（如 `512x512`, `1024x1024`） |
| `response_format` | string | 否 | `url` 或 `b64_json`，默认 `b64_json` |
| `user` | string | 否 | 透传字段，用于审计或限流 |

**兼容性说明（差异）**:
- 仅支持“生成”场景；编辑/变体类能力如需支持会另行扩展。
- 部分 provider 可能忽略 `size` 或仅支持固定尺寸。
- `response_format` 可能受 provider 能力限制，若不支持 `url` 将返回 `b64_json`。

**字段映射与支持矩阵（OpenAI 兼容）**:

| 字段 | OpenAI 语义 | 网关处理 | 说明 |
|------|-------------|----------|------|
| `model` | 图像模型 | 必填/校验 | 需匹配白名单与前缀规则 |
| `prompt` | 生成提示词 | 必填/透传 | 空字符串将返回参数错误 |
| `n` | 生成数量 | 可选/透传 | 若 provider 不支持多图，按 1 处理 |
| `size` | 图像尺寸 | 可选/透传 | 可能被忽略或降级为固定尺寸 |
| `response_format` | 返回格式 | 可选/透传 | 不支持 `url` 时降级为 `b64_json` |
| `user` | 追踪字段 | 可选/透传 | 用于审计或限流，不影响生成 |

**能力边界**:
- 当前仅支持图像生成，不支持图像编辑/变体。
- 不支持的能力返回 `image_not_supported` 错误。

---

## 3. Claude 兼容端点

### 3.1 列出模型

**请求**:
```http
GET /v1/claude/models
Authorization: Bearer <token>
```

**响应**:
```json
{
  "data": [
    {
      "type": "model",
      "id": "gemini-2.5-pro",
      "display_name": "Gemini 2.5 Pro"
    },
    {
      "type": "model",
      "id": "claude-3-opus",
      "display_name": "Claude 3 Opus"
    }
  ]
}
```

### 3.2 消息完成

**请求**:
```http
POST /v1/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "gemini-2.5-pro",
  "max_tokens": 1024,
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}
```

**响应（非流式）**:
```json
{
  "id": "msg_01X7...",
  "type": "message",
  "role": "assistant",
  "model": "gemini-2.5-pro",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 12
  }
}
```

**响应（流式）**:
```
event: message_start
data: {"type":"message_start","message":{"id":"msg_01X7...","type":"message","role":"assistant","model":"gemini-2.5-pro"}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_stop
data: {"type":"message_stop"}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 ID |
| `messages` | array | 是 | 消息列表（仅 user/assistant） |
| `system` | string | 否 | 系统提示词 |
| `max_tokens` | integer | 是 | 最大生成 token 数 |
| `stream` | boolean | 否 | 是否流式响应 |

> 说明：Claude 文本能力通过 g4f provider 提供；图像/多模态能力不保证支持。

---

## 4. 管理端点

### 4.1 健康检查

**请求**:
```http
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "providers": {
    "gemini": "ok",
    "g4f": "ok"
  }
}
```

### 4.2 触发配置重载

**请求**:
```http
POST /admin/config/reload
Authorization: Bearer <token>
```

**响应**:
```json
{
  "status": "success",
  "message": "Configuration reloaded successfully",
  "timestamp": "2026-01-31T14:30:00"
}
```

### 4.3 更新 Cookie

**请求**:
```http
POST /admin/cookies
Authorization: Bearer <token>
Content-Type: application/json

{
  "__Secure-1PSID": "g.a000...",
  "__Secure-1PSIDTS": "sidts-CjEB..."
}
```

**响应**:
```json
{
  "status": "success",
  "message": "Cookies updated and provider reloaded",
  "timestamp": "2026-01-31T14:30:00"
}
```

### 4.4 查看 Cookie 状态

**请求**:
```http
GET /admin/cookies/status
Authorization: Bearer <token>
```

**响应**:
```json
{
  "has_psid": true,
  "has_psidts": true,
  "updated_at": "2026-01-31T14:30:00",
  "auto_refresh": true
}
```

### 4.5 切换日志级别

**请求**:
```http
POST /admin/logging
Authorization: Bearer <token>
Content-Type: application/json

{
  "level": "DEBUG"
}
```

**响应**:
```json
{
  "status": "success",
  "level": "DEBUG",
  "previous_level": "INFO"
}
```

**支持的日志级别**: `DEBUG`, `INFO`, `WARNING`, `ERROR`

---

## 5. 错误响应

### 5.1 通用错误格式

```json
{
  "error": {
    "message": "Invalid model: gemini-99",
    "type": "invalid_request_error",
    "code": "model_not_found"
  }
}
```

### 5.2 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 401 | 认证失败（Token 无效） |
| 404 | 模型不存在 |
| 422 | 请求参数错误 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（Provider 故障） |

### 5.3 错误代码

| 代码 | 说明 |
|------|------|
| `model_not_found` | 模型不存在 |
| `invalid_token` | Token 无效 |
| `cookie_expired` | Cookie 已过期 |
| `provider_error` | Provider 调用失败 |
| `rate_limit` | 请求过于频繁 |
| `image_not_supported` | 图像能力不可用或 provider 不支持 |

---

## 6. 客户端配置示例

### 6.1 OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8022/v1",
    api_key="your-bearer-token"
)

# 非流式
response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)

# 流式
stream = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### 6.2 Claude Code CLI

```bash
# 设置环境变量
export ANTHROPIC_BASE_URL=http://localhost:8022
export ANTHROPIC_API_KEY=your-bearer-token

# 启动 Claude Code
claude

# 或指定模型
claude --model gemini-2.5-pro
```

### 6.3 cURL 示例

```bash
# 列出模型（OpenAI 格式）
curl http://localhost:8022/v1/models \
  -H "Authorization: Bearer your-token"

# 列出模型（Claude 格式）
curl http://localhost:8022/v1/claude/models \
  -H "Authorization: Bearer your-token"

# 聊天完成
curl http://localhost:8022/v1/chat/completions \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# 流式响应
curl http://localhost:8022/v1/chat/completions \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

---

*文档版本: 1.0*
*更新日期: 2026-01-31*
