"""请求日志中间件"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.logger import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录请求信息的中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求开始
        client_host = request.client.host if request.client else "unknown"
        logger.debug(f"Request started: {request.method} {request.url.path} from {client_host}")
        
        try:
            response = await call_next(request)
            
            # 计算耗时
            process_time = time.time() - start_time
            
            # 记录请求完成
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
            )
            
            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} - ERROR - {process_time:.3f}s - {str(e)}"
            )
            raise
