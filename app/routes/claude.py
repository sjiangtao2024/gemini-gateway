from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
import uuid

from app.providers.gemini import GeminiProvider
from app.providers.g4f import G4FProvider

router = APIRouter()

_gemini_models: list[str] = []
_g4f_models: list[str] = []
_gemini: GeminiProvider | None = None
_g4f: G4FProvider | None = None


class ClaudeMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ClaudeRequest(BaseModel):
    model: str
    messages: list[ClaudeMessage]
    system: str | None = None
    max_tokens: int | None = None
    stream: bool = False


class ClaudeContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ClaudeUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ClaudeResponse(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    model: str
    content: list[ClaudeContent]
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence"] = "end_turn"
    usage: ClaudeUsage


def configure(
    gemini_models: list[str],
    g4f_models: list[str],
    gemini: GeminiProvider | None = None,
    g4f: G4FProvider | None = None
) -> None:
    global _gemini_models, _g4f_models, _gemini, _g4f
    _gemini_models = gemini_models
    _g4f_models = g4f_models
    _gemini = gemini
    _g4f = g4f


def _is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-")


def _claude_to_openai_messages(claude_req: ClaudeRequest) -> list[dict]:
    """将 Claude 请求转换为 OpenAI 格式"""
    messages = []
    
    # 处理 system prompt
    if claude_req.system:
        messages.append({"role": "system", "content": claude_req.system})
    
    # 转换 messages
    for msg in claude_req.messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    return messages


def _openai_to_claude_response(openai_result: dict, model: str) -> ClaudeResponse:
    """将 OpenAI 格式结果转换为 Claude 格式"""
    # 提取文本内容
    text = ""
    if "text" in openai_result:
        text = openai_result["text"]
    elif "choices" in openai_result and openai_result["choices"]:
        text = openai_result["choices"][0].get("message", {}).get("content", "")
    
    # 估算 token 数 (简化处理)
    input_tokens = len(str(openai_result.get("messages", []))) // 4
    output_tokens = len(text) // 4
    
    return ClaudeResponse(
        id=f"msg_{uuid.uuid4().hex[:24]}",
        model=model,
        content=[ClaudeContent(text=text)],
        usage=ClaudeUsage(input_tokens=input_tokens, output_tokens=output_tokens)
    )


@router.get("/v1/claude/models")
async def list_models():
    models = _gemini_models + _g4f_models
    return {"data": [{"type": "model", "id": m, "display_name": m} for m in models]}


@router.post("/v1/messages")
async def messages(payload: ClaudeRequest):
    """Claude 协议消息完成 - 支持 Gemini 和 g4f"""
    model = payload.model
    
    if _is_gemini_model(model):
        if _gemini is None:
            raise HTTPException(status_code=503, detail="Gemini provider not configured")
        
        # 转换为 OpenAI 格式并调用
        openai_messages = _claude_to_openai_messages(payload)
        result = await _gemini.chat_completions(
            messages=openai_messages,
            model=model
        )
        
        return _openai_to_claude_response(result, model)
    
    # g4f 模型
    if _g4f is None:
        raise HTTPException(status_code=503, detail="g4f provider not configured")
    
    # g4f 可以直接接受 OpenAI 格式
    openai_payload = {
        "model": model,
        "messages": _claude_to_openai_messages(payload)
    }
    result = await _g4f.chat_completions(openai_payload)
    
    return _openai_to_claude_response(result, model)
