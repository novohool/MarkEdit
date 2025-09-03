"""
统一错误处理工具模块

提供统一的错误处理、日志记录和用户反馈机制
"""
import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union, List
from enum import Enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

# 设置模板目录
templates = Jinja2Templates(directory="templates")

class ErrorLevel(Enum):
    """错误级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """错误分类枚举"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"

class ErrorContext:
    """错误上下文信息"""
    
    def __init__(self, 
                 error_id: str = None,
                 user_id: str = None,
                 request_path: str = None,
                 request_method: str = None,
                 user_agent: str = None,
                 ip_address: str = None,
                 additional_data: Dict[str, Any] = None):
        self.error_id = error_id or str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.user_id = user_id
        self.request_path = request_path
        self.request_method = request_method
        self.user_agent = user_agent
        self.ip_address = ip_address
        self.additional_data = additional_data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "additional_data": self.additional_data
        }

class ErrorInfo:
    """错误信息封装类"""
    
    def __init__(self,
                 message: str,
                 error_code: str = None,
                 level: ErrorLevel = ErrorLevel.ERROR,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 context: ErrorContext = None,
                 original_exception: Exception = None,
                 user_message: str = None,
                 recovery_suggestions: List[str] = None,
                 debug_info: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.level = level
        self.category = category
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestions = recovery_suggestions or []
        self.debug_info = debug_info or {}
        
        # 如果有原始异常，添加堆栈跟踪
        if original_exception:
            self.debug_info["traceback"] = traceback.format_exception(
                type(original_exception), original_exception, original_exception.__traceback__
            )
    
    def _generate_user_message(self) -> str:
        """根据错误类别生成用户友好的错误消息"""
        category_messages = {
            ErrorCategory.AUTHENTICATION: "登录验证失败，请检查用户名和密码",
            ErrorCategory.AUTHORIZATION: "权限不足，无法执行此操作",
            ErrorCategory.VALIDATION: "输入数据格式不正确，请检查后重试",
            ErrorCategory.DATABASE: "数据库操作失败，请稍后重试",
            ErrorCategory.FILE_SYSTEM: "文件操作失败，请检查文件权限",
            ErrorCategory.NETWORK: "网络连接失败，请检查网络连接",
            ErrorCategory.BUSINESS_LOGIC: "操作失败，请检查输入数据",
            ErrorCategory.SYSTEM: "系统内部错误，请联系管理员",
            ErrorCategory.UNKNOWN: "操作失败，请稍后重试"
        }
        return category_messages.get(self.category, "操作失败，请稍后重试")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_id": self.context.error_id,
            "error_message": self.message,  # 改名避免与日志记录的message字段冲突
            "error_code": self.error_code,
            "level": self.level.value,
            "category": self.category.value,
            "user_message": self.user_message,
            "recovery_suggestions": self.recovery_suggestions,
            "timestamp": self.context.timestamp.isoformat(),
            "debug_info": self.debug_info if self.level == ErrorLevel.DEBUG else {}
        }

class UnifiedErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, logger_name: str = "app.error_handler"):
        self.logger = logging.getLogger(logger_name)
        self._error_stats = {}  # 错误统计
    
    def create_error_context(self, request: Request = None, user_id: str = None) -> ErrorContext:
        """创建错误上下文"""
        if request:
            return ErrorContext(
                user_id=user_id,
                request_path=str(request.url.path),
                request_method=request.method,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None
            )
        return ErrorContext(user_id=user_id)
    
    def handle_exception(self,
                        exception: Exception,
                        context: ErrorContext = None,
                        category: ErrorCategory = ErrorCategory.UNKNOWN,
                        user_message: str = None,
                        recovery_suggestions: List[str] = None) -> ErrorInfo:
        """处理异常并创建错误信息"""
        
        # 根据异常类型确定错误分类和级别
        level, category = self._classify_exception(exception, category)
        
        # 创建错误信息
        error_info = ErrorInfo(
            message=str(exception),
            level=level,
            category=category,
            context=context or ErrorContext(),
            original_exception=exception,
            user_message=user_message,
            recovery_suggestions=recovery_suggestions
        )
        
        # 记录日志
        self._log_error(error_info)
        
        # 更新错误统计
        self._update_error_stats(error_info)
        
        return error_info
    
    def _classify_exception(self, exception: Exception, default_category: ErrorCategory) -> tuple:
        """根据异常类型分类错误"""
        exception_mappings = {
            # HTTP异常
            HTTPException: (ErrorLevel.WARNING, ErrorCategory.BUSINESS_LOGIC),
            
            # 认证和授权异常
            PermissionError: (ErrorLevel.WARNING, ErrorCategory.AUTHORIZATION),
            
            # 文件系统异常
            FileNotFoundError: (ErrorLevel.WARNING, ErrorCategory.FILE_SYSTEM),
            FileExistsError: (ErrorLevel.WARNING, ErrorCategory.FILE_SYSTEM),
            IsADirectoryError: (ErrorLevel.WARNING, ErrorCategory.FILE_SYSTEM),
            NotADirectoryError: (ErrorLevel.WARNING, ErrorCategory.FILE_SYSTEM),
            
            # 数据验证异常
            ValueError: (ErrorLevel.WARNING, ErrorCategory.VALIDATION),
            TypeError: (ErrorLevel.ERROR, ErrorCategory.VALIDATION),
            
            # 网络异常
            ConnectionError: (ErrorLevel.ERROR, ErrorCategory.NETWORK),
            TimeoutError: (ErrorLevel.ERROR, ErrorCategory.NETWORK),
            
            # 系统异常
            MemoryError: (ErrorLevel.CRITICAL, ErrorCategory.SYSTEM),
            SystemError: (ErrorLevel.CRITICAL, ErrorCategory.SYSTEM),
        }
        
        for exc_type, (level, category) in exception_mappings.items():
            if isinstance(exception, exc_type):
                return level, category
        
        # 默认为系统错误
        return ErrorLevel.ERROR, default_category
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_message = f"[{error_info.context.error_id}] {error_info.message}"
        
        # 添加上下文信息
        if error_info.context.user_id:
            log_message += f" | User: {error_info.context.user_id}"
        if error_info.context.request_path:
            log_message += f" | Path: {error_info.context.request_path}"
        
        # 根据错误级别选择日志方法
        if error_info.level == ErrorLevel.DEBUG:
            self.logger.debug(log_message, extra=error_info.to_dict())
        elif error_info.level == ErrorLevel.INFO:
            self.logger.info(log_message, extra=error_info.to_dict())
        elif error_info.level == ErrorLevel.WARNING:
            self.logger.warning(log_message, extra=error_info.to_dict())
        elif error_info.level == ErrorLevel.ERROR:
            self.logger.error(log_message, extra=error_info.to_dict(), exc_info=error_info.original_exception)
        elif error_info.level == ErrorLevel.CRITICAL:
            self.logger.critical(log_message, extra=error_info.to_dict(), exc_info=error_info.original_exception)
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """更新错误统计"""
        category_key = error_info.category.value
        if category_key not in self._error_stats:
            self._error_stats[category_key] = {"count": 0, "last_occurrence": None}
        
        self._error_stats[category_key]["count"] += 1
        self._error_stats[category_key]["last_occurrence"] = error_info.context.timestamp
    
    def create_http_exception(self, error_info: ErrorInfo) -> HTTPException:
        """根据错误信息创建HTTP异常"""
        status_code_mapping = {
            ErrorCategory.AUTHENTICATION: 401,
            ErrorCategory.AUTHORIZATION: 403,
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.DATABASE: 500,
            ErrorCategory.FILE_SYSTEM: 404,
            ErrorCategory.NETWORK: 503,
            ErrorCategory.BUSINESS_LOGIC: 400,
            ErrorCategory.SYSTEM: 500,
            ErrorCategory.UNKNOWN: 500
        }
        
        status_code = status_code_mapping.get(error_info.category, 500)
        
        return HTTPException(
            status_code=status_code,
            detail={
                "error_id": error_info.context.error_id,
                "message": error_info.user_message,
                "error_code": error_info.error_code,
                "recovery_suggestions": error_info.recovery_suggestions
            }
        )
    
    def create_json_response(self, error_info: ErrorInfo) -> JSONResponse:
        """创建JSON错误响应"""
        status_code_mapping = {
            ErrorCategory.AUTHENTICATION: 401,
            ErrorCategory.AUTHORIZATION: 403,
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.DATABASE: 500,
            ErrorCategory.FILE_SYSTEM: 404,
            ErrorCategory.NETWORK: 503,
            ErrorCategory.BUSINESS_LOGIC: 400,
            ErrorCategory.SYSTEM: 500,
            ErrorCategory.UNKNOWN: 500
        }
        
        status_code = status_code_mapping.get(error_info.category, 500)
        
        response_data = {
            "status": "error",
            "error_id": error_info.context.error_id,
            "message": error_info.user_message,
            "error_code": error_info.error_code,
            "recovery_suggestions": error_info.recovery_suggestions,
            "timestamp": error_info.context.timestamp.isoformat()
        }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    def create_html_response(self, error_info: ErrorInfo, request: Request, 
                           template_name: str = "error.html") -> HTMLResponse:
        """创建HTML错误响应"""
        try:
            return templates.TemplateResponse(template_name, {
                "request": request,
                "error": error_info.to_dict(),
                "theme": "default"
            })
        except Exception:
            # 如果模板渲染失败，返回简单的HTML响应
            return HTMLResponse(
                content=f"""
                <html>
                <head><title>错误</title></head>
                <body>
                    <h1>系统错误</h1>
                    <p>{error_info.user_message}</p>
                    <p>错误ID: {error_info.context.error_id}</p>
                    <p>时间: {error_info.context.timestamp}</p>
                </body>
                </html>
                """,
                status_code=500
            )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            "total_errors": sum(stat["count"] for stat in self._error_stats.values()),
            "by_category": self._error_stats,
            "generated_at": datetime.now().isoformat()
        }

# 全局错误处理器实例
error_handler = UnifiedErrorHandler()

def handle_controller_error(operation_name: str = "操作"):
    """控制器错误处理装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # 重新抛出HTTP异常
                raise
            except Exception as e:
                # 提取请求对象和用户信息
                request = None
                user_id = None
                
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                # 创建错误上下文
                context = error_handler.create_error_context(request, user_id)
                
                # 处理异常
                error_info = error_handler.handle_exception(
                    e, context, 
                    recovery_suggestions=[
                        "请检查输入数据是否正确",
                        "如果问题持续存在，请联系管理员",
                        f"错误ID: {context.error_id}"
                    ]
                )
                
                # 抛出HTTP异常
                raise error_handler.create_http_exception(error_info)
        
        return wrapper
    return decorator

def create_recovery_suggestions(error_category: ErrorCategory) -> List[str]:
    """根据错误类别创建恢复建议"""
    suggestions_map = {
        ErrorCategory.AUTHENTICATION: [
            "请检查用户名和密码是否正确",
            "确认账户是否已激活",
            "尝试重新登录"
        ],
        ErrorCategory.AUTHORIZATION: [
            "请联系管理员分配相应权限",
            "确认您有权限执行此操作",
            "尝试使用其他账户登录"
        ],
        ErrorCategory.VALIDATION: [
            "请检查输入数据的格式",
            "确认所有必填字段已填写",
            "参考帮助文档中的数据格式要求"
        ],
        ErrorCategory.DATABASE: [
            "请稍后重试",
            "如果问题持续存在，请联系管理员",
            "检查网络连接是否正常"
        ],
        ErrorCategory.FILE_SYSTEM: [
            "检查文件是否存在",
            "确认文件路径是否正确",
            "检查文件权限设置"
        ],
        ErrorCategory.NETWORK: [
            "检查网络连接",
            "稍后重试",
            "联系网络管理员"
        ],
        ErrorCategory.BUSINESS_LOGIC: [
            "检查操作步骤是否正确",
            "确认数据状态符合操作要求",
            "参考用户手册"
        ],
        ErrorCategory.SYSTEM: [
            "请稍后重试",
            "联系系统管理员",
            "记录错误ID以便技术支持"
        ]
    }
    
    return suggestions_map.get(error_category, [
        "请稍后重试",
        "如果问题持续存在，请联系管理员"
    ])