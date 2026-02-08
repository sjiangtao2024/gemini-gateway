# AI-Gateway 上传文件清单

> **目标服务器**: `toddsun@192.168.1.112:~/aiproxy/ai-gateway/`  
> **创建时间**: 2026-02-09  
> **项目版本**: 1.0.0

---

## 📁 上传命令

```bash
# 在项目根目录执行
rsync -avz \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='agent-rules' \
  ./ toddsun@192.168.1.112:~/aiproxy/ai-gateway/
```

---

## 📂 必需上传的文件夹

### 1. app/ - 应用程序代码
```
app/
├── __init__.py
├── main.py                    # FastAPI 入口
├── auth/
│   ├── __init__.py
│   └── middleware.py          # Bearer 认证中间件
├── config/
│   ├── __init__.py
│   ├── settings.py            # Pydantic 配置模型
│   ├── manager.py             # 配置管理器
│   └── watcher.py             # 热重载观察器
├── middlewares/
│   ├── __init__.py
│   └── logging.py             # 请求日志中间件
├── providers/
│   ├── __init__.py
│   ├── base.py                # Provider 基类
│   ├── gemini.py              # Gemini Provider
│   └── g4f.py                 # g4f Provider
├── routes/
│   ├── __init__.py
│   ├── openai.py              # OpenAI 协议路由
│   ├── claude.py              # Claude 协议路由
│   ├── admin.py               # 管理接口路由
│   └── files.py               # 文件上传路由
├── services/
│   ├── __init__.py
│   ├── logger.py              # 日志服务
│   ├── model_registry.py      # 模型注册表
│   ├── stream.py              # 流式处理
│   └── file_manager.py        # 文件管理服务
└── utils/
    ├── __init__.py
    └── errors.py              # 错误处理模块
```

### 2. docs/ - 文档
```
docs/
├── architecture.md            # 架构设计文档
├── api-spec.md                # API 接口规范
├── config-examples.md         # 配置示例
├── deployment.md              # 部署指南
├── troubleshooting.md         # 故障排查
└── plans/                     # 开发计划（可选）
    ├── 2026-02-08-rename-and-phase1.md
    ├── 2026-02-08-phase2-claude-protocol.md
    ├── 2026-02-08-phase3-multimodal.md
    ├── 2026-02-08-phase4-stability.md
    ├── 2026-02-08-phase5-hot-reload.md
    ├── 2026-02-09-cookie-restructure.md
    └── 2026-02-09-integrate-g4f-library.md
```

### 3. tests/ - 测试文件
```
tests/
├── __init__.py
├── test_claude_format.py      # Claude 格式测试
├── test_multimodal.py         # 多模态测试
├── test_errors.py             # 错误处理测试
├── test_config_watcher.py     # 配置热重载测试
├── test_admin_routes.py       # 管理接口测试
├── test_auth.py               # 认证测试
├── test_claude_messages.py    # Claude 消息测试
├── test_claude_routes.py      # Claude 路由测试
├── test_config_reload.py      # 配置重载测试
├── test_g4f_provider.py       # g4f Provider 测试
├── test_gemini_provider.py    # Gemini Provider 测试
├── test_model_registry.py     # 模型注册表测试
├── test_openai_images.py      # OpenAI 图像测试
├── test_openai_routes.py      # OpenAI 路由测试
├── test_provider_base.py      # Provider 基类测试
├── test_settings.py           # 设置测试
├── test_settings_env.py       # 环境变量测试
└── test_streaming.py          # 流式测试
```

### 4. config/ - 配置文件（需要创建并配置）
```
config/
└── config.yaml                # 主配置文件（需要手动创建或从模板复制）
```

**注意**: 初始部署时需要创建 `config/config.yaml`，可参考 `docs/config-examples.md`

---

## 📄 必需上传的独立文件

### 根目录文件
| 文件名 | 用途 | 必需 |
|--------|------|------|
| `README.md` | 项目说明 | ✅ |
| `requirements.txt` | Python 依赖 | ✅ |
| `Dockerfile` | Docker 镜像构建 | ✅ |
| `docker-compose.yml` | Docker Compose 配置 | ✅ |
| `.dockerignore` | Docker 忽略规则 | ✅ |
| `.gitignore` | Git 忽略规则 | ✅ |
| `LICENSE` | 许可证 | 可选 |
| `PROJECT_SUMMARY.md` | 项目总结 | 可选 |

---

## 🚫 不需要上传的文件/文件夹

| 路径/文件 | 原因 |
|-----------|------|
| `.git/` | Git 仓库数据，远程不需要 |
| `venv/` | Python 虚拟环境，服务器会重新创建 |
| `__pycache__/` | Python 缓存，会自动生成 |
| `*.pyc` | 编译后的 Python 字节码 |
| `.pytest_cache/` | pytest 缓存 |
| `data/` | 数据目录，服务器本地创建 |
| `logs/` | 日志目录，服务器本地创建 |

---

## 📋 服务器部署步骤

### 1. 上传文件后，在服务器上执行：

```bash
ssh toddsun@192.168.1.112

cd ~/aiproxy/ai-gateway

# 创建数据目录
mkdir -p config data/gemini data/g4f/{cookies,har,media} logs

# 复制配置模板
cp docs/config-examples.md config/config.yaml

# 编辑配置文件
vim config/config.yaml
```

### 2. 准备 Cookie 文件

**Gemini Cookie**:
```bash
# 编辑 data/gemini/cookies.json
vim data/gemini/cookies.json
```
内容格式：
```json
{
  "__Secure-1PSID": "your-psid-here",
  "__Secure-1PSIDTS": "your-psidts-here",
  "updated_at": "2026-02-09T00:00:00"
}
```

**g4f HAR/Cookie**（ChatGPT、Kimi、Qwen 等）:
```bash
# 方式 1：API 上传 HAR 文件（ChatGPT 需要）
curl -X POST http://localhost:8022/admin/files/har \
  -H "Authorization: Bearer your-token" \
  -F "file=@chat.openai.com.har" \
  -F "provider=openai"

# 方式 2：API 上传 Cookie 文件（Kimi、Qwen 等）
curl -X POST http://localhost:8022/admin/files/cookie \
  -H "Authorization: Bearer your-token" \
  -F "file=@kimi.com.json" \
  -F "domain=kimi.com"

# 方式 3：直接复制到目录（无需重启，g4f 自动读取）
cp chat.openai.com.har ./data/g4f/har/
cp kimi.com.json ./data/g4f/cookies/
```

**data/g4f/media/ 目录说明**：
此目录用于存储 g4f 生成的媒体文件（图片、音频等），由 g4f 库自动写入。例如：
- Bing Image Creator 生成的图片
- Pollinations AI 生成的图片

**支持的 Provider 和文件类型**：
| Provider | 文件类型 | 文件名示例 |
|---------|---------|-----------|
| ChatGPT | HAR | `chat.openai.com.har` |
| Kimi | Cookie JSON | `kimi.com.json` |
| Qwen | Cookie JSON | `qwen.com.json` |
| GLM | Cookie JSON | `chatglm.cn.json` |
| Grok | Cookie JSON | `grok.com.json` |

### 3. 启动服务

```bash
docker-compose up -d

# 查看日志
docker-compose logs -f

# 验证
curl http://localhost:8022/health
```

---

## 🔧 配置文件关键项

### config.yaml 必须修改的项：

```yaml
auth:
  bearer_token: "your-secure-token-here"  # ← 必须修改

gemini:
  enabled: true
  cookie_path: "/app/data/gemini/cookies.json"  # ← 确认路径正确

g4f:
  enabled: false        # ← 根据需要启用
  cookies_dir: "/app/har_and_cookies"  # g4f 读取 cookie 的目录
```

---

## 📊 文件统计

| 类别 | 数量 | 大小估算 |
|------|------|----------|
| Python 代码文件 | ~35 | ~50 KB |
| 测试文件 | ~19 | ~30 KB |
| 文档 | ~10 | ~100 KB |
| 配置文件 | ~6 | ~10 KB |
| **总计** | **~70** | **~200 KB** |

---

## ⚠️ 注意事项

1. **权限**: 确保 `data/gemini/` 目录在容器内可读写
2. **端口**: 默认使用 8022 端口，确保服务器防火墙开放
3. **Cookie**: Gemini Cookie 需要定期更新（有自动刷新机制）
4. **日志**: 日志文件会写入 `logs/` 目录，注意磁盘空间

---

*上传完成后，请参考 `docs/deployment.md` 进行详细部署配置*
