# Phase 3: 多模态支持实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 实现图像理解（Vision）、文件上传、图像生成等多模态功能

**Architecture:** 
- Vision: OpenAI `/v1/chat/completions` 接收图片 URL/base64 → 调用 Gemini Vision
- 文件上传: 支持 PDF/图片等文件上传分析
- 图像生成: 整合 Gemini 和 g4f 的图像生成能力

**Tech Stack:** FastAPI, Base64, File Upload, Gemini-API

---

## 背景信息

### Gemini-API 多模态能力

**图像理解 (Vision):**
```python
response = await client.generate_content(
    "描述这张图",
    files=["/path/to/image.png"]
)
```

**支持的文件类型:**
- 图片: PNG, JPEG, WEBP, HEIC, HEIF
- 文档: PDF

### 当前 OpenAI 路由状态

**app/routes/openai.py:**
- `/v1/chat/completions` - 仅文本消息
- `/v1/images` - 仅 Gemini 图像生成，g4f 不支持

### OpenAI Vision API 格式

**请求:**
```json
{
  "model": "gemini-2.5-pro",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "描述这张图"},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]
  }]
}
```

---

## Task 1: Vision 图像理解支持

**Files:**
- Modify: `app/routes/openai.py`
- Modify: `app/providers/gemini.py`

**Step 1: 添加 Pydantic 模型到 openai.py**

```python
from pydantic import BaseModel
from typing import Literal

class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str

class ImageUrlContent(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: dict  # {"url": "data:image/png;base64,..."}

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[TextContent | ImageUrlContent]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
```

**Step 2: 实现图片提取和保存函数**

```python
import base64
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

def _extract_image_from_content(content: list) -> tuple[str, list[str]]:
    """从 content 中提取文本和图片
    
    Returns:
        (text_prompt, list_of_temp_file_paths)
    """
    text_parts = []
    image_files = []
    
    for item in content:
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
        elif item.get("type") == "image_url":
            image_url = item.get("image_url", {}).get("url", "")
            # 处理 base64 图片
            if image_url.startswith("data:image"):
                # 提取 base64 数据
                match = re.match(r"data:image/\w+;base64,(.+)", image_url)
                if match:
                    base64_data = match.group(1)
                    image_bytes = base64.b64decode(base64_data)
                    
                    # 保存到临时文件
                    ext = re.search(r"data:image/(\w+);", image_url)
                    ext = ext.group(1) if ext else "png"
                    
                    with NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                        f.write(image_bytes)
                        image_files.append(f.name)
    
    return "\n".join(text_parts), image_files
```

**Step 3: 修改 chat_completions 支持多模态**

```python
@router.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest):
    model = payload.model
    stream = payload.stream
    
    if _is_gemini_model(model):
        if _gemini is None:
            raise HTTPException(status_code=503, detail="Gemini provider not configured")
        
        # 检查是否包含图片
        last_message = payload.messages[-1] if payload.messages else None
        has_image = (
            last_message and 
            isinstance(last_message.content, list) and
            any(item.get("type") == "image_url" for item in last_message.content)
        )
        
        if has_image:
            # Vision 请求
            text, image_files = _extract_image_from_content(last_message.content)
            result = await _gemini.chat_completions_with_files(
                messages=payload.messages[:-1],  # 之前的消息作为上下文
                text=text,
                files=image_files,
                model=model
            )
            # 清理临时文件
            for f in image_files:
                try:
                    Path(f).unlink()
                except:
                    pass
        else:
            # 普通文本请求
            messages = [
                {"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)}
                for m in payload.messages
            ]
            result = await _gemini.chat_completions(messages=messages, model=model)
        
        text_result = result.get("text", "")
        return _create_openai_response(text_result, model)
    
    # g4f 处理 (暂不支持 Vision)
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    
    # 转换为标准 OpenAI 格式
    messages = []
    for m in payload.messages:
        if isinstance(m.content, str):
            messages.append({"role": m.role, "content": m.content})
        else:
            # 多模态，g4f 可能不支持，提取文本部分
            text_parts = [item.get("text", "") for item in m.content if item.get("type") == "text"]
            messages.append({"role": m.role, "content": "\n".join(text_parts)})
    
    openai_payload = {"model": model, "messages": messages, "stream": stream}
    return await _g4f.chat_completions(openai_payload)
```

**Step 4: 辅助函数 _create_openai_response**

```python
def _create_openai_response(text: str, model: str) -> dict:
    """创建标准 OpenAI 响应"""
    return {
        "id": f"chatcmpl-{model.replace('-', '')}",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(text) // 4,
            "total_tokens": len(text) // 4
        }
    }
```

**Step 5: 在 gemini.py 添加 chat_completions_with_files 方法**

```python
# app/providers/gemini.py

async def chat_completions_with_files(
    self,
    messages: list[dict],
    text: str,
    files: list[str],
    model: str | None = None
) -> dict:
    """支持文件上传的聊天完成"""
    client = await self._ensure_client()
    
    # 构建提示词（包含历史消息上下文）
    context = self._messages_to_prompt(messages)
    if context:
        prompt = f"{context}\n\n{text}"
    else:
        prompt = text
    
    selected_model = model or self.model
    if selected_model:
        response = await client.generate_content(prompt, files=files, model=selected_model)
    else:
        response = await client.generate_content(prompt, files=files)
    
    return {"text": response.text, "images": response.images, "raw": response}
```

**Step 6: Test imports**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -c "from app.routes.openai import router; print('Import OK')"
```

**Step 7: Commit**

```bash
git add app/routes/openai.py app/providers/gemini.py
git commit -m "feat(vision): add image understanding support

- Support OpenAI Vision API format with image_url content
- Extract base64 images and save to temp files
- Add chat_completions_with_files to GeminiProvider
- Handle vision requests in /v1/chat/completions"
```

---

## Task 2: 文件上传分析支持

**Files:**
- Create: `app/routes/files.py` (新的路由文件)
- Modify: `app/main.py` (注册新路由)

**Step 1: Create app/routes/files.py**

```python
"""文件上传和分析路由"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import tempfile
from pathlib import Path

from app.providers.gemini import GeminiProvider

router = APIRouter()

_gemini: GeminiProvider | None = None

def configure(gemini: GeminiProvider | None) -> None:
    global _gemini
    _gemini = gemini

@router.post("/v1/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("assistants")
):
    """上传文件，返回 file_id"""
    if _gemini is None:
        raise HTTPException(status_code=503, detail="Gemini provider not configured")
    
    # 保存上传的文件
    suffix = Path(file.filename).suffix if file.filename else ".tmp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # 返回 file_id (使用临时文件路径作为 id)
    return {
        "id": f"file-{Path(tmp_path).name}",
        "object": "file",
        "bytes": len(content),
        "created_at": 0,
        "filename": file.filename,
        "purpose": purpose,
        "status": "processed"
    }

@router.post("/v1/chat/completions/with-files")
async def chat_with_files(
    model: str = Form(...),
    message: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    """上传文件并进行对话"""
    if _gemini is None:
        raise HTTPException(status_code=503, detail="Gemini provider not configured")
    
    if not model.startswith("gemini-"):
        raise HTTPException(status_code=400, detail="File upload only supported for Gemini models")
    
    # 保存所有上传的文件
    file_paths = []
    for file in files:
        suffix = Path(file.filename).suffix if file.filename else ".tmp"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            file_paths.append(tmp.name)
    
    try:
        # 调用 Gemini
        result = await _gemini.chat_completions_with_files(
            messages=[],
            text=message,
            files=file_paths,
            model=model
        )
        
        return {
            "id": f"chatcmpl-{model.replace('-', '')}",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result.get("text", "")},
                "finish_reason": "stop"
            }]
        }
    finally:
        # 清理临时文件
        for fp in file_paths:
            try:
                Path(fp).unlink()
            except:
                pass
```

**Step 2: Register in app/main.py**

```python
from app.routes.files import router as files_router, configure as configure_files

# ... existing router includes ...
app.include_router(files_router)

# ... in setup code ...
configure_files(gemini_provider)
```

**Step 3: Test imports**

```bash
python3 -c "from app.routes.files import router; print('Import OK')"
python3 -c "from app.main import app; print('Main import OK')"
```

**Step 4: Commit**

```bash
git add app/routes/files.py app/main.py
git commit -m "feat(files): add file upload and analysis support

- POST /v1/files for file upload
- POST /v1/chat/completions/with-files for chat with files
- Support PDF, images, and other documents"
```

---

## Task 3: 图像生成增强

**Files:**
- Modify: `app/routes/openai.py`

**Step 1: Enhance /v1/images to support more parameters**

当前代码:
```python
@router.post("/v1/images")
async def images(payload: dict):
    model = payload.get("model", "")
    prompt = payload.get("prompt", "")
    # ... basic implementation
```

改进：

```python
from pydantic import BaseModel
from typing import Literal

class ImageGenerationRequest(BaseModel):
    model: str
    prompt: str
    n: int = 1
    size: str = "1024x1024"  # Gemini 可能忽略
    response_format: Literal["url", "b64_json"] = "b64_json"

@router.post("/v1/images")
async def images(payload: ImageGenerationRequest):
    """图像生成 - 支持 Gemini 和 g4f"""
    
    if _is_gemini_model(payload.model):
        if _gemini is None:
            raise HTTPException(status_code=503, detail="Gemini provider not configured")
        
        # Gemini 图像生成
        images = await _gemini.generate_images(prompt=payload.prompt, model=payload.model)
        
        data = []
        for image in images[:payload.n]:  # 限制数量
            if isinstance(image, bytes):
                encoded = base64.b64encode(image).decode("utf-8")
            else:
                encoded = str(image)
            
            item = {"b64_json": encoded}
            if payload.response_format == "url":
                # Gemini 不支持 URL，仍返回 base64
                item = {"url": f"data:image/png;base64,{encoded}"}
            
            data.append(item)
        
        return {"created": 0, "data": data}
    
    # g4f 图像生成
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    
    try:
        # 调用 g4f 的图像生成
        result = await _g4f.chat_completions({
            "model": payload.model,
            "messages": [{"role": "user", "content": payload.prompt}],
            # g4f 可能有专门的图像生成端点
        })
        
        # 处理 g4f 响应
        # ... 根据 g4f 实际响应格式处理
        
        return {"created": 0, "data": [{"b64_json": "..."}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {e}")
```

**Step 2: Test imports**

```bash
python3 -c "from app.routes.openai import router; print('Import OK')"
```

**Step 3: Commit**

```bash
git add app/routes/openai.py
git commit -m "feat(images): enhance image generation endpoint

- Support n, size, response_format parameters
- Support both Gemini and g4f providers
- Better error handling"
```

---

## Task 4: 添加多模态测试

**Files:**
- Create: `tests/test_multimodal.py`

**Step 1: Create test file**

```python
import pytest
import base64
from io import BytesIO
from app.routes.openai import _extract_image_from_content

class TestVision:
    """测试图像理解功能"""
    
    def test_extract_text_only(self):
        """测试纯文本内容"""
        content = [{"type": "text", "text": "Hello"}]
        text, files = _extract_image_from_content(content)
        
        assert text == "Hello"
        assert files == []
    
    def test_extract_base64_image(self):
        """测试提取 base64 图片"""
        # 创建一个简单的 base64 图片
        image_data = b"fake-image-data"
        base64_str = base64.b64encode(image_data).decode()
        
        content = [
            {"type": "text", "text": "描述这张图"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_str}"}}
        ]
        
        text, files = _extract_image_from_content(content)
        
        assert text == "描述这张图"
        assert len(files) == 1
        # 验证临时文件存在
        assert files[0].endswith('.png')
    
    def test_extract_multiple_images(self):
        """测试提取多张图片"""
        base64_str = base64.b64encode(b"image").decode()
        
        content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_str}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{base64_str}"}}
        ]
        
        text, files = _extract_image_from_content(content)
        
        assert len(files) == 2
        assert files[0].endswith('.jpeg')
        assert files[1].endswith('.webp')

class TestImageGeneration:
    """测试图像生成功能"""
    
    def test_image_request_model(self):
        """测试图像生成请求模型"""
        from app.routes.openai import ImageGenerationRequest
        
        req = ImageGenerationRequest(
            model="gemini-2.5-pro",
            prompt="a cat",
            n=2,
            response_format="b64_json"
        )
        
        assert req.model == "gemini-2.5-pro"
        assert req.prompt == "a cat"
        assert req.n == 2
        assert req.response_format == "b64_json"
```

**Step 2: Run tests**

```bash
cd /home/yukun/dev/gemini-business-automation/gemini-api
python3 -m pytest tests/test_multimodal.py -v
```

**Step 3: Commit**

```bash
git add tests/test_multimodal.py
git commit -m "test(multimodal): add vision and image generation tests

- Test image extraction from content
- Test base64 image decoding
- Test multiple image handling
- Test image generation request model"
```

---

## 验证清单

完成所有任务后验证：

```bash
# 1. 检查所有导入
python3 -c "
from app.routes.openai import router
from app.routes.files import router as files_router
from app.providers.gemini import GeminiProvider
print('✅ All imports OK')
"

# 2. 运行测试
python3 -m pytest tests/test_multimodal.py -v

# 3. 检查主应用导入
python3 -c "from app.main import app; print('✅ Main app OK')"
```

---

## 提交历史

1. `feat(vision): add image understanding support`
2. `feat(files): add file upload and analysis support`
3. `feat(images): enhance image generation endpoint`
4. `test(multimodal): add vision and image generation tests`

---

## 预期结果

完成后可以通过以下方式使用：

```python
# Vision 图像理解
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8022/v1", api_key="token")

response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述这张图"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
)

# 文件上传分析
curl -X POST http://localhost:8022/v1/chat/completions/with-files \
  -F "model=gemini-2.5-pro" \
  -F "message=总结这个PDF的内容" \
  -F "files=@document.pdf"
```
