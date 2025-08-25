"""
Authentication decorators for MarkEdit application.

This module contains decorator functions for authentication and authorization.
"""
import logging
from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, Request, Depends

logger = logging.getLogger(__name__)

def _get_session_service():
    """延迟导入session_service"""
    from app.services.session_service import session_service
    return session_service

def get_session(request: Request):
    """获取当前会话数据（依赖注入用）"""
    return _get_session_service().get_session(request)

def require_auth_session(func: Callable) -> Callable:
    """要求用户已登录的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 查找request参数
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            # 从kwargs中查找
            request = kwargs.get('request')
        
        if not request:
            raise HTTPException(status_code=500, detail="无法获取请求对象")
        
        session_service = _get_session_service()
        session = session_service.get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="请先登录")
        
        return await func(*args, **kwargs)
    
    return wrapper

def require_permission(permission: str):
    """要求特定权限的装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找request参数
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            session_service = _get_session_service()
            session = session_service.get_session(request)
            if not session.username:
                raise HTTPException(status_code=401, detail="请先登录")
            
            # 更新会话权限（如果需要）
            await session_service.update_session_permissions(session)
            
            # 检查权限
            has_permission = await session_service.check_user_permission(session.username, permission)
            if not has_permission:
                raise HTTPException(
                    status_code=403, 
                    detail=f"权限不足，需要权限: {permission}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_role(role: str):
    """要求特定角色的装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找request参数
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            session_service = _get_session_service()
            session = session_service.get_session(request)
            if not session.username:
                raise HTTPException(status_code=401, detail="请先登录")
            
            # 更新会话权限（如果需要）
            await session_service.update_session_permissions(session)
            
            # 检查角色
            user_roles = await session_service.get_user_roles(session.username)
            if role not in user_roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"权限不足，需要角色: {role}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_admin(func: Callable) -> Callable:
    """要求管理员权限的装饰器"""
    return require_permission("admin_access")(func)

def require_super_admin(func: Callable) -> Callable:
    """要求超级管理员权限的装饰器"""
    return require_permission("super_admin")(func)

def optional_auth(func: Callable) -> Callable:
    """可选认证装饰器（不强制要求登录）"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 查找request参数
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            request = kwargs.get('request')
        
        if request:
            try:
                session_service = _get_session_service()
                session = session_service.get_session(request)
                if session.username:
                    # 如果用户已登录，更新会话权限
                    await session_service.update_session_permissions(session)
            except Exception as e:
                logger.warning(f"可选认证失败: {str(e)}")
        
        return await func(*args, **kwargs)
    
    return wrapper

# =============================================================================
# 注意：向后兼容的函数已移至 app.common.auth 模块
# 请直接从 app.common 导入这些函数:
# from app.common import check_user_permission, get_user_permissions, get_user_roles
# =============================================================================