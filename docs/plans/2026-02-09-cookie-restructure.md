# Cookie 目录重构 + HAR 上传实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 
1. 统一目录挂载结构（gemini + g4f 分离）
2. 添加 HAR 文件上传管理接口
3. 支持多 Provider Cookie 管理

---

## 任务1: 重构目录挂载

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docs/config-examples.md`

### Step 1: Update docker-compose.yml

```yaml
services:
  ai-gateway:
    build: .
    container_name: ai-gateway
    ports:
      - "8022:8022"
    environment:
      - PYTHONUNBUFFERED=1
      - CONFIG_PATH=/app/config/config.yaml
      - GEMINI_COOKIE_PATH=/app/data/gemini/cookies.json
    volumes:
      # 配置（只读）
      - ./config:/app/config:ro
      
      # Gemini 数据（读写 - 需要保存刷新后的 cookie）
      - ./data/gemini:/app/data/gemini
      
      # g4f 数据（只读 - g4f 服务内部管理）
      - ./data/g4f/cookies:/app/har_and_cookies/cookies:ro
      - ./data/g4f/har:/app/har_and_cookies/har:ro
      
      # 日志
      - ./logs:/app/logs
    command: >
      bash -lc "uv pip install -r /app/requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8022 --reload"
    restart: unless-stopped
```

### Step 2: Update docs/config-examples.md

添加目录结构说明：

```markdown
## 数据目录结构

```
data/
├── gemini/                 # Gemini Cookie
│   └── cookies.json       # 自动读取和保存
└── g4f/                   # g4f Cookies/HAR
    ├── cookies/           # Cookie JSON 文件
    │   ├── kimi.com.json
    │   ├── qwen.com.json
    │   └── glm.com.json
    └── har/               # HAR 抓包文件
        ├── chat.openai.com.har
        └── chat.google.com.har
```

**注意**: 
- gemini 目录需要可写（自动刷新保存）
- g4f 目录只读即可（g4f 服务内部管理）
```

### Step 3: Commit

```bash
git add docker-compose.yml docs/config-examples.md
git commit -m "refactor(docker): restructure data directories

- Unified data directory structure
- Separate gemini (RW) and g4f (RO) directories
- Add GEMINI_COOKIE_PATH environment variable"
```

---

## 任务2: 添加 HAR 文件上传接口

**Files:**
- Modify: `app/routes/admin.py`
- Create: `app/services/file_manager.py`

### Step 1: Create file_manager.py

```python
"""文件管理服务"""
import shutil
from pathlib import Path
from typing import List
from fastapi import UploadFile
from app.services.logger import logger


class FileManager:
    """管理 HAR 和 Cookie 文件"""
    
    def __init__(self, base_dir: str = "/app/har_and_cookies"):
        self.base_dir = Path(base_dir)
        self.cookies_dir = self.base_dir / "cookies"
        self.har_dir = self.base_dir / "har"
        
        # 确保目录存在
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self.har_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_har(self, file: UploadFile, provider: str | None = None) -> dict:
        """保存 HAR 文件"""
        if not file.filename or not file.filename.endswith('.har'):
            raise ValueError("Only .har files are allowed")
        
        # 如果有 provider 指定，重命名为 provider.har
        if provider:
            filename = f"{provider}.har"
        else:
            filename = file.filename
        
        filepath = self.har_dir / filename
        
        # 保存文件
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logger.info(f"HAR file saved: {filepath}")
        
        return {
            "filename": filename,
            "path": str(filepath),
            "size": filepath.stat().st_size
        }
    
    async def save_cookie(self, file: UploadFile, domain: str | None = None) -> dict:
        """保存 Cookie JSON 文件"""
        if not file.filename or not file.filename.endswith('.json'):
            raise ValueError("Only .json files are allowed")
        
        # 如果有 domain 指定，重命名为 domain.json
        if domain:
            filename = f"{domain}.json"
        else:
            filename = file.filename
        
        filepath = self.cookies_dir / filename
        
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logger.info(f"Cookie file saved: {filepath}")
        
        return {
            "filename": filename,
            "path": str(filepath),
            "size": filepath.stat().st_size
        }
    
    def list_files(self) -> dict:
        """列出所有文件"""
        har_files = [f.name for f in self.har_dir.glob("*.har")]
        cookie_files = [f.name for f in self.cookies_dir.glob("*.json")]
        
        return {
            "har_files": har_files,
            "cookie_files": cookie_files,
            "har_dir": str(self.har_dir),
            "cookies_dir": str(self.cookies_dir)
        }
    
    def delete_file(self, file_type: str, filename: str) -> bool:
        """删除文件"""
        if file_type == "har":
            filepath = self.har_dir / filename
        elif file_type == "cookie":
            filepath = self.cookies_dir / filename
        else:
            return False
        
        if filepath.exists():
            filepath.unlink()
            logger.info(f"File deleted: {filepath}")
            return True
        return False
```

### Step 2: Update admin.py

添加 HAR 和 Cookie 文件管理接口：

```python
from fastapi import UploadFile, File, Form
from app.services.file_manager import FileManager

# 初始化文件管理器
_file_manager: FileManager | None = None

def configure_file_manager(manager: FileManager | None):
    global _file_manager
    _file_manager = manager

# 在 admin configure 中调用
# configure_file_manager(FileManager())

@router.post("/admin/files/har")
async def upload_har(
    file: UploadFile = File(...),
    provider: str | None = Form(None)
):
    """上传 HAR 文件
    
    provider: 可选，如 'openai', 'google' 等，用于命名文件
    """
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    try:
        result = await _file_manager.save_har(file, provider)
        return {
            "status": "success",
            "message": "HAR file uploaded",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save HAR: {e}")

@router.post("/admin/files/cookie")
async def upload_cookie(
    file: UploadFile = File(...),
    domain: str | None = Form(None)
):
    """上传 Cookie JSON 文件
    
    domain: 可选，如 'kimi.com', 'qwen.com' 等，用于命名文件
    """
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    try:
        result = await _file_manager.save_cookie(file, domain)
        return {
            "status": "success",
            "message": "Cookie file uploaded",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookie: {e}")

@router.get("/admin/files")
async def list_files():
    """列出所有 HAR 和 Cookie 文件"""
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    return _file_manager.list_files()

@router.delete("/admin/files/{file_type}/{filename}")
async def delete_file(file_type: str, filename: str):
    """删除文件
    
    file_type: 'har' 或 'cookie'
    """
    if _file_manager is None:
        raise HTTPException(status_code=503, detail="File manager not configured")
    
    if file_type not in ["har", "cookie"]:
        raise HTTPException(status_code=400, detail="file_type must be 'har' or 'cookie'")
    
    success = _file_manager.delete_file(file_type, filename)
    if success:
        return {"status": "success", "message": f"{filename} deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")
```

### Step 3: Update main.py

```python
from app.services.file_manager import FileManager
from app.routes.admin import configure_file_manager

# 在应用启动时初始化
configure_file_manager(FileManager())
```

### Step 4: Commit

```bash
git add app/services/file_manager.py app/routes/admin.py app/main.py
git commit -m "feat(admin): add HAR and cookie file upload management

- POST /admin/files/har - upload HAR files
- POST /admin/files/cookie - upload cookie JSON files
- GET /admin/files - list all files
- DELETE /admin/files/{type}/{name} - delete files"
```

---

## 任务3: 更新文档

### 添加 API 文档

```markdown
## 文件管理接口

### 上传 HAR 文件
```bash
curl -X POST http://localhost:8022/admin/files/har \
  -H "Authorization: Bearer token" \
  -F "file=@chat.openai.com.har" \
  -F "provider=openai"
```

### 上传 Cookie 文件
```bash
curl -X POST http://localhost:8022/admin/files/cookie \
  -H "Authorization: Bearer token" \
  -F "file=@kimi.com.json" \
  -F "domain=kimi.com"
```

### 列出文件
```bash
curl http://localhost:8022/admin/files \
  -H "Authorization: Bearer token"
```

### 删除文件
```bash
curl -X DELETE http://localhost:8022/admin/files/har/openai.har \
  -H "Authorization: Bearer token"
```
```

### 添加 g4f Provider Cookie 说明

```markdown
## g4f Provider Cookie 管理

g4f 支持多种 Provider，不同 Provider 需要不同的认证方式：

### Cookie 文件格式

文件名格式: `{domain}.json`

```json
{
  "session_token": "xxx",
  "cf_clearance": "xxx"
}
```

### HAR 文件格式

文件名格式: `{provider}.har` 或 `{domain}.har`

从浏览器开发者工具 Network 标签导出。

### Provider 对应文件

| Provider | 需要文件 | 文件名示例 |
|---------|---------|-----------|
| ChatGPT | HAR | `openai.com.har` 或 `chat.openai.com.har` |
| Kimi | Cookie | `kimi.com.json` 或 `kimi.moonshot.cn.json` |
| Qwen | Cookie | `qwen.com.json` 或 `tongyi.aliyun.com.json` |
| GLM | Cookie | `chatglm.cn.json` |
| Minimax | Cookie | `minimax.chat.json` |

**注意**: g4f 会自动在 `/app/har_and_cookies/` 目录查找匹配的文件。
```

---

## 验证清单

```bash
# 1. 检查目录结构
ls -la data/

# 2. 测试上传 HAR
curl -X POST http://localhost:8022/admin/files/har \
  -H "Authorization: Bearer xxx" \
  -F "file=@test.har" \
  -F "provider=test"

# 3. 测试列出文件
curl http://localhost:8022/admin/files \
  -H "Authorization: Bearer xxx"

# 4. 运行测试
pytest tests/ -v
```
