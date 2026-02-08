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
- **🐳 Docker 部署**: 支持树莓派 5

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ai-gateway.git
cd ai-gateway

# 2. 准备配置
mkdir -p config cookies logs
cp docs/config-examples.md config/config.yaml
# 编辑 config.yaml，设置 bearer_token

# 3. 准备 Cookie
# 从浏览器获取 __Secure-1PSID 和 __Secure-1PSIDTS
# 写入 cookies/gemini.json

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
│   ├── providers/         # 模型 Provider
│   ├── routes/            # API 路由
│   ├── services/          # 业务服务
│   └── utils/             # 工具函数
├── config/                # 配置文件
│   └── config.yaml
├── cookies/               # Cookie 存储
├── docs/                  # 文档
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🛠️ 管理接口

```bash
# 更新 Cookie
curl -X POST http://localhost:8022/admin/cookies \
  -H "Authorization: Bearer your-token" \
  -d '{"__Secure-1PSID": "...", "__Secure-1PSIDTS": "..."}'

# 切换日志级别
curl -X POST http://localhost:8022/admin/logging \
  -H "Authorization: Bearer your-token" \
  -d '{"level": "DEBUG"}'

# 重载配置
curl -X POST http://localhost:8022/admin/config/reload \
  -H "Authorization: Bearer your-token"
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
