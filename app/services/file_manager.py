"""文件管理服务 - 管理 HAR 和 Cookie 文件"""
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
        
        # 确保目录存在（延迟创建，只在需要时）
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录存在，失败时不抛出异常"""
        try:
            self.cookies_dir.mkdir(parents=True, exist_ok=True)
            self.har_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # 在测试环境或只读环境中可能无法创建目录
            logger.warning(f"Cannot create directories at {self.base_dir}: {e}")
    
    async def save_har(self, file: UploadFile, provider: str | None = None) -> dict:
        """保存 HAR 文件
        
        Args:
            file: 上传的文件
            provider: 可选，如 'openai', 'google' 等，用于重命名文件
            
        Returns:
            保存的文件信息
        """
        if not file.filename or not file.filename.endswith('.har'):
            raise ValueError("Only .har files are allowed")
        
        # 如果有 provider 指定，重命名为 provider.har
        if provider:
            filename = f"{provider}.har"
        else:
            filename = file.filename
        
        filepath = self.har_dir / filename
        
        # 保存文件
        try:
            with open(filepath, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            size = filepath.stat().st_size
            logger.info(f"HAR file saved: {filepath} ({size} bytes)")
            
            return {
                "filename": filename,
                "path": str(filepath),
                "size": size
            }
        except Exception as e:
            logger.error(f"Failed to save HAR file: {e}")
            raise
    
    async def save_cookie(self, file: UploadFile, domain: str | None = None) -> dict:
        """保存 Cookie JSON 文件
        
        Args:
            file: 上传的文件
            domain: 可选，如 'kimi.com', 'qwen.com' 等，用于重命名文件
            
        Returns:
            保存的文件信息
        """
        if not file.filename or not file.filename.endswith('.json'):
            raise ValueError("Only .json files are allowed")
        
        # 如果有 domain 指定，重命名为 domain.json
        if domain:
            filename = f"{domain}.json"
        else:
            filename = file.filename
        
        filepath = self.cookies_dir / filename
        
        try:
            with open(filepath, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            size = filepath.stat().st_size
            logger.info(f"Cookie file saved: {filepath} ({size} bytes)")
            
            return {
                "filename": filename,
                "path": str(filepath),
                "size": size
            }
        except Exception as e:
            logger.error(f"Failed to save cookie file: {e}")
            raise
    
    def list_files(self) -> dict:
        """列出所有 HAR 和 Cookie 文件
        
        Returns:
            文件列表信息
        """
        har_files = sorted([f.name for f in self.har_dir.glob("*.har")])
        cookie_files = sorted([f.name for f in self.cookies_dir.glob("*.json")])
        
        return {
            "har_files": har_files,
            "cookie_files": cookie_files,
            "har_dir": str(self.har_dir),
            "cookies_dir": str(self.cookies_dir),
            "total_har": len(har_files),
            "total_cookies": len(cookie_files)
        }
    
    def delete_file(self, file_type: str, filename: str) -> bool:
        """删除文件
        
        Args:
            file_type: 'har' 或 'cookie'
            filename: 文件名
            
        Returns:
            是否成功删除
        """
        if file_type == "har":
            filepath = self.har_dir / filename
        elif file_type == "cookie":
            filepath = self.cookies_dir / filename
        else:
            logger.warning(f"Unknown file type: {file_type}")
            return False
        
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"File deleted: {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete file: {e}")
                return False
        else:
            logger.warning(f"File not found: {filepath}")
            return False
    
    def get_file_info(self, file_type: str, filename: str) -> dict | None:
        """获取文件信息
        
        Args:
            file_type: 'har' 或 'cookie'
            filename: 文件名
            
        Returns:
            文件信息或 None
        """
        if file_type == "har":
            filepath = self.har_dir / filename
        elif file_type == "cookie":
            filepath = self.cookies_dir / filename
        else:
            return None
        
        if filepath.exists():
            stat = filepath.stat()
            return {
                "filename": filename,
                "path": str(filepath),
                "size": stat.st_size,
                "modified": stat.st_mtime
            }
        return None
