# Findings & Decisions

## Requirements
<!-- Captured from user request -->

### 功能需求
1. **多模型支持**
   - Gemini 2.5 Pro/Flash、Gemini 3.0 Pro（主力）
   - ChatGPT GPT-4o/4o-mini（备选，通过 gpt4free）
   - 直接暴露真实模型名，无映射

2. **双协议支持**
   - OpenAI 协议：`/v1/chat/completions`、`/v1/models`
   - Claude 协议：`/v1/messages`、`/v1/models`
   - 均支持流式响应（SSE）

3. **认证机制**
   - HTTP Header: `Authorization: Bearer <token>`
   - Token 在配置文件中定义

4. **配置管理**
   - 配置文件挂载到容器
   - 支持热重载（不重启服务）
   - 支持日志级别动态切换

5. **账号支持**
   - 当前：单 Gemini 账号
   - 预留：多账号扩展接口

### 非功能需求
- 树莓派 5 + Docker 部署
- 详细/简洁日志可切换
- 高可用、易维护

## Research Findings

### gemini-webapi 分析
- **版本**: 1.17.3（最新，2025-12-05）
- **功能**: 支持 Gemini 2.5/3.0、自动 Cookie 刷新、流式响应
- **Breaking Changes**: 1.10.0 废弃 `images` 参数，改用 `files`
- **认证**: Cookie-based（`__Secure-1PSID`、`__Secure-1PSIDTS`）

### gpt4free 分析
- **作用**: 聚合多个免费 AI API
- **支持模型**: GPT-4o、Claude-3、DeepSeek 等
- **稳定性**: 免费服务，可能不稳定，需要 fallback
- **协议**: 提供 OpenAI 兼容接口

### 协议差异
| 特性 | OpenAI | Claude |
|------|--------|--------|
| 端点 | `/v1/chat/completions` | `/v1/messages` |
| 系统提示 | `messages` 中 role=system | 独立 `system` 字段 |
| 流式格式 | `data: {...}\n\n` | `event: type\ndata: {...}\n\n` |
| 模型字段 | `model` | `model` |
| 消息格式 | `{role, content}` | `{role, content}` |

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI 框架 | 原生异步支持、自动 OpenAPI 文档、SSE 支持好 |
| Pydantic Settings | 类型安全、环境变量支持、配置验证 |
| 配置文件 YAML | 易读、支持注释、层级结构清晰 |
| 热重载：文件监听 | 使用 `watchdog` 库监听配置文件变化 |
| 日志：Loguru + 动态级别 | 支持运行时切换，无需重启 |
| 单进程单账号 | 简化初期，预留多账号管理接口 |
| Bearer Token 认证 | 标准、兼容 OpenAI/Claude 客户端 |
| 流式响应：SSE | Codex/Claude Code 都使用 SSE |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 无 | - |

## Doc Review Findings (2026-01-31)
- `docs/deployment.md`: “cp docs/config-examples.md config/config.yaml” 将 Markdown 复制为 YAML 不可用，应改为从示例中拷贝 YAML 片段或提供 `config/config.yaml` 模板文件。
- `docs/architecture.md` vs `docs/api-spec.md`/`docs/deployment.md`: 管理端点路径不一致（`/admin/config` vs `/admin/config/reload`），需要统一。
- `docs/api-spec.md`: `/v1/models` 既用于 OpenAI 也用于 Claude 格式响应，需说明选择机制（例如基于请求头/参数/路径前缀）或拆分端点避免歧义。
- `docs/config-examples.md`: 开发环境示例把 `./app` 只读挂载且使用 `--reload`，会阻断热重载/代码改动；建议改为可写挂载或说明这是仅配置热重载。
- `docs/deployment.md`: “查看当前配置” 使用 `/admin/config`，而 API 规范只给出 `/admin/config/reload`；需要补充查询端点或修正示例。

## Resources
- gemini-webapi: https://github.com/HanaokaYuzu/Gemini-API
- gpt4free: https://github.com/xtekky/gpt4free
- FastAPI: https://fastapi.tiangolo.com/
- Claude API 文档: https://docs.anthropic.com/claude/reference/messages_post
- OpenAI API 文档: https://platform.openai.com/docs/api-reference

## Visual/Browser Findings
- gemini-webapi 1.17.3 支持 Gemini 3.0 Pro
- gpt4free 支持多种 provider  fallback
- Claude Code CLI 使用 SSE 流式响应

---
*Generated: 2026-01-31*

## 2026-02-01
- Reviewed `docs/api-spec.md` and `docs/deployment.md` for update points.
- `docs/api-spec.md` currently lacks `/v1/images` OpenAI-compatible section and does not note Claude text-only limitations.
- `docs/deployment.md` currently lacks g4f browser/Chrome requirements, `har_and_cookies` and `generated_media` volume guidance, and optional 7900 login port.
- Reviewed `docs/architecture.md` and `docs/config-examples.md`; they lack multimodal/image flow, provider whitelist + prefix filtering, and dynamic provider/model aggregation notes.
- `docs/config-examples.md` currently includes a g4f model sync script; needs adaptation to provider whitelist + prefix filtering and g4f cookie/har directories.
- Updated docs to include OpenAI-compatible /v1/images, Claude text-only note, provider whitelist/prefix filtering, and dynamic model aggregation via g4f providers.
- Added Docker guidance for g4f browser dependencies, shm_size, har_and_cookies, generated_media, and optional 7900 login port.
- Added /v1/images field mapping matrix and capability boundaries to docs/api-spec.md for OpenAI-compatible image requests.
