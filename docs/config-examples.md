# 配置示例

## 1. 基础配置 (config.yaml)

```yaml
# ============================================
# Gemini-Gateway 配置文件
# ============================================

server:
  host: "0.0.0.0"      # 监听地址，0.0.0.0 允许外部访问
  port: 8022           # 服务端口

auth:
  bearer_token: "your-secure-token-here"  # 认证令牌，请修改！

logging:
  level: "INFO"        # 日志级别: DEBUG, INFO, WARNING, ERROR
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
  file: "/app/logs/gateway.log"
  rotation: "10 MB"    # 日志轮转大小
  retention: "7 days"  # 日志保留时间

gemini:
  enabled: true
  cookie_path: "/app/cookies/gemini.json"
  auto_refresh: true   # 自动刷新 __Secure-1PSIDTS
  models:
    - "gemini-2.5-pro"
    - "gemini-2.5-flash"
    - "gemini-3.0-pro"
    - "gemini-2.0-flash"
  # 可选：代理配置
  # proxy: "http://proxy.example.com:8080"

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
    enabled: true      # Gemini 失败时尝试 G4F
    max_retries: 2
    timeout: 30        # 秒
  # 提示：可通过 g4f 的 /v1/providers 接口查看可用 provider 与模型列表
```

## 2. Cookie 文件 (cookies/gemini.json)

```json
{
  "__Secure-1PSID": "g.a000...",
  "__Secure-1PSIDTS": "sidts-CjEB...",
  "updated_at": "2026-01-31T14:30:00"
}
```

### 如何获取 Cookie

1. 在浏览器中登录 https://gemini.google.com
2. 打开开发者工具 (F12) → Application/Storage → Cookies
3. 复制 `__Secure-1PSID` 和 `__Secure-1PSIDTS` 的值
4. 粘贴到上面的 JSON 文件中

## 3. Docker Compose 配置

### 3.1 标准部署

```yaml
version: '3.8'

services:
  gemini-gateway:
    build: .
    container_name: gemini-gateway
    ports:
      - "8022:8022"
    volumes:
      # 配置文件（只读挂载）
      - ./config/config.yaml:/app/config/config.yaml:ro
      # Cookie 文件（读写挂载）
      - ./cookies:/app/cookies
      # 日志目录
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - TZ=Asia/Shanghai
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8022/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 3.2 树莓派 5 优化版

```yaml
version: '3.8'

services:
  gemini-gateway:
    build: .
    container_name: gemini-gateway
    ports:
      - "8022:8022"
    volumes:
      - ./config/config.yaml:/app/config/config.yaml:ro
      - ./cookies:/app/cookies
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
    # 资源限制
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
    restart: unless-stopped
```

### 3.3 开发环境（启用热重载）

```yaml
version: '3.8'

services:
  gemini-gateway:
    build: .
    container_name: gemini-gateway-dev
    ports:
      - "8022:8022"
    volumes:
      # 代码热重载（开发模式）
      - ./app:/app/app
      # 配置热重载
      - ./config:/app/config
      - ./cookies:/app/cookies
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG  # 开发模式详细日志
    command: ["python", "-m", "app.main", "--reload"]
```

## 4. 环境变量

可以通过环境变量覆盖配置文件：

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `CONFIG_PATH` | 配置文件路径 | `/app/config/config.yaml` |
| `COOKIE_PATH` | Cookie 文件路径 | `/app/cookies/gemini.json` |
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `ERROR` |
| `BEARER_TOKEN` | 认证令牌（优先于配置文件） | `your-token` |
| `GEMINI_PROXY` | Gemini 代理 | `http://proxy:8080` |

### 使用环境变量的 Docker Compose

```yaml
version: '3.8'

services:
  gemini-gateway:
    build: .
    ports:
      - "8022:8022"
    volumes:
      - ./cookies:/app/cookies
      - ./logs:/app/logs
    environment:
      - BEARER_TOKEN=${BEARER_TOKEN}  # 从 .env 文件读取
      - LOG_LEVEL=INFO
```

配合 `.env` 文件：
```
BEARER_TOKEN=your-secure-token-here
```

### 4.1 g4f 模型列表自动同步（可选）

以下脚本会从 g4f 的 `/v1/providers` 与 `/v1/providers/{id}` 拉取可用模型列表，输出为可直接粘贴到 `config.yaml` 的 `g4f.models` 片段。

```bash
# 可选：指定 g4f API 基础地址（默认本地 1337）
export G4F_BASE_URL=http://localhost:1337/v1
# 可选：仅同步指定 provider（如 HuggingChat）
export G4F_PROVIDER=HuggingChat

python - <<'PY'
import json
import os
import sys
from urllib.request import urlopen

base_url = os.getenv("G4F_BASE_URL", "http://localhost:1337/v1").rstrip("/")
provider_filter = os.getenv("G4F_PROVIDER")

def get_json(url: str):
    with urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

providers = get_json(f"{base_url}/providers")
provider_ids = [p["id"] for p in providers]
if provider_filter:
    provider_ids = [pid for pid in provider_ids if pid == provider_filter]

models = set()
for pid in provider_ids:
    details = get_json(f"{base_url}/providers/{pid}")
    for m in details.get("models", []):
        models.add(m)

print("g4f:")
print("  models:")
for m in sorted(models):
    print(f"    - \"{m}\"")
PY
```

## 5. Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8022;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

## 6. Systemd 服务（裸机部署）

```ini
# /etc/systemd/system/gemini-gateway.service
[Unit]
Description=Gemini Gateway
After=network.target

[Service]
Type=simple
User=gateway
WorkingDirectory=/opt/gemini-gateway
Environment=PYTHONUNBUFFERED=1
Environment=CONFIG_PATH=/opt/gemini-gateway/config/config.yaml
ExecStart=/opt/gemini-gateway/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable gemini-gateway
sudo systemctl start gemini-gateway
sudo systemctl status gemini-gateway
```

---

*配置文档版本: 1.0*
