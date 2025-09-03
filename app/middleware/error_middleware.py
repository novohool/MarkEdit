"""
错误处理中间件

提供全局错误捕获和处理功能
"""
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.error_handler import (
    error_handler, ErrorCategory, ErrorLevel, 
    create_recovery_suggestions
)

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("app.middleware.error")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并捕获异常"""
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            return await self._handle_exception(request, e)
    
    async def _handle_exception(self, request: Request, exception: Exception) -> Response:
        """处理异常并返回适当的响应"""
        try:
            # 获取用户信息
            user_id = await self._get_user_id_from_request(request)
            
            # 创建错误上下文
            context = error_handler.create_error_context(request, user_id)
            
            # 根据异常类型确定错误分类
            category = self._determine_error_category(exception, request)
            
            # 创建恢复建议
            recovery_suggestions = create_recovery_suggestions(category)
            
            # 处理异常
            error_info = error_handler.handle_exception(
                exception, 
                context, 
                category,
                recovery_suggestions=recovery_suggestions
            )
            
            # 根据请求类型返回不同格式的响应
            if self._is_api_request(request):
                return error_handler.create_json_response(error_info)
            else:
                return error_handler.create_html_response(error_info, request)
                
        except Exception as middleware_error:
            # 中间件本身出错时的降级处理
            self.logger.critical(f"错误处理中间件失败: {str(middleware_error)}", exc_info=True)
            return await self._create_fallback_response(request, exception)
    
    async def _get_user_id_from_request(self, request: Request) -> str:
        """从请求中获取用户ID"""
        try:
            # 尝试从会话中获取用户信息
            from app.common import get_session_service
            session_service = get_session_service()
            session = session_service.get_session(request)
            return session.username if session else None
        except Exception:
            return None
    
    def _determine_error_category(self, exception: Exception, request: Request) -> ErrorCategory:
        """根据异常和请求确定错误分类"""
        # 根据请求路径确定分类
        path = request.url.path
        
        # EPUB查看器页面不需要认证，将其归类为业务逻辑错误而不是权限错误
        if path == "/epub-viewer.html":
            return ErrorCategory.BUSINESS_LOGIC
        
        if "/api/admin" in path or "/admin" in path:
            if "permission" in str(exception).lower() or "权限" in str(exception):
                return ErrorCategory.AUTHORIZATION
            elif "login" in path or "auth" in path:
                return ErrorCategory.AUTHENTICATION
        
        if "/api/user" in path:
            if "theme" in path or "profile" in path:
                return ErrorCategory.BUSINESS_LOGIC
        
        if "/api/file" in path or "file" in str(exception).lower():
            return ErrorCategory.FILE_SYSTEM
        
        # 根据异常类型确定分类
        if isinstance(exception, PermissionError):
            return ErrorCategory.AUTHORIZATION
        elif isinstance(exception, (FileNotFoundError, FileExistsError)):
            return ErrorCategory.FILE_SYSTEM
        elif isinstance(exception, (ValueError, TypeError)):
            return ErrorCategory.VALIDATION
        elif "database" in str(exception).lower() or "sql" in str(exception).lower():
            return ErrorCategory.DATABASE
        elif "network" in str(exception).lower() or "connection" in str(exception).lower():
            return ErrorCategory.NETWORK
        
        return ErrorCategory.UNKNOWN
    
    def _is_api_request(self, request: Request) -> bool:
        """判断是否为API请求"""
        # 检查路径
        if request.url.path.startswith("/api/"):
            return True
        
        # 检查Accept头
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            return True
        
        # 检查Content-Type头
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            return True
        
        return False
    
    async def _create_fallback_response(self, request: Request, original_exception: Exception) -> Response:
        """创建降级响应（当错误处理器本身失败时）"""
        error_id = "fallback-error"
        
        if self._is_api_request(request):
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error_id": error_id,
                    "message": "系统内部错误，请稍后重试",
                    "recovery_suggestions": [
                        "请稍后重试",
                        "如果问题持续存在，请联系管理员",
                        f"错误ID: {error_id}"
                    ]
                }
            )
        else:
            return HTMLResponse(
                content=f"""
                <html>
                <head><title>系统错误</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1>系统错误</h1>
                    <p>系统遇到了内部错误，请稍后重试。</p>
                    <p>错误ID: {error_id}</p>
                    <p><a href="/">返回首页</a> | <a href="javascript:history.back()">返回上一页</a></p>
                </body>
                </html>
                """,
                status_code=500
            )

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("app.middleware.request")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """记录请求和响应信息"""
        import time
        
        start_time = time.time()
        
        # 记录请求信息
        self.logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            self.logger.info(
                f"Response: {response.status_code} "
                f"in {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # 记录异常信息
            process_time = time.time() - start_time
            self.logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"after {process_time:.3f}s - {str(e)}"
            )
            raise

def setup_error_middleware(app):
    """设置错误处理中间件"""
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)