"""
Base utilities for MarkEdit application.

This module provides common utility classes and functions that can be reused
across different parts of the application to reduce code duplication.
"""
import json
import logging
from typing import Any, Dict, Optional, Union, Callable, Type, List
from pathlib import Path
from functools import wraps

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

class ExceptionHandler:
    """统一的异常处理工具类"""
    
    @staticmethod
    def handle_json_error(operation: str = "JSON操作"):
        """JSON操作异常处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except json.JSONDecodeError as e:
                    logger.error(f"{operation}JSON解析失败: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"无效的JSON格式: {str(e)}")
                except Exception as e:
                    logger.error(f"{operation}失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{operation}失败: {str(e)}")
            return wrapper
        return decorator
    
    @staticmethod
    def handle_file_error(operation: str = "文件操作"):
        """文件操作异常处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except FileNotFoundError as e:
                    logger.warning(f"{operation}文件未找到: {str(e)}")
                    raise HTTPException(status_code=404, detail=f"文件不存在: {str(e)}")
                except PermissionError as e:
                    logger.warning(f"{operation}权限错误: {str(e)}")
                    raise HTTPException(status_code=403, detail=f"文件访问权限不足: {str(e)}")
                except UnicodeDecodeError as e:
                    logger.warning(f"{operation}编码错误: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"文件编码错误: {str(e)}")
                except Exception as e:
                    logger.error(f"{operation}失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{operation}失败: {str(e)}")
            return wrapper
        return decorator
    
    @staticmethod
    def handle_system_error(operation: str = "系统操作"):
        """系统操作异常处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except ImportError as e:
                    logger.error(f"{operation}导入错误: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"系统组件缺失: {str(e)}")
                except OSError as e:
                    logger.error(f"{operation}系统错误: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"系统操作失败: {str(e)}")
                except Exception as e:
                    logger.error(f"{operation}失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{operation}失败: {str(e)}")
            return wrapper
        return decorator
    
    @staticmethod
    def create_http_exception(status_code: int, message: str, 
                            error_code: str = None) -> HTTPException:
        """创建标准的HTTP异常"""
        detail = {"message": message}
        if error_code:
            detail["error_code"] = error_code
        return HTTPException(status_code=status_code, detail=detail)


class JSONUtils:
    """JSON操作工具类，统一JSON处理逻辑"""
    
    @staticmethod
    @ExceptionHandler.handle_json_error("JSON验证")
    def validate_json_string(json_str: str) -> bool:
        """验证JSON字符串格式"""
        json.loads(json_str)
        return True
    
    @staticmethod
    @ExceptionHandler.handle_json_error("JSON解析")
    def parse_json_string(json_str: str) -> Dict[str, Any]:
        """安全地解析JSON字符串"""
        return json.loads(json_str)
    
    @staticmethod
    @ExceptionHandler.handle_json_error("JSON序列化")
    def serialize_to_json(data: Any, indent: Optional[int] = None, 
                         ensure_ascii: bool = False) -> str:
        """将数据序列化为JSON字符串"""
        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
    
    @staticmethod
    def safe_json_loads(json_str: str, default: Any = None) -> Any:
        """安全的JSON解析，失败时返回默认值"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default


class ValidationUtils:
    """验证工具类，统一验证逻辑"""
    
    # 危险的文件路径字符
    DANGEROUS_PATH_CHARS = ['..', '~', '$', '&', '|', '>', '<', ';', '\\', '//']
    
    # 允许的主题名称字符
    THEME_NAME_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
    
    @classmethod
    def validate_json(cls, json_str: str, raise_on_error: bool = True) -> bool:
        """验证JSON字符串"""
        if raise_on_error:
            return JSONUtils.validate_json_string(json_str)
        else:
            try:
                json.loads(json_str)
                return True
            except json.JSONDecodeError:
                return False
    
    @classmethod
    def validate_theme_name(cls, theme: str) -> bool:
        """验证主题名称（字母、数字、下划线、连字符）"""
        if not theme or len(theme) > 50:
            return False
        return all(c in cls.THEME_NAME_CHARS for c in theme)
    
    @classmethod
    def validate_password_strength(cls, password: str, 
                                  min_length: int = 8,
                                  require_upper: bool = True,
                                  require_lower: bool = True,
                                  require_digit: bool = True,
                                  require_special: bool = False) -> Dict[str, Any]:
        """验证密码强度，返回详细的验证结果"""
        result = {
            "valid": True,
            "errors": [],
            "score": 0
        }
        
        if len(password) < min_length:
            result["valid"] = False
            result["errors"].append(f"密码长度至少{min_length}位")
        else:
            result["score"] += 1
        
        if require_upper and not any(c.isupper() for c in password):
            result["valid"] = False
            result["errors"].append("密码需要包含大写字母")
        elif any(c.isupper() for c in password):
            result["score"] += 1
        
        if require_lower and not any(c.islower() for c in password):
            result["valid"] = False
            result["errors"].append("密码需要包含小写字母")
        elif any(c.islower() for c in password):
            result["score"] += 1
        
        if require_digit and not any(c.isdigit() for c in password):
            result["valid"] = False
            result["errors"].append("密码需要包含数字")
        elif any(c.isdigit() for c in password):
            result["score"] += 1
        
        if require_special:
            special_chars = "!@#$%^&*()"
            if not any(c in special_chars for c in password):
                result["valid"] = False
                result["errors"].append("密码需要包含特殊字符")
            elif any(c in special_chars for c in password):
                result["score"] += 1
        
        return result
    
    @classmethod
    def sanitize_file_path(cls, path: str) -> str:
        """清理文件路径，防止路径遍历攻击"""
        if not path:
            return ""
        
        # 移除危险字符
        cleaned_path = path
        for char in cls.DANGEROUS_PATH_CHARS:
            cleaned_path = cleaned_path.replace(char, '')
        
        # 移除开头的斜杠和反斜杠
        cleaned_path = cleaned_path.lstrip('/\\')
        
        # 限制路径长度
        if len(cleaned_path) > 500:
            cleaned_path = cleaned_path[:500]
        
        return cleaned_path
    
    @classmethod
    def validate_file_path(cls, path: str, allowed_extensions: List[str] = None) -> bool:
        """验证文件路径的安全性"""
        if not path:
            return False
        
        # 检查危险字符
        if any(char in path for char in cls.DANGEROUS_PATH_CHARS):
            return False
        
        # 检查文件扩展名
        if allowed_extensions:
            path_obj = Path(path)
            ext = path_obj.suffix.lower()
            if ext not in [f".{ext}" if not ext.startswith('.') else ext for ext in allowed_extensions]:
                return False
        
        # 检查路径长度
        if len(path) > 500:
            return False
        
        return True


class RequestUtils:
    """请求处理工具类，统一请求参数获取逻辑"""
    
    @staticmethod
    def extract_request_from_args(*args, **kwargs) -> Optional[Request]:
        """从函数参数中提取Request对象"""
        # 从位置参数中查找
        for arg in args:
            if isinstance(arg, Request):
                return arg
        
        # 从关键字参数中查找
        request = kwargs.get('request')
        if isinstance(request, Request):
            return request
        
        return None
    
    @staticmethod
    def ensure_request_exists(*args, **kwargs) -> Request:
        """确保Request对象存在，否则抛出异常"""
        request = RequestUtils.extract_request_from_args(*args, **kwargs)
        if not request:
            raise HTTPException(status_code=500, detail="无法获取请求对象")
        return request
    
    @staticmethod
    async def safe_parse_json(request: Request, required_fields: List[str] = None) -> Dict[str, Any]:
        """安全地解析请求的JSON数据"""
        try:
            body = await request.json()
            
            if required_fields:
                missing_fields = [field for field in required_fields if field not in body]
                if missing_fields:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"缺少必需字段: {', '.join(missing_fields)}"
                    )
            
            return body
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            raise HTTPException(status_code=400, detail="无效的JSON格式")
        except Exception as e:
            logger.error(f"请求解析异常: {str(e)}")
            raise HTTPException(status_code=500, detail="请求解析失败")


class ServiceImportUtils:
    """服务导入工具类，统一延迟导入模式"""
    
    _service_cache = {}
    
    @classmethod
    def get_session_service(cls):
        """延迟导入session_service"""
        if 'session_service' not in cls._service_cache:
            from app.services.session_service import session_service
            cls._service_cache['session_service'] = session_service
        return cls._service_cache['session_service']
    
    @classmethod
    def get_user_service(cls):
        """延迟导入user_service"""
        if 'user_service' not in cls._service_cache:
            from app.common import get_user_service
            cls._service_cache['user_service'] = get_user_service()
        return cls._service_cache['user_service']
    
    @classmethod
    def get_admin_service(cls):
        """延迟导入admin_service"""
        if 'admin_service' not in cls._service_cache:
            from app.common import get_admin_service
            cls._service_cache['admin_service'] = get_admin_service()
        return cls._service_cache['admin_service']
    
    @classmethod
    def clear_cache(cls):
        """清除服务缓存（主要用于测试）"""
        cls._service_cache.clear()


class FormatUtils:
    """格式化工具类，统一数据格式化逻辑"""
    
    @staticmethod
    def format_bytes(bytes_value: Union[int, float]) -> str:
        """格式化字节大小"""
        try:
            if bytes_value == 0:
                return "0 B"
            
            size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
            import math
            i = int(math.floor(math.log(bytes_value, 1024)))
            p = math.pow(1024, i)
            s = round(bytes_value / p, 2)
            
            return f"{s} {size_names[i]}"
        except (ValueError, OverflowError, TypeError) as e:
            logger.warning(f"格式化字节大小失败: {str(e)}")
            return str(bytes_value)
    
    @staticmethod
    def format_duration(seconds: Union[int, float]) -> str:
        """格式化持续时间"""
        try:
            if seconds < 0:
                return "0秒"
            
            days, remainder = divmod(int(seconds), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            parts = []
            if days > 0:
                parts.append(f"{days}天")
            if hours > 0:
                parts.append(f"{hours}小时")
            if minutes > 0:
                parts.append(f"{minutes}分钟")
            if seconds > 0 or not parts:
                parts.append(f"{seconds}秒")
            
            return "".join(parts)
        except (ValueError, TypeError) as e:
            logger.warning(f"格式化持续时间失败: {str(e)}")
            return str(seconds)
    
    @staticmethod
    def format_timestamp(timestamp: Union[int, float], 
                        format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间戳"""
        try:
            import datetime
            dt = datetime.datetime.fromtimestamp(timestamp)
            return dt.strftime(format_str)
        except (ValueError, TypeError, OSError) as e:
            logger.warning(f"格式化时间戳失败: {str(e)}")
            return str(timestamp)


# 向后兼容的函数别名
validate_json_string = JSONUtils.validate_json_string
validate_json_and_parse = JSONUtils.parse_json_string
validate_theme_name = ValidationUtils.validate_theme_name
validate_password_strength = ValidationUtils.validate_password_strength
sanitize_file_path = ValidationUtils.sanitize_file_path
format_bytes = FormatUtils.format_bytes
format_duration = FormatUtils.format_duration