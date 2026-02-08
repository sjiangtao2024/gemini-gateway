"""错误处理测试"""
import pytest
from app.utils.errors import (
    AIGatewayError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ProviderError,
    InvalidRequestError,
    classify_exception,
    http_exception_from_error
)


class TestErrors:
    """测试错误类"""
    
    def test_base_error(self):
        """测试基础错误类"""
        err = AIGatewayError("test message", "test_code", 400, {"detail": "info"})
        
        assert err.message == "test message"
        assert err.code == "test_code"
        assert err.status_code == 400
        assert err.details == {"detail": "info"}
    
    def test_error_to_dict(self):
        """测试错误转字典"""
        err = AuthenticationError("Invalid token")
        result = err.to_dict()
        
        assert result["error"]["message"] == "Invalid token"
        assert result["error"]["code"] == "authentication_error"
        assert result["error"]["type"] == "authentication error"
    
    def test_authentication_error_defaults(self):
        """测试认证错误默认值"""
        err = AuthenticationError()
        
        assert err.status_code == 401
        assert err.code == "authentication_error"
        assert "Authentication failed" in err.message
    
    def test_rate_limit_error(self):
        """测试限流错误"""
        err = RateLimitError()
        
        assert err.status_code == 429
        assert err.code == "rate_limit_exceeded"
    
    def test_model_not_found_error(self):
        """测试模型不存在错误"""
        err = ModelNotFoundError("gemini-99")
        
        assert err.status_code == 404
        assert "gemini-99" in err.message
        assert err.details["model"] == "gemini-99"
    
    def test_provider_error(self):
        """测试 Provider 错误"""
        err = ProviderError("gemini", "Connection timeout")
        
        assert err.status_code == 503
        assert "gemini" in err.message
        assert err.details["provider"] == "gemini"
    
    def test_invalid_request_error(self):
        """测试请求错误"""
        err = InvalidRequestError("Missing required field")
        
        assert err.status_code == 422
        assert err.code == "invalid_request_error"


class TestExceptionClassification:
    """测试异常分类"""
    
    def test_classify_auth_error(self):
        """测试分类认证错误"""
        exc = Exception("Cookie expired")
        err = classify_exception(exc)
        
        assert isinstance(err, AuthenticationError)
    
    def test_classify_rate_limit(self):
        """测试分类限流错误"""
        exc = Exception("Rate limit exceeded")
        err = classify_exception(exc)
        
        assert isinstance(err, RateLimitError)
    
    def test_classify_timeout(self):
        """测试分类超时错误"""
        exc = Exception("Connection timeout")
        err = classify_exception(exc, "gemini")
        
        assert isinstance(err, ProviderError)
        assert err.details["provider"] == "gemini"
    
    def test_classify_generic(self):
        """测试分类通用错误"""
        exc = Exception("Something went wrong")
        err = classify_exception(exc, "test")
        
        assert isinstance(err, ProviderError)


class TestHTTPException:
    """测试 HTTP 异常转换"""
    
    def test_http_exception_from_error(self):
        """测试转换为 FastAPI HTTPException"""
        err = AuthenticationError("Invalid token")
        http_exc = http_exception_from_error(err)
        
        from fastapi import HTTPException
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 401
        assert "error" in http_exc.detail
