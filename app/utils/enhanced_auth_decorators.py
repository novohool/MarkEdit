"""
Enhanced authentication decorators for MarkEdit application.

This module contains improved decorator functions that use the base utilities
to reduce code duplication and provide more consistent behavior.
"""
import logging
from functools import wraps
from typing import Callable, Any, Optional, List
from fastapi import HTTPException, Request, Depends

from .base_utils import (
    ExceptionHandler, RequestUtils, ServiceImportUtils
)

logger = logging.getLogger(__name__)

class AuthDecorators:
    """统一的认证装饰器类"""
    
    @staticmethod
    def get_session(request: Request):
        """获取当前会话数据（依赖注入用）"""
        session_service = ServiceImportUtils.get_session_service()
        return session_service.get_session(request)
    
    @staticmethod
    def _extract_session_from_request(*args, **kwargs):
        """从请求中提取会话信息的通用方法"""
        request = RequestUtils.extract_request_from_args(*args, **kwargs)
        if not request:
            raise HTTPException(status_code=500, detail="无法获取请求对象")
        
        session_service = ServiceImportUtils.get_session_service()
        session = session_service.get_session(request)
        
        return request, session, session_service
    
    @staticmethod
    def require_auth_session(func: Callable) -> Callable:
        """要求用户已登录的装饰器（改进版）"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                request, session, session_service = AuthDecorators._extract_session_from_request(*args, **kwargs)
                
                if not session.username:
                    raise HTTPException(status_code=401, detail="请先登录")
                
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"认证检查失败: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="认证检查失败")
        
        return wrapper
    
    @staticmethod
    def require_permission(permission: str, update_permissions: bool = True):
        """要求特定权限的装饰器（改进版）"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    request, session, session_service = AuthDecorators._extract_session_from_request(*args, **kwargs)
                    
                    if not session.username:
                        raise HTTPException(status_code=401, detail="请先登录")
                    
                    # 更新会话权限（如果需要）
                    if update_permissions:
                        await session_service.update_session_permissions(session)
                    
                    # 检查权限
                    has_permission = await session_service.check_user_permission(session.username, permission)
                    if not has_permission:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"权限不足，需要权限: {permission}"
                        )
                    
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"权限检查失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail="权限检查失败")
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_any_permission(permissions: List[str], update_permissions: bool = True):
        """要求任意一个权限的装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    request, session, session_service = AuthDecorators._extract_session_from_request(*args, **kwargs)
                    
                    if not session.username:
                        raise HTTPException(status_code=401, detail="请先登录")
                    
                    # 更新会话权限（如果需要）
                    if update_permissions:
                        await session_service.update_session_permissions(session)
                    
                    # 检查任意一个权限
                    has_any_permission = False
                    for permission in permissions:
                        if await session_service.check_user_permission(session.username, permission):
                            has_any_permission = True
                            break
                    
                    if not has_any_permission:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"权限不足，需要以下权限之一: {', '.join(permissions)}"
                        )
                    
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"权限检查失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail="权限检查失败")
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_role(role: str, update_permissions: bool = True):
        """要求特定角色的装饰器（改进版）"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    request, session, session_service = AuthDecorators._extract_session_from_request(*args, **kwargs)
                    
                    if not session.username:
                        raise HTTPException(status_code=401, detail="请先登录")
                    
                    # 更新会话权限（如果需要）
                    if update_permissions:
                        await session_service.update_session_permissions(session)
                    
                    # 检查角色
                    user_roles = await session_service.get_user_roles(session.username)
                    if role not in user_roles:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"权限不足，需要角色: {role}"
                        )
                    
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"角色检查失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail="角色检查失败")
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_any_role(roles: List[str], update_permissions: bool = True):
        """要求任意一个角色的装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    request, session, session_service = AuthDecorators._extract_session_from_request(*args, **kwargs)
                    
                    if not session.username:
                        raise HTTPException(status_code=401, detail="请先登录")
                    
                    # 更新会话权限（如果需要）
                    if update_permissions:
                        await session_service.update_session_permissions(session)
                    
                    # 检查任意一个角色
                    user_roles = await session_service.get_user_roles(session.username)
                    has_any_role = any(role in user_roles for role in roles)
                    
                    if not has_any_role:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"权限不足，需要以下角色之一: {', '.join(roles)}"
                        )
                    
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"角色检查失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail="角色检查失败")
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_admin(func: Callable) -> Callable:
        """要求管理员权限的装饰器（改进版）"""
        return AuthDecorators.require_permission("admin_access")(func)
    
    @staticmethod
    def require_super_admin(func: Callable) -> Callable:
        """要求超级管理员权限的装饰器（改进版）"""
        return AuthDecorators.require_permission("super_admin")(func)
    
    @staticmethod
    def optional_auth(func: Callable) -> Callable:
        """可选认证装饰器（不强制要求登录）（改进版）"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                request = RequestUtils.extract_request_from_args(*args, **kwargs)
                
                if request:
                    try:
                        session_service = ServiceImportUtils.get_session_service()
                        session = session_service.get_session(request)
                        if session.username:
                            # 如果用户已登录，更新会话权限
                            await session_service.update_session_permissions(session)
                    except Exception as e:
                        logger.warning(f"可选认证失败: {str(e)}")
                
                return await func(*args, **kwargs)
            except Exception as e:
                # 对于可选认证，不应该因为认证失败而阻止请求
                logger.warning(f"可选认证处理异常: {str(e)}")
                return await func(*args, **kwargs)
        
        return wrapper
    
    @staticmethod
    def rate_limit(max_requests: int, window_seconds: int = 60):
        """简单的速率限制装饰器"""
        request_counts = {}
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                import time
                
                try:
                    request = RequestUtils.extract_request_from_args(*args, **kwargs)
                    if not request:
                        return await func(*args, **kwargs)
                    
                    # 获取客户端IP
                    client_ip = request.client.host if request.client else "unknown"
                    current_time = time.time()
                    
                    # 清理过期的记录
                    for ip in list(request_counts.keys()):
                        request_counts[ip] = [
                            timestamp for timestamp in request_counts[ip]
                            if current_time - timestamp < window_seconds
                        ]
                        if not request_counts[ip]:
                            del request_counts[ip]
                    
                    # 检查当前IP的请求次数
                    if client_ip not in request_counts:
                        request_counts[client_ip] = []
                    
                    if len(request_counts[client_ip]) >= max_requests:
                        raise HTTPException(
                            status_code=429,
                            detail=f"请求过于频繁，请在{window_seconds}秒后重试"
                        )
                    
                    # 记录当前请求
                    request_counts[client_ip].append(current_time)
                    
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"速率限制检查失败: {str(e)}", exc_info=True)
                    return await func(*args, **kwargs)  # 速率限制失败时不阻止请求
            
            return wrapper
        return decorator


# 向后兼容的别名和函数
get_session = AuthDecorators.get_session
require_auth_session = AuthDecorators.require_auth_session
require_permission = AuthDecorators.require_permission
require_role = AuthDecorators.require_role
require_admin = AuthDecorators.require_admin
require_super_admin = AuthDecorators.require_super_admin
optional_auth = AuthDecorators.optional_auth

# 新的增强功能
require_any_permission = AuthDecorators.require_any_permission
require_any_role = AuthDecorators.require_any_role
rate_limit = AuthDecorators.rate_limit