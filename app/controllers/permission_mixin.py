"""
权限检查混入类

提供统一的权限验证功能，消除控制器间重复的权限检查逻辑
"""
import logging
from typing import Dict, Any, Optional, Union, List
from functools import wraps

from fastapi import HTTPException, Request, Depends
from app.common import (
    SessionData, check_user_permission, get_session, require_auth_session
)

logger = logging.getLogger(__name__)

class PermissionMixin:
    """权限检查混入类，提供统一的权限验证功能"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    # ===================
    # 权限检查装饰器
    # ===================
    
    def require_permissions(self, permissions: Union[str, List[str]], 
                          require_all: bool = False):
        """
        权限检查装饰器
        
        Args:
            permissions: 必需的权限列表或单个权限
            require_all: 是否需要所有权限（True）还是任一权限（False）
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 从参数中获取session
                session = None
                for arg in args:
                    if isinstance(arg, SessionData):
                        session = arg
                        break
                
                # 从kwargs中获取session
                if not session:
                    session = kwargs.get('session')
                
                if not session:
                    raise HTTPException(status_code=401, detail="用户未登录")
                
                # 权限检查
                await self._check_user_permissions(session, permissions, require_all)
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_file_permission(self, file_type_param: str = 'file_type'):
        """
        文件操作权限检查装饰器
        
        根据文件类型自动检查对应的权限：
        - src: content.edit
        - build: file.manage
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取文件类型
                file_type = kwargs.get(file_type_param)
                if not file_type and len(args) > 0:
                    # 尝试从位置参数获取
                    file_type = args[0] if isinstance(args[0], str) else None
                
                if not file_type:
                    raise HTTPException(status_code=400, detail="未指定文件类型")
                
                # 获取session
                session = None
                for arg in args:
                    if isinstance(arg, SessionData):
                        session = arg
                        break
                
                if not session:
                    session = kwargs.get('session')
                
                if not session:
                    raise HTTPException(status_code=401, detail="用户未登录")
                
                # 根据文件类型检查权限
                await self._check_file_type_permission(session, file_type)
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    # ===================
    # 权限检查方法
    # ===================
    
    async def check_permission(self, session: SessionData, 
                              permission: str) -> bool:
        """检查单个权限"""
        if not session or not session.username:
            return False
        
        return await check_user_permission(session.username, permission)
    
    async def check_any_permission(self, session: SessionData, 
                                  permissions: List[str]) -> bool:
        """检查是否拥有任一权限"""
        if not session or not session.username:
            return False
        
        for permission in permissions:
            if await check_user_permission(session.username, permission):
                return True
        return False
    
    async def check_all_permissions(self, session: SessionData, 
                                   permissions: List[str]) -> bool:
        """检查是否拥有所有权限"""
        if not session or not session.username:
            return False
        
        for permission in permissions:
            if not await check_user_permission(session.username, permission):
                return False
        return True
    
    async def _check_user_permissions(self, session: SessionData, 
                                     permissions: Union[str, List[str]], 
                                     require_all: bool = False):
        """内部权限检查方法"""
        if isinstance(permissions, str):
            permissions = [permissions]
        
        if require_all:
            has_permission = await self.check_all_permissions(session, permissions)
            error_msg = f"权限不足，需要所有权限: {', '.join(permissions)}"
        else:
            has_permission = await self.check_any_permission(session, permissions)
            error_msg = f"权限不足，需要以下任一权限: {', '.join(permissions)}"
        
        if not has_permission:
            self.logger.warning(f"用户 {session.username} {error_msg}")
            raise HTTPException(status_code=403, detail=error_msg)
    
    async def _check_file_type_permission(self, session: SessionData, file_type: str):
        """根据文件类型检查权限"""
        permission_map = {
            'src': 'content.edit',
            'build': 'file.manage',
            'backup': 'manual_backup'
        }
        
        required_permission = permission_map.get(file_type)
        if not required_permission:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_type}"
            )
        
        has_permission = await self.check_permission(session, required_permission)
        if not has_permission:
            raise HTTPException(
                status_code=403, 
                detail=f"权限不足，无法操作{file_type}类型的文件，需要权限: {required_permission}"
            )
    
    # ===================
    # 特定功能权限检查
    # ===================
    
    async def check_admin_permission(self, session: SessionData):
        """检查管理员权限"""
        admin_permissions = [
            "system.config", 
            "user.manage", 
            "role.manage", 
            "permission.manage"
        ]
        
        has_permission = await self.check_any_permission(session, admin_permissions)
        if not has_permission:
            raise HTTPException(
                status_code=403, 
                detail="权限不足，需要管理员权限"
            )
    
    async def check_epub_permission(self, session: SessionData):
        """检查EPUB构建权限"""
        await self._check_user_permissions(session, "build.epub")
    
    async def check_pdf_permission(self, session: SessionData):
        """检查PDF构建权限"""
        await self._check_user_permissions(session, "build.pdf")
    
    async def check_backup_permission(self, session: SessionData):
        """检查备份权限"""
        await self._check_user_permissions(session, "manual_backup")
    
    async def check_content_edit_permission(self, session: SessionData):
        """检查内容编辑权限"""
        await self._check_user_permissions(session, "content.edit")
    
    async def check_file_manage_permission(self, session: SessionData):
        """检查文件管理权限"""
        await self._check_user_permissions(session, "file.manage")
    
    async def check_system_config_permission(self, session: SessionData):
        """检查系统配置权限"""
        await self._check_user_permissions(session, "system.config")


class PermissionDependencyFactory:
    """权限依赖工厂类，创建各种权限检查依赖"""
    
    @staticmethod
    def create_permission_dependency(permission: str):
        """创建单个权限检查依赖"""
        async def permission_check(session: SessionData = Depends(require_auth_session)):
            if not session or not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            has_permission = await check_user_permission(session.username, permission)
            if not has_permission:
                raise HTTPException(
                    status_code=403, 
                    detail=f"权限不足，需要权限: {permission}"
                )
            return session
        
        return permission_check
    
    @staticmethod
    def create_file_permission_dependency(file_type: str):
        """创建文件类型权限检查依赖"""
        permission_map = {
            'src': 'content.edit',
            'build': 'file.manage',
            'backup': 'manual_backup'
        }
        
        required_permission = permission_map.get(file_type)
        if not required_permission:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        return PermissionDependencyFactory.create_permission_dependency(required_permission)


# 预定义的权限检查依赖
require_admin_permission = PermissionDependencyFactory.create_permission_dependency("system.config")
require_epub_permission = PermissionDependencyFactory.create_permission_dependency("build.epub")
require_pdf_permission = PermissionDependencyFactory.create_permission_dependency("build.pdf")
require_backup_permission = PermissionDependencyFactory.create_permission_dependency("manual_backup")
require_content_edit_permission = PermissionDependencyFactory.create_permission_dependency("content.edit")
require_file_manage_permission = PermissionDependencyFactory.create_permission_dependency("file.manage")


# 便利函数
def get_permission_dependency(permission: str):
    """获取权限检查依赖的便利函数"""
    return PermissionDependencyFactory.create_permission_dependency(permission)

def get_file_permission_dependency(file_type: str):
    """获取文件权限检查依赖的便利函数"""
    return PermissionDependencyFactory.create_file_permission_dependency(file_type)