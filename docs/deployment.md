# 部署指南

## 1. 系统要求

### 1.1 硬件要求

| 环境 | CPU | 内存 | 存储 |
|------|-----|------|------|
| 开发环境 | 2 核 | 2 GB | 10 GB |
| 生产环境 | 2 核 | 4 GB | 20 GB |
| 树莓派 5 | 4 核 | 4 GB | 16 GB |

### 1.2 软件要求

- Docker 20.10+ / Docker Compose 2.0+
- Python 3.11+（裸机部署）
- Git（克隆代码）
- Chrome/Chromium（仅当启用 g4f 浏览器类 provider 时需要）

## 2. 快速开始（Docker）

### 2.1 克隆项目

```bash
git clone https://github.com/yourusername/gemini-gateway.git
cd gemini-gateway
```

### 2.2 准备配置

```bash
# 创建目录
mkdir -p config cookies logs

# 从 docs/config-examples.md 中复制“基础配置 (config.yaml)”的 YAML 片段
# 粘贴到 config/config.yaml
nano config/config.yaml
```

### 2.3 配置 Cookie

```bash
# 创建 Cookie 文件
nano cookies/gemini.json
```

内容格式：
```json
{
  "__Secure-1PSID": "your-psid-here",
  "__Secure-1PSIDTS": "your-psidts-here",
  "updated_at": "2026-01-31T00:00:00"
}
```

### 2.4 启动服务

```bash
docker-compose up -d
```

### 2.5 g4f 浏览器依赖与 HAR/Cookies（可选）

当启用 g4f 的浏览器类 provider（需要网页自动化）时，建议：

- 镜像内安装 Chrome/Chromium
- 设置容器共享内存（`shm_size`）避免浏览器崩溃
- 挂载 `har_and_cookies/` 与 `generated_media/` 目录（持久化登录状态与媒体）
- 可选暴露 7900 端口用于手动登录获取 cookies/HAR

示例（节选）：
```yaml
services:
  gemini-gateway:
    shm_size: "2gb"
    ports:
      - "8022:8022"
      - "7900:7900"  # 可选：登录桌面
    volumes:
      - ./har_and_cookies:/app/har_and_cookies
      - ./generated_media:/app/generated_media
```

### 2.5 验证部署

```bash
# 查看日志
docker-compose logs -f

# 健康检查
curl http://localhost:8022/health

# 测试 API
curl http://localhost:8022/v1/models \
  -H "Authorization: Bearer your-token"

# Claude 格式模型列表
curl http://localhost:8022/v1/claude/models \
  -H "Authorization: Bearer your-token"
```

## 3. 树莓派 5 部署

### 3.1 安装 Docker

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加用户到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 安装 Docker Compose
sudo apt install docker-compose-plugin
```

### 3.2 优化配置

使用树莓派专用配置：

```bash
# 使用优化版 docker-compose
cp docker-compose.rpi.yml docker-compose.yml
```

### 3.3 限制资源

编辑 `docker-compose.yml`：

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '1.0'
```

### 3.4 启动

```bash
docker-compose up -d
```

### 3.5 性能监控

```bash
# 查看资源使用
docker stats gemini-gateway

# 查看日志
docker-compose logs -f --tail=100
```

## 4. 裸机部署

### 4.1 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4.2 配置

```bash
# 创建目录
mkdir -p config cookies logs

# 编辑配置
nano config/config.yaml
```

### 4.3 启动

```bash
python -m app.main
```

或使用 Gunicorn：

```bash
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8022
```

## 5. 配置热重载

### 5.1 自动热重载

配置文件修改后自动生效（无需重启）：

```bash
# 修改配置
nano config/config.yaml

# 保存后自动重载（约 1-2 秒生效）
```

### 5.2 手动触发重载

```bash
curl -X POST http://localhost:8022/admin/config/reload \
  -H "Authorization: Bearer your-token"
```

### 5.3 查看当前配置

当前文档未定义“配置查询”端点；如需查看配置，请直接查看挂载的 `config/config.yaml`。

## 6. 日志管理

### 6.1 查看日志

```bash
# Docker 方式
docker-compose logs -f

# 文件方式
tail -f logs/gateway.log
```

### 6.2 切换日志级别

```bash
# 切换到 DEBUG 模式
curl -X POST http://localhost:8022/admin/logging \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'

# 切换回 INFO
curl -X POST http://localhost:8022/admin/logging \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"level": "INFO"}'
```

### 6.3 日志轮转

日志自动轮转（由 Loguru 处理）：
- 单个文件最大 10 MB
- 保留 7 天的日志

## 7. Cookie 更新

### 7.1 通过 API 更新

```bash
curl -X POST http://localhost:8022/admin/cookies \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "__Secure-1PSID": "new-psid",
    "__Secure-1PSIDTS": "new-psidts"
  }'
```

### 7.2 直接修改文件

```bash
# 编辑 Cookie 文件
nano cookies/gemini.json

# 重载配置
curl -X POST http://localhost:8022/admin/config/reload \
  -H "Authorization: Bearer your-token"
```

### 7.3 查看 Cookie 状态

```bash
curl http://localhost:8022/admin/cookies/status \
  -H "Authorization: Bearer your-token"
```

## 8. 更新部署

### 8.1 更新代码

```bash
# 拉取最新代码
git pull origin main

# 重新构建
docker-compose down
docker-compose up -d --build
```

### 8.2 更新依赖

```bash
# 更新基础镜像
docker-compose pull
docker-compose up -d
```

## 9. 故障排查

### 9.1 服务无法启动

```bash
# 查看详细日志
docker-compose logs --no-color

# 检查配置语法
docker-compose config

# 验证 Cookie 文件
cat cookies/gemini.json | python3 -m json.tool
```

### 9.2 Cookie 过期

症状：返回 401 或 503 错误

解决：
```bash
# 1. 获取新 Cookie（浏览器开发者工具）
# 2. 更新 Cookie
curl -X POST http://localhost:8022/admin/cookies \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "__Secure-1PSID": "new-value",
    "__Secure-1PSIDTS": "new-value"
  }'
```

### 9.3 内存不足（树莓派）

症状：服务被杀掉（OOM）

解决：
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 256M  # 降低限制
```

### 9.4 网络问题

```bash
# 测试 Gemini 连通性
docker exec gemini-gateway curl -I https://gemini.google.com

# 查看网络配置
docker network ls
docker inspect gemini-gateway
```

## 10. 备份与恢复

### 10.1 备份

```bash
# 备份配置和 Cookie
tar czvf backup-$(date +%Y%m%d).tar.gz config/ cookies/

# 备份日志（可选）
tar czvf logs-$(date +%Y%m%d).tar.gz logs/
```

### 10.2 恢复

```bash
# 解压备份
tar xzvf backup-20260131.tar.gz

# 重启服务
docker-compose restart
```

## 11. 安全建议

### 11.1 网络安全

- 使用防火墙限制访问（仅允许特定 IP）
- 使用 HTTPS（通过 Nginx 反向代理）
- 定期更换 Bearer Token

### 11.2 Token 管理

```bash
# 生成安全 Token
openssl rand -hex 32

# 更新 Token
curl -X POST http://localhost:8022/admin/config/reload \
  -H "Authorization: Bearer old-token"
```

### 11.3 日志脱敏

确保日志中不记录：
- Bearer Token
- Cookie 值
- 敏感消息内容

## 12. 监控建议

### 12.1 基础监控

```bash
# 查看服务状态
docker-compose ps

# 查看资源使用
docker stats

# 查看日志错误
docker-compose logs | grep ERROR
```

### 12.2 健康检查

```bash
# 添加到 crontab
crontab -e

# 每 5 分钟检查一次
*/5 * * * * curl -f http://localhost:8022/health || docker-compose restart
```

---

*部署指南版本: 1.0*

## 13. 常见问题快速定位

更多排查步骤请参考 `docs/troubleshooting.md`。
