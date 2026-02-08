"""错误处理和分类模块"""
from typing import Any
from fastapi import HTTPException


class AIGatewayError(Exception):
    """基础错误类"""
    def __init__(self, message: str, code: str, status_code: int = 500, details: dict | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "type": self.code.replace("_", " "),
                "code": self.code,
                **self.details
            }
        }


class AuthenticationError(AIGatewayError):
    """认证错误 (Cookie 过期、无效 Token)"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "authentication_error", 401)


class RateLimitError(AIGatewayError):
    """限流错误"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "rate_limit_exceeded", 429)


class ModelNotFoundError(AIGatewayError):
    """模型不存在"""
    def __init__(self, model: str):
        super().__init__(
            f"Model '{model}' not found",
            "model_not_found",
            404,
            {"model": model}
        )


class ProviderError(AIGatewayError):
    """Provider 服务错误"""
    def __init__(self, provider: str, message: str):
        super().__init__(
            f"{provider} error: {message}",
            "provider_error",
            503,
            {"provider": provider}
        )


class InvalidRequestError(AIGatewayError):
    """请求参数错误"""
    def __init__(self, message: str):
        super().__init__(message, "invalid_request_error", 422)


def http_exception_from_error(error: AIGatewayError) -> HTTPException:
    """将自定义错误转换为 FastAPI HTTPException"""
    return HTTPException(
        status_code=error.status_code,
        detail=error.to_dict()
    )


def classify_exception(exc: Exception, provider: str = "unknown") -> AIGatewayError:
    """分类异常为具体的错误类型"""
    error_msg = str(exc).lower()
    
    # 认证相关
    if any(k in error_msg for k in ["cookie", "auth", "unauthorized", "401"]):
        return AuthenticationError(str(exc))
    
    # 限流相关
    if any(k in error_msg for k in ["rate limit", "too many", "429"]):
        return RateLimitError(str(exc))
    
    # 超时/连接错误
    if any(k in error_msg for k in ["timeout", "connection", "refused"]):
        return ProviderError(provider, str(exc))
    
    # 默认 Provider 错误
    return ProviderError(provider, str(exc))
