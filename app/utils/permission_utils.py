"""
Permission utilities for MarkEdit application.

This module contains utility functions and decorators for permission handling.
"""
import logging
from functools import wraps
from typing import Callable, List, Dict, Any
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

class PermissionError(Exception):
    """权限相关错误"""
    pass

def require_permissions(*required_permissions: str):
    """
    装饰器：要求用户拥有指定的权限
    
    Args:
        required_permissions: 必需的权限列表
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取request对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # 从kwargs中查找request
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            # 获取用户会话
            from app.services.session_service import session_service
            from app.common import check_user_permission
            try:
                session = session_service.get_session(request)
                if not session.username:
                    raise HTTPException(status_code=401, detail="用户未登录")
                
                # 检查所有必需权限
                for permission in required_permissions:
                    has_permission = await check_user_permission(session.username, permission)
                    if not has_permission:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"权限不足，缺少权限: {permission}"
                        )
                
                # 所有权限检查通过，执行原函数
                return await func(*args, **kwargs)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"权限检查过程中出错: {str(e)}")
                raise HTTPException(status_code=500, detail="权限检查失败")
        
        return wrapper
    return decorator

def require_any_permission(*permissions: str):
    """
    装饰器：要求用户拥有任意一个指定的权限
    
    Args:
        permissions: 权限列表（用户只需拥有其中任意一个）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取request对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # 从kwargs中查找request
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            # 获取用户会话
            from app.services.session_service import session_service
            from app.common import check_user_permission
            try:
                session = session_service.get_session(request)
                if not session.username:
                    raise HTTPException(status_code=401, detail="用户未登录")
                
                # 检查是否拥有任意一个权限
                has_any_permission = False
                for permission in permissions:
                    if await check_user_permission(session.username, permission):
                        has_any_permission = True
                        break
                
                if not has_any_permission:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"权限不足，需要以下权限之一: {', '.join(permissions)}"
                    )
                
                # 权限检查通过，执行原函数
                return await func(*args, **kwargs)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"权限检查过程中出错: {str(e)}")
                raise HTTPException(status_code=500, detail="权限检查失败")
        
        return wrapper
    return decorator

async def check_user_has_permission(username: str, permission: str) -> bool:
    """
    检查用户是否拥有指定权限
    
    Args:
        username: 用户名
        permission: 权限名称
        
    Returns:
        是否拥有权限
    """
    try:
        from app.common import check_user_permission
        return await check_user_permission(username, permission)
    except Exception as e:
        logger.error(f"检查用户权限时出错: {str(e)}")
        return False

async def check_user_has_role(username: str, role: str) -> bool:
    """
    检查用户是否拥有指定角色
    
    Args:
        username: 用户名
        role: 角色名称
        
    Returns:
        是否拥有角色
    """
    try:
        from app.common import get_user_roles
        user_roles = await get_user_roles(username)
        return role in user_roles
    except Exception as e:
        logger.error(f"检查用户角色时出错: {str(e)}")
        return False

async def get_user_permission_summary(username: str) -> Dict[str, Any]:
    """
    获取用户权限摘要信息
    
    Args:
        username: 用户名
        
    Returns:
        权限摘要字典
    """
    try:
        from app.common import get_user_roles, get_user_permissions
        
        roles = await get_user_roles(username)
        permissions = await get_user_permissions(username)
        
        # 按类别分组权限
        permission_groups = {
            "用户管理": [],
            "角色管理": [],
            "权限管理": [],
            "系统管理": [],
            "内容管理": [],
            "文件操作": [],
            "构建功能": [],
            "特殊权限": []
        }
        
        for permission in permissions:
            if permission.startswith("user."):
                permission_groups["用户管理"].append(permission)
            elif permission.startswith("role."):
                permission_groups["角色管理"].append(permission)
            elif permission.startswith("permission."):
                permission_groups["权限管理"].append(permission)
            elif permission.startswith("system."):
                permission_groups["系统管理"].append(permission)
            elif permission.startswith("content.") or permission == "theme_access":
                permission_groups["内容管理"].append(permission)
            elif permission.startswith("file."):
                permission_groups["文件操作"].append(permission)
            elif permission.startswith("build."):
                permission_groups["构建功能"].append(permission)
            else:
                permission_groups["特殊权限"].append(permission)
        
        return {
            "username": username,
            "roles": roles,
            "permissions_count": len(permissions),
            "permission_groups": permission_groups,
            "all_permissions": permissions
        }
        
    except Exception as e:
        logger.error(f"获取用户权限摘要时出错: {str(e)}")
        return {
            "username": username,
            "roles": [],
            "permissions_count": 0,
            "permission_groups": {},
            "all_permissions": [],
            "error": str(e)
        }

def validate_permission_name(permission: str) -> bool:
    """
    验证权限名称格式
    
    Args:
        permission: 权限名称
        
    Returns:
        是否为有效的权限名称
    """
    if not permission or not isinstance(permission, str):
        return False
    
    # 权限名称应该是点分格式，如 "user.create", "system.config"
    parts = permission.split('.')
    if len(parts) < 2:
        return False
    
    # 检查每个部分是否为有效标识符
    for part in parts:
        if not part.isidentifier():
            return False
    
    return True

def validate_role_name(role: str) -> bool:
    """
    验证角色名称格式
    
    Args:
        role: 角色名称
        
    Returns:
        是否为有效的角色名称
    """
    if not role or not isinstance(role, str):
        return False
    
    # 角色名称应该是简单的标识符或包含下划线
    import re
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', role))

class PermissionConstants:
    """权限常量定义"""
    
    # 用户管理权限
    USER_CREATE = "user.create"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"
    USER_LIST = "user.list"
    USER_SELF_INFO = "user.self_info"
    USER_SELF_EDIT = "user.self_edit"
    
    # 角色管理权限
    ROLE_CREATE = "role.create"
    ROLE_EDIT = "role.edit"
    ROLE_DELETE = "role.delete"
    ROLE_LIST = "role.list"
    
    # 权限管理权限
    PERMISSION_CREATE = "permission.create"
    PERMISSION_EDIT = "permission.edit"
    PERMISSION_DELETE = "permission.delete"
    PERMISSION_LIST = "permission.list"
    
    # 系统管理权限
    SYSTEM_BACKUP = "system.backup"
    SYSTEM_CONFIG = "system.config"
    CONTENT_EDIT = "content.edit"
    
    # 特殊功能权限
    EPUB_CONVERSION = "epub_conversion"
    MANUAL_BACKUP = "manual_backup"
    THEME_ACCESS = "theme_access"
    ADMIN_ACCESS = "admin_access"
    SUPER_ADMIN = "super_admin"
    
    # 文件操作权限
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    
    # 构建权限
    BUILD_EPUB = "build.epub"
    BUILD_PDF = "build.pdf"

class RoleConstants:
    """角色常量定义"""
    
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"