"""
Enhanced response utilities for MarkEdit application.

This module provides improved response handling with reduced code duplication
and more consistent behavior across the application.
"""
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from fastapi import HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse

from .base_utils import ExceptionHandler, ValidationUtils, FormatUtils
from .file_utils import is_text_file, is_image_file

logger = logging.getLogger(__name__)

class ResponseBuilder:
    """响应构建器，提供统一的响应格式"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", 
                status_code: int = 200) -> JSONResponse:
        """创建成功响应"""
        response_data = {
            "status": "success",
            "message": message
        }
        
        if data is not None:
            if isinstance(data, dict):
                response_data.update(data)
            else:
                response_data["data"] = data
        
        return JSONResponse(content=response_data, status_code=status_code)
    
    @staticmethod
    def error(message: str, status_code: int = 400, 
              error_code: str = None, details: Any = None) -> JSONResponse:
        """创建错误响应"""
        response_data = {
            "status": "error",
            "message": message
        }
        
        if error_code:
            response_data["error_code"] = error_code
        
        if details:
            response_data["details"] = details
        
        return JSONResponse(content=response_data, status_code=status_code)
    
    @staticmethod
    def list_response(items: List[Any], total: int = None, 
                     page: int = None, page_size: int = None) -> JSONResponse:
        """创建列表响应"""
        response_data = {
            "status": "success",
            "items": items,
            "count": len(items)
        }
        
        if total is not None:
            response_data["total"] = total
        
        if page is not None and page_size is not None:
            response_data["pagination"] = {
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total else 1
            }
        
        return JSONResponse(content=response_data)


class FileResponseHandler:
    """文件响应处理器，统一文件响应逻辑"""
    
    # 支持的文本文件MIME类型
    TEXT_MIME_TYPES = {
        '.html': 'text/html; charset=utf-8',
        '.htm': 'text/html; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.xml': 'application/xml; charset=utf-8',
        '.txt': 'text/plain; charset=utf-8',
        '.md': 'text/markdown; charset=utf-8',
        '.py': 'text/plain; charset=utf-8',
        '.yml': 'text/yaml; charset=utf-8',
        '.yaml': 'text/yaml; charset=utf-8'
    }
    
    # 支持的图片文件MIME类型
    IMAGE_MIME_TYPES = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.ico': 'image/x-icon'
    }
    
    # 支持的编码列表
    SUPPORTED_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
    
    @classmethod
    @ExceptionHandler.handle_file_error("文件响应创建")
    def create_file_response(cls, file_path: Path, raw: bool = False,
                           encoding: str = None) -> Response:
        """创建文件响应（改进版）"""
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"路径不是文件: {file_path.name}")
        
        suffix = file_path.suffix.lower()
        
        if raw or is_text_file(file_path):
            return cls._create_text_response(file_path, suffix, encoding)
        elif is_image_file(file_path):
            return cls._create_image_response(file_path, suffix)
        else:
            return cls._create_binary_response(file_path)
    
    @classmethod
    def _create_text_response(cls, file_path: Path, suffix: str, 
                             encoding: str = None) -> Response:
        """创建文本文件响应"""
        encodings_to_try = [encoding] if encoding else cls.SUPPORTED_ENCODINGS
        
        for enc in encodings_to_try:
            if enc is None:
                continue
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                
                mime_type = cls.TEXT_MIME_TYPES.get(suffix, 'text/plain; charset=utf-8')
                return Response(content=content, media_type=mime_type)
                
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，返回错误
        raise HTTPException(
            status_code=400, 
            detail=f"无法解码文本文件: {file_path.name}，尝试的编码: {', '.join(filter(None, encodings_to_try))}"
        )
    
    @classmethod
    def _create_image_response(cls, file_path: Path, suffix: str) -> FileResponse:
        """创建图片文件响应"""
        mime_type = cls.IMAGE_MIME_TYPES.get(suffix, 'application/octet-stream')
        return FileResponse(file_path, media_type=mime_type)
    
    @classmethod
    def _create_binary_response(cls, file_path: Path) -> FileResponse:
        """创建二进制文件响应"""
        return FileResponse(file_path)
    
    @classmethod
    @ExceptionHandler.handle_file_error("静态文件响应创建")
    def create_static_file_response(cls, file_path: Path,
                                   cache_control: str = None) -> Response:
        """创建静态文件响应（改进版）"""
        # 对于图片文件，不使用raw模式以确保正确的MIME类型
        is_image = cls._get_mime_type(file_path).startswith('image/')
        response = cls.create_file_response(file_path, raw=not is_image)
        
        # 添加缓存控制头
        if cache_control:
            response.headers["Cache-Control"] = cache_control
        elif file_path.suffix.lower() in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg']:
            # 对于静态资源，设置较长的缓存时间
            response.headers["Cache-Control"] = "public, max-age=31536000"  # 1年
        
        return response
    
    @classmethod
    def get_file_info(cls, file_path: Path) -> Dict[str, Any]:
        """获取文件信息"""
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")
        
        stat = file_path.stat()
        
        return {
            "name": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "size_formatted": FormatUtils.format_bytes(stat.st_size),
            "modified": FormatUtils.format_timestamp(stat.st_mtime),
            "is_text": is_text_file(file_path),
            "is_image": is_image_file(file_path),
            "extension": file_path.suffix.lower(),
            "mime_type": cls._get_mime_type(file_path)
        }
    
    @classmethod
    def _get_mime_type(cls, file_path: Path) -> str:
        """获取文件的MIME类型"""
        suffix = file_path.suffix.lower()
        
        if suffix in cls.TEXT_MIME_TYPES:
            return cls.TEXT_MIME_TYPES[suffix]
        elif suffix in cls.IMAGE_MIME_TYPES:
            return cls.IMAGE_MIME_TYPES[suffix]
        else:
            return 'application/octet-stream'


class APIResponseHandler:
    """API响应处理器，统一API响应格式"""
    
    @staticmethod
    def paginated_response(items: List[Any], page: int, page_size: int, 
                          total: int, extra_data: Dict[str, Any] = None) -> JSONResponse:
        """创建分页响应"""
        response_data = {
            "status": "success",
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": page * page_size < total,
                "has_prev": page > 1
            }
        }
        
        if extra_data:
            response_data.update(extra_data)
        
        return JSONResponse(content=response_data)
    
    @staticmethod
    def operation_response(success: bool, message: str, 
                          data: Any = None, error_code: str = None) -> JSONResponse:
        """创建操作结果响应"""
        if success:
            return ResponseBuilder.success(data, message)
        else:
            return ResponseBuilder.error(message, 400, error_code)
    
    @staticmethod
    def validation_error_response(errors: List[str]) -> JSONResponse:
        """创建验证错误响应"""
        return ResponseBuilder.error(
            message="数据验证失败",
            status_code=400,
            error_code="VALIDATION_ERROR",
            details={"validation_errors": errors}
        )
    
    @staticmethod
    def not_found_response(resource: str = "资源") -> JSONResponse:
        """创建资源未找到响应"""
        return ResponseBuilder.error(
            message=f"{resource}不存在",
            status_code=404,
            error_code="NOT_FOUND"
        )
    
    @staticmethod
    def permission_denied_response(required_permission: str = None) -> JSONResponse:
        """创建权限拒绝响应"""
        message = "权限不足"
        if required_permission:
            message += f"，需要权限: {required_permission}"
        
        return ResponseBuilder.error(
            message=message,
            status_code=403,
            error_code="PERMISSION_DENIED"
        )
    
    @staticmethod
    def rate_limit_response(retry_after: int = None) -> JSONResponse:
        """创建速率限制响应"""
        message = "请求过于频繁"
        if retry_after:
            message += f"，请在{retry_after}秒后重试"
        
        response = ResponseBuilder.error(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )
        
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        
        return response


# 向后兼容的函数别名
create_file_response = FileResponseHandler.create_file_response
create_static_file_response = FileResponseHandler.create_static_file_response

# 新的便捷函数
success_response = ResponseBuilder.success
error_response = ResponseBuilder.error
list_response = ResponseBuilder.list_response