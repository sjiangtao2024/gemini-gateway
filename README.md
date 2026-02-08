# AI-Gateway

一个支持 OpenAI 和 Claude 双协议的 AI 模型网关，统一接入 Gemini、ChatGPT 及其他开源模型。

## ✨ 核心特性

- **🤖 多模型支持**: Gemini 2.5/3.0 (主力) + ChatGPT/Claude (备选，通过 gpt4free)
- **🔄 双协议兼容**: OpenAI (`/v1/chat/completions`) + Claude (`/v1/messages`)
- **📡 流式响应**: 支持 SSE (Server-Sent Events)
- **🔧 配置热重载**: 修改配置无需重启服务
- **📊 动态日志**: 运行时切换日志级别 (DEBUG/INFO/ERROR)
- **🔐 Bearer 认证**: 标准 Token 认证
- **🍪 Cookie 管理**: API 接口更新，支持自动刷新
- **📁 文件管理**: 支持 HAR/Cookie 文件上传，统一管理多 Provider
- **🐳 Docker 部署**: 支持树莓派 5

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ai-gateway.git
cd ai-gateway

# 2. 准备配置
mkdir -p config data/gemini data/g4f/{cookies,har,media} logs
cp docs/config-examples.md config/config.yaml
# 编辑 config.yaml，设置 bearer_token

# 3. 准备 Cookie
# Gemini: 从浏览器获取 __Secure-1PSID 和 __Secure-1PSIDTS
# 写入 data/gemini/cookies.json
# 
# g4f: 将 HAR/Cookie 文件放入对应目录
# - data/g4f/har/       (HAR 抓包文件)
# - data/g4f/cookies/   (Cookie JSON 文件)

# 4. 启动
docker-compose up -d

# 5. 验证
curl http://localhost:8022/health
```

### 使用示例

**OpenAI 客户端**:
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8022/v1",
    api_key="your-bearer-token"
)

response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)
```

**Claude Code CLI**:
```bash
export ANTHROPIC_BASE_URL=http://localhost:8022
export ANTHROPIC_API_KEY=your-bearer-token
claude --model gemini-2.5-pro
```

## 📚 文档

- [架构设计](docs/architecture.md) - 系统架构和技术选型
- [API 规范](docs/api-spec.md) - 完整的 API 接口文档
- [配置示例](docs/config-examples.md) - 配置文件参考
- [部署指南](docs/deployment.md) - 详细部署步骤
- [故障排查](docs/troubleshooting.md) - 常见问题定位

## 🏗️ 项目结构

```
ai-gateway/
├── app/                    # 应用代码
│   ├── main.py            # FastAPI 入口
│   ├── config/            # 配置管理
│   ├── middlewares/       # 中间件
│   ├── providers/         # 模型 Provider
│   ├── routes/            # API 路由
│   ├── services/          # 业务服务
│   └── utils/             # 工具函数
├── config/                # 配置文件
│   └── config.yaml
├── data/                  # 数据目录
│   ├── gemini/            # Gemini Cookie
│   │   └── cookies.json
│   └── g4f/               # g4f 数据
│       ├── cookies/       # Cookie JSON
│       ├── har/           # HAR 文件
│       └── media/         # 生成媒体
├── logs/                  # 日志文件
├── docs/                  # 文档
├── tests/                 # 测试
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🛠️ 管理接口

### Cookie 管理

**Gemini Cookie**（支持自动刷新）
```bash
# 更新 Gemini Cookie
curl -X POST http://localhost:8022/admin/cookies \
  -H "Authorization: Bearer your-token" \
  -d '{"__Secure-1PSID": "...", "__Secure-1PSIDTS": "..."}'
```

**g4f Cookie/HAR**（ChatGPT、Kimi、Qwen 等）
```bash
# 方式 1：API 上传 HAR 文件
curl -X POST http://localhost:8022/admin/files/har \
  -H "Authorization: Bearer your-token" \
  -F "file=@chat.openai.com.har" \
  -F "provider=openai"

# 方式 2：API 上传 Cookie 文件
curl -X POST http://localhost:8022/admin/files/cookie \
  -H "Authorization: Bearer your-token" \
  -F "file=@kimi.com.json" \
  -F "domain=kimi.com"

# 方式 3：直接放入目录（无需重启）
cp chat.openai.com.har ./data/g4f/har/
cp kimi.com.json ./data/g4f/cookies/

# 查看已上传的文件
curl http://localhost:8022/admin/files \
  -H "Authorization: Bearer your-token"
```

### 系统管理
```bash
# 切换日志级别
curl -X POST http://localhost:8022/admin/logging \
  -H "Authorization: Bearer your-token" \
  -d '{"level": "DEBUG"}'

# 重载配置
curl -X POST http://localhost:8022/admin/config/reload \
  -H "Authorization: Bearer your-token"

# 健康检查
curl http://localhost:8022/health
```

## ✅ 验证步骤（开发）

> 使用 uv 管理 Python 环境。

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
pytest -v
```

---

*Made with ❤️ for AI enthusiasts*
