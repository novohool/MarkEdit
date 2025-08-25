"""
Authentication functions module for MarkEdit application.

This module provides common authentication and permission management functions.
"""
from typing import List
from fastapi import Request, Depends
from app.models.session_model import SessionData


def get_session(request: Request) -> SessionData:
    """获取当前会话数据（依赖注入用）"""
    from app.common.services import get_session_service
    return get_session_service().get_session(request)

async def require_auth_session(request: Request) -> SessionData:
    """统一的认证检查依赖项"""
    from app.common.services import get_session_service
    return await get_session_service().require_auth_session(request)

def require_auth(request: Request, session: SessionData = Depends(get_session)) -> SessionData:
    """依赖项：检查用户是否已登录，未登录则重定向到登录页"""
    from app.common.services import get_session_service
    return get_session_service().require_auth(request, session)

# 权限相关函数已统一到session_service中，这里保留向后兼容的函数
# 推荐直接使用 get_session_service() 中的方法

async def check_user_permission(username: str, permission: str) -> bool:
    """检查用户权限（向后兼容）"""
    from app.common.services import get_session_service
    return await get_session_service().check_user_permission(username, permission)

async def get_user_permissions(username: str) -> List[str]:
    """获取用户权限列表（向后兼容）"""
    from app.common.services import get_session_service
    return await get_session_service().get_user_permissions(username)

async def get_user_roles(username: str) -> List[str]:
    """获取用户角色列表（向后兼容）"""
    from app.common.services import get_session_service
    return await get_session_service().get_user_roles(username)

async def assign_default_user_role(username: str):
    """分配默认用户角色（向后兼容）"""
    from app.common.services import get_session_service
    return await get_session_service().assign_default_user_role(username)

async def update_session_permissions(session: SessionData):
    """更新会话权限（向后兼容）"""
    from app.common.services import get_session_service
    return await get_session_service().update_session_permissions(session)

async def load_user_permissions_and_roles(session: SessionData):
    """加载用户权限和角色到会话中（向后兼容）"""
    from app.common.services import get_session_service
    return await get_session_service().load_user_permissions_and_roles(session)