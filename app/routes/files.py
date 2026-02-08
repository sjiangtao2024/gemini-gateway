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
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": len(result.get("text", "")) // 4,
                "total_tokens": len(result.get("text", "")) // 4
            }
        }
    finally:
        # 清理临时文件
        for fp in file_paths:
            try:
                Path(fp).unlink()
            except:
                pass
