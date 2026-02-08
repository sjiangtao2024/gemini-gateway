import base64
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.providers.g4f import G4FProvider
from app.providers.gemini import GeminiProvider
from app.services.stream import sse_chat_chunks

router = APIRouter()

_gemini: GeminiProvider | None = None
_g4f: G4FProvider | None = None
_gemini_models: list[str] = []


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageUrlContent(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: dict  # {"url": "data:image/png;base64,..."}


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[dict]  # list[TextContent | ImageUrlContent]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False


def configure(gemini: GeminiProvider | None, g4f: G4FProvider | None, gemini_models: list[str]) -> None:
    global _gemini, _g4f, _gemini_models
    _gemini = gemini
    _g4f = g4f
    _gemini_models = gemini_models


def _is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-")


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
                match = re.match(r"data:image/(\w+);base64,(.+)", image_url)
                if match:
                    ext, base64_data = match.groups()
                    image_bytes = base64.b64decode(base64_data)
                    
                    # 保存到临时文件
                    with NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                        f.write(image_bytes)
                        image_files.append(f.name)
    
    return "\n".join(text_parts), image_files


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


@router.get("/v1/models")
async def list_models():
    data = [
        {"id": model, "object": "model", "owned_by": "google"}
        for model in _gemini_models
    ]
    if _g4f is not None:
        try:
            data.extend(await _g4f.list_models())
        except Exception:
            pass
    return {"object": "list", "data": data}


@router.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest):
    model = payload.model
    stream = payload.stream
    
    if _is_gemini_model(model):
        if _gemini is None:
            raise HTTPException(status_code=503, detail="Gemini provider not configured")
        
        # 检查最后一条消息是否包含图片
        last_message = payload.messages[-1] if payload.messages else None
        has_image = (
            last_message and 
            isinstance(last_message.content, list) and
            any(item.get("type") == "image_url" for item in last_message.content)
        )
        
        if has_image:
            # Vision 请求
            text, image_files = _extract_image_from_content(last_message.content)
            
            # 构建历史消息（不含最后一条）
            prev_messages = [
                {"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)}
                for m in payload.messages[:-1]
            ]
            
            result = await _gemini.chat_completions_with_files(
                messages=prev_messages,
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
        
        return _create_openai_response(result.get("text", ""), model)
    
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


@router.post("/v1/images")
async def images(payload: dict):
    model = payload.get("model", "")
    prompt = payload.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt required")
    if not _is_gemini_model(model):
        raise HTTPException(status_code=501, detail="Image generation only supported for Gemini models")
    if _gemini is None:
        raise HTTPException(status_code=503, detail="Gemini provider not configured")
    images = await _gemini.generate_images(prompt=prompt, model=model)
    data: list[dict[str, Any]] = []
    for image in images:
        if isinstance(image, bytes):
            encoded = base64.b64encode(image).decode("utf-8")
        else:
            encoded = str(image)
        data.append({"b64_json": encoded})
    return {"created": 0, "data": data}
