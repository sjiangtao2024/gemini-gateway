"""文件管理服务 - 管理 HAR 和 Cookie 文件"""
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from fastapi import UploadFile
from app.services.logger import logger


class HARValidationResult:
    """HAR 文件验证结果"""
    def __init__(self, valid: bool, message: str, details: Dict[str, Any] = None):
        self.valid = valid
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "message": self.message,
            "details": self.details
        }


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
        """保存 HAR 文件（自动验证有效性）
        
        Args:
            file: 上传的文件
            provider: 可选，如 'openai', 'google' 等，用于重命名文件
            
        Returns:
            保存的文件信息和验证结果
        """
        if not file.filename or not file.filename.endswith('.har'):
            raise ValueError("Only .har files are allowed")
        
        # 如果有 provider 指定，重命名为 provider.har
        if provider:
            filename = f"{provider}.har"
        else:
            filename = file.filename
        
        filepath = self.har_dir / filename
        
        # 先保存到临时文件进行验证
        temp_filepath = filepath.with_suffix('.har.tmp')
        
        try:
            # 保存到临时文件
            with open(temp_filepath, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # 验证 HAR 文件
            validation = self.validate_har_file(temp_filepath)
            
            # 如果无效，删除临时文件并返回错误
            if not validation.valid:
                temp_filepath.unlink(missing_ok=True)
                logger.warning(f"HAR file validation failed: {validation.message}")
                raise ValueError(f"HAR validation failed: {validation.message}")
            
            # 验证通过，移动到正式位置
            if filepath.exists():
                filepath.unlink()  # 删除旧文件
            temp_filepath.rename(filepath)
            
            size = filepath.stat().st_size
            logger.info(f"HAR file saved and validated: {filepath} ({size} bytes). {validation.message}")
            
            return {
                "filename": filename,
                "path": str(filepath),
                "size": size,
                "validation": validation.to_dict()
            }
        except ValueError:
            # 验证错误，直接抛出
            if temp_filepath.exists():
                temp_filepath.unlink(missing_ok=True)
            raise
        except Exception as e:
            # 其他错误
            if temp_filepath.exists():
                temp_filepath.unlink(missing_ok=True)
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
    
    def validate_har_file(self, filepath: Path) -> HARValidationResult:
        """验证 HAR 文件的有效性
        
        检查内容：
        1. 是否为有效的 JSON
        2. 是否包含标准的 HAR 结构 (log.entries)
        3. 对于 ChatGPT HAR，检查是否包含授权信息
        
        Args:
            filepath: HAR 文件路径
            
        Returns:
            验证结果
        """
        try:
            with open(filepath, "rb") as f:
                har_data = json.load(f)
        except json.JSONDecodeError as e:
            return HARValidationResult(
                valid=False,
                message=f"Invalid JSON format: {e}",
                details={"error_type": "json_decode"}
            )
        except Exception as e:
            return HARValidationResult(
                valid=False,
                message=f"Failed to read file: {e}",
                details={"error_type": "read_error"}
            )
        
        # 检查 HAR 结构
        if "log" not in har_data:
            return HARValidationResult(
                valid=False,
                message="Invalid HAR format: missing 'log' key",
                details={"error_type": "missing_log"}
            )
        
        log = har_data.get("log", {})
        entries = log.get("entries", [])
        
        if not entries:
            return HARValidationResult(
                valid=False,
                message="HAR file contains no entries",
                details={"error_type": "no_entries", "version": log.get("version", "unknown")}
            )
        
        # 分析条目
        total_entries = len(entries)
        domains = set()
        has_auth = False
        auth_details = []
        chatgpt_entries = 0
        
        for entry in entries:
            request = entry.get("request", {})
            url = request.get("url", "")
            
            # 提取域名
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                if domain:
                    domains.add(domain)
            except:
                pass
            
            # 检查 ChatGPT 相关
            if "chatgpt.com" in url or "chat.openai.com" in url:
                chatgpt_entries += 1
                
                # 检查 headers
                headers = {h.get("name", "").lower(): h.get("value", "") 
                          for h in request.get("headers", [])}
                
                if "authorization" in headers:
                    has_auth = True
                    auth_details.append({
                        "url": url[:60],
                        "type": "header",
                        "domain": domain
                    })
                
                # 检查 cookies
                cookies = request.get("cookies", [])
                if cookies:
                    cookie_names = [c.get("name", "") for c in cookies]
                    # 检查是否有会话相关的 cookie
                    session_cookies = [c for c in cookie_names 
                                      if any(s in c.lower() for s in ["sess", "auth", "token", "login"])]
                    if session_cookies:
                        has_auth = True
                        auth_details.append({
                            "url": url[:60],
                            "type": "cookie",
                            "cookies": session_cookies[:5]  # 最多5个
                        })
        
        # 构建验证结果
        details = {
            "total_entries": total_entries,
            "domains": sorted(list(domains))[:10],  # 最多10个域名
            "chatgpt_entries": chatgpt_entries,
            "has_auth": has_auth,
            "auth_count": len(auth_details)
        }
        
        # 如果是 ChatGPT HAR 但没有认证信息
        if chatgpt_entries > 0 and not has_auth:
            return HARValidationResult(
                valid=False,
                message="ChatGPT HAR file detected but no authorization tokens found. "
                       "Please ensure you are logged into ChatGPT when exporting the HAR file.",
                details={**details, "auth_details": auth_details}
            )
        
        # 有效但可能有警告
        warnings = []
        if chatgpt_entries == 0:
            warnings.append("No ChatGPT entries found. This HAR may not work for OpenaiChat provider.")
        
        if has_auth:
            message = f"Valid HAR file with {len(auth_details)} authorization tokens found."
        else:
            message = "Valid HAR file structure."
        
        if warnings:
            message += " Warnings: " + "; ".join(warnings)
        
        return HARValidationResult(
            valid=True,
            message=message,
            details={**details, "auth_details": auth_details, "warnings": warnings}
        )
