"""
Authentication and session management mixin for MarkEdit application.

This module provides common functionality for authentication and session management
across different services, eliminating code duplication.
"""
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from fastapi import Request, HTTPException
from databases.core import Record

from app.common import (
    SessionData, AuthContext,
    database, user_table, admin_table, role_table, user_role_table, 
    permission_table, role_permission_table,
    get_session_service,
    generate_random_password, hash_password,
    copy_default_files_to_user_directory
)

logger = logging.getLogger(__name__)

class AuthenticationMixin:
    """认证混入类，提供统一的认证逻辑"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    async def authenticate_user(self, username: str, password: str, user_type: str = "auto") -> Optional[SessionData]:
        """统一的用户认证方法"""
        try:
            # 根据user_type决定查询哪个表
            if user_type == "admin":
                # 只查询管理员表
                query = admin_table.select().where(admin_table.c.username == username)
                user_record = await database.fetch_one(query)
                if not user_record:
                    return None
            elif user_type == "user":
                # 只查询用户表
                query = user_table.select().where(user_table.c.username == username)
                user_record = await database.fetch_one(query)
                if not user_record:
                    return None
            else:
                # 自动检测，先查管理员表，再查用户表
                admin_query = admin_table.select().where(admin_table.c.username == username)
                admin_record = await database.fetch_one(admin_query)
                
                if admin_record:
                    user_record = admin_record
                    user_type = "admin"
                else:
                    user_query = user_table.select().where(user_table.c.username == username)
                    user_record = await database.fetch_one(user_query)
                    user_type = "user"
                    
                    if not user_record:
                        return None
            
            # 验证密码（这里需要根据实际的密码验证逻辑）
            # TODO: 实现具体的密码验证逻辑
            
            # 创建会话数据
            theme = user_record.get("theme", "default") if user_type == "user" else "default"
            
            session_data = SessionData(
                username=username,
                user_type=user_type,
                theme=theme
            )
            
            # 更新会话的权限信息
            await self.update_session_permissions(session_data)
            
            return session_data
            
        except Exception as e:
            self.logger.error(f"用户认证失败: {str(e)}", exc_info=True)
            return None
    
    async def validate_session(self, request: Request, required_permissions: List[str] = None) -> SessionData:
        """验证会话并检查权限"""
        try:
            session_service = get_session_service()
            session = session_service.get_session(request)
            
            if not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            # 更新权限信息（缓存机制）
            session = await self.update_session_permissions(session)
            
            # 检查所需权限
            if required_permissions:
                for permission in required_permissions:
                    if not await self.check_user_permission(session.username, permission):
                        raise HTTPException(status_code=403, detail=f"缺少权限: {permission}")
            
            return session
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"会话验证失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=401, detail="认证失败")

class PermissionMixin:
    """权限混入类，提供统一的权限管理逻辑"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    async def check_user_permission(self, username: str, permission_name: str) -> bool:
        """检查用户是否具有特定权限"""
        try:
            # 特殊处理超管用户markedit
            if username == "markedit":
                # 超管用户拥有所有权限
                return True
            
            # 检查admin表中的用户（给予管理员权限）- 尝试多种用户名格式
            from app.common import admin_table
            admin_queries = [
                admin_table.select().where(admin_table.c.username == username),
                admin_table.select().where(admin_table.c.username == f"super_admin_{username}"),
                admin_table.select().where(admin_table.c.username == "super_admin_markedit")
            ]
            
            admin_record = None
            for query in admin_queries:
                admin_record = await database.fetch_one(query)
                if admin_record:
                    break
            
            if admin_record:
                # admin表中的用户拥有大部分管理权限
                admin_permissions = [
                    "admin_access", "user.list", "user.create", "user.edit", "user.delete",
                    "role.list", "role.create", "role.edit", "role.delete",
                    "permission.list", "permission.create", "permission.edit", "permission.delete",
                    "content.edit", "file.manage", "build.epub", "build.pdf", "build.html",
                    "epub_conversion", "manual_backup", "system.config", "theme_access"
                ]
                if permission_name in admin_permissions:
                    return True
            
            # 使用连接查询一次性获取用户权限信息
            query = (
                user_table.select()
                .select_from(
                    user_table.join(user_role_table, user_table.c.id == user_role_table.c.user_id)
                    .join(role_permission_table, user_role_table.c.role_id == role_permission_table.c.role_id)
                    .join(permission_table, role_permission_table.c.permission_id == permission_table.c.id)
                )
                .where(
                    (user_table.c.username == username) &
                    (permission_table.c.name == permission_name)
                )
            )
            
            result = await database.fetch_one(query)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"检查用户权限时出错: {str(e)}", exc_info=True)
            return False
    
    async def get_user_permissions(self, username: str) -> List[str]:
        """获取用户所有权限"""
        try:
            # 特殊处理超管用户markedit
            if username == "markedit":
                # 返回所有权限
                all_perms_query = permission_table.select()
                all_perms = await database.fetch_all(all_perms_query)
                return [perm["name"] for perm in all_perms]
            
            # 检查admin表中的用户 - 尝试多种用户名格式
            from app.common import admin_table
            admin_queries = [
                admin_table.select().where(admin_table.c.username == username),
                admin_table.select().where(admin_table.c.username == f"super_admin_{username}"),
                admin_table.select().where(admin_table.c.username == "super_admin_markedit")
            ]
            
            admin_record = None
            for query in admin_queries:
                admin_record = await database.fetch_one(query)
                if admin_record:
                    break
            
            if admin_record:
                # admin表中的用户拥有管理员权限
                return [
                    "admin_access", "user.list", "user.create", "user.edit", "user.delete",
                    "role.list", "role.create", "role.edit", "role.delete",
                    "permission.list", "permission.create", "permission.edit", "permission.delete",
                    "content.edit", "file.manage", "build.epub", "build.pdf", "build.html",
                    "epub_conversion", "manual_backup", "system.config", "theme_access"
                ]
            
            query = (
                permission_table.select()
                .select_from(
                    permission_table.join(role_permission_table, permission_table.c.id == role_permission_table.c.permission_id)
                    .join(user_role_table, role_permission_table.c.role_id == user_role_table.c.role_id)
                    .join(user_table, user_role_table.c.user_id == user_table.c.id)
                )
                .where(user_table.c.username == username)
            )
            
            results = await database.fetch_all(query)
            return [result["name"] for result in results]
            
        except Exception as e:
            self.logger.error(f"获取用户权限时出错: {str(e)}", exc_info=True)
            return []
    
    async def get_user_roles(self, username: str) -> List[str]:
        """获取用户所有角色"""
        try:
            # 特殊处理超管用户markedit
            if username == "markedit":
                return ["super_admin"]
            
            # 检查admin表中的用户 - 尝试多种用户名格式
            from app.common import admin_table
            admin_queries = [
                admin_table.select().where(admin_table.c.username == username),
                admin_table.select().where(admin_table.c.username == f"super_admin_{username}"),
                admin_table.select().where(admin_table.c.username == "super_admin_markedit")
            ]
            
            admin_record = None
            for query in admin_queries:
                admin_record = await database.fetch_one(query)
                if admin_record:
                    break
            
            if admin_record:
                return ["admin"]
            
            query = (
                role_table.select()
                .select_from(
                    role_table.join(user_role_table, role_table.c.id == user_role_table.c.role_id)
                    .join(user_table, user_role_table.c.user_id == user_table.c.id)
                )
                .where(user_table.c.username == username)
            )
            
            results = await database.fetch_all(query)
            return [result["name"] for result in results]
            
        except Exception as e:
            self.logger.error(f"获取用户角色时出错: {str(e)}", exc_info=True)
            return []
    
    async def assign_role_to_user(self, username: str, role_name: str) -> bool:
        """为用户分配角色"""
        try:
            # 获取用户ID
            user_query = user_table.select().where(user_table.c.username == username)
            user_record = await database.fetch_one(user_query)
            if not user_record:
                self.logger.error(f"用户 {username} 不存在")
                return False
            
            user_id = user_record["id"]
            
            # 获取角色ID
            role_query = role_table.select().where(role_table.c.name == role_name)
            role_record = await database.fetch_one(role_query)
            if not role_record:
                self.logger.error(f"角色 {role_name} 不存在")
                return False
            
            role_id = role_record["id"]
            
            # 检查是否已有角色分配
            check_query = user_role_table.select().where(
                (user_role_table.c.user_id == user_id) &
                (user_role_table.c.role_id == role_id)
            )
            existing_role = await database.fetch_one(check_query)
            
            if not existing_role:
                # 分配角色
                insert_query = user_role_table.insert().values(
                    user_id=user_id,
                    role_id=role_id
                )
                await database.execute(insert_query)
                self.logger.info(f"为用户 {username} 分配角色 {role_name} 成功")
                return True
            else:
                self.logger.info(f"用户 {username} 已有角色 {role_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"为用户分配角色时出错: {str(e)}", exc_info=True)
            return False
    
    async def remove_role_from_user(self, username: str, role_name: str) -> bool:
        """移除用户的角色"""
        try:
            # 获取用户ID和角色ID
            user_query = user_table.select().where(user_table.c.username == username)
            user_record = await database.fetch_one(user_query)
            if not user_record:
                return False
            
            role_query = role_table.select().where(role_table.c.name == role_name)
            role_record = await database.fetch_one(role_query)
            if not role_record:
                return False
            
            # 删除角色分配
            delete_query = user_role_table.delete().where(
                (user_role_table.c.user_id == user_record["id"]) &
                (user_role_table.c.role_id == role_record["id"])
            )
            await database.execute(delete_query)
            
            self.logger.info(f"移除用户 {username} 的角色 {role_name} 成功")
            return True
            
        except Exception as e:
            self.logger.error(f"移除用户角色时出错: {str(e)}", exc_info=True)
            return False

class SessionManagementMixin:
    """会话管理混入类，提供统一的会话管理逻辑"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    async def update_session_permissions(self, session: SessionData) -> SessionData:
        """更新会话中的权限信息"""
        if session.username:
            current_time = time.time()
            
            # 每5分钟更新一次权限信息，减少数据库查询
            if (session.last_permission_check is None or 
                current_time - session.last_permission_check > 300):
                
                session.roles = await self.get_user_roles(session.username)
                session.permissions = await self.get_user_permissions(session.username)
                session.last_permission_check = current_time
                
                # 获取用户类型
                query = user_table.select().where(user_table.c.username == session.username)
                user_info = await database.fetch_one(query)
                if user_info:
                    session.user_type = user_info.get("user_type", "user")
        
        return session
    
    async def create_user_session(self, username: str, user_type: str = "user", 
                                theme: str = "default") -> str:
        """创建新的用户会话"""
        session_id = str(uuid.uuid4())
        session_data = SessionData(
            username=username,
            user_type=user_type,
            theme=theme,
            access_token=session_id
        )
        
        # 更新权限信息
        await self.update_session_permissions(session_data)
        
        # 这里需要调用SessionService来存储会话
        session_service = get_session_service()
        session_service.sessions[session_id] = session_data
        
        self.logger.info(f"为用户 {username} 创建新会话: {session_id}")
        return session_id
    
    async def destroy_user_session(self, session_id: str) -> bool:
        """销毁用户会话"""
        try:
            session_service = get_session_service()
            return session_service.destroy_session(session_id)
        except Exception as e:
            self.logger.error(f"销毁会话失败: {str(e)}", exc_info=True)
            return False
    
    async def refresh_session_data(self, session: SessionData) -> SessionData:
        """刷新会话数据"""
        try:
            # 重新获取用户信息
            if session.user_type == "admin":
                query = admin_table.select().where(admin_table.c.username == session.username)
            else:
                query = user_table.select().where(user_table.c.username == session.username)
            
            user_record = await database.fetch_one(query)
            if user_record and session.user_type == "user":
                session.theme = user_record.get("theme", "default")
            
            # 更新权限信息
            await self.update_session_permissions(session)
            
            return session
            
        except Exception as e:
            self.logger.error(f"刷新会话数据失败: {str(e)}", exc_info=True)
            return session

# 组合混入类，提供完整的认证会话管理功能
class AuthSessionMixin(AuthenticationMixin, PermissionMixin, SessionManagementMixin):
    """组合的认证会话管理混入类，整合所有认证和会话管理功能"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def initialize_new_user(self, username: str, default_role: str = "user") -> bool:
        """初始化新用户，分配默认角色和复制默认文件"""
        try:
            # 分配默认角色
            success = await self.assign_role_to_user(username, default_role)
            if not success:
                self.logger.error(f"为新用户 {username} 分配默认角色失败")
                return False
            
            # 复制默认文件到用户目录
            try:
                copy_default_files_to_user_directory(username)
                self.logger.info(f"为新用户 {username} 复制默认文件成功")
            except Exception as e:
                self.logger.warning(f"为新用户 {username} 复制默认文件失败: {str(e)}")
                # 复制文件失败不影响用户创建
            
            return True
            
        except Exception as e:
            self.logger.error(f"初始化新用户失败: {str(e)}", exc_info=True)
            return False
    
    async def get_user_session_info(self, username: str) -> Dict[str, Any]:
        """获取用户的完整会话信息"""
        try:
            # 获取用户基本信息
            user_info = None
            user_type = "user"
            
            # 先检查管理员表
            admin_query = admin_table.select().where(admin_table.c.username == username)
            admin_record = await database.fetch_one(admin_query)
            
            if admin_record:
                user_info = admin_record
                user_type = "admin"
            else:
                # 检查用户表
                user_query = user_table.select().where(user_table.c.username == username)
                user_record = await database.fetch_one(user_query)
                if user_record:
                    user_info = user_record
                    user_type = "user"
            
            if not user_info:
                return {}
            
            # 获取角色和权限信息
            roles = await self.get_user_roles(username)
            permissions = await self.get_user_permissions(username)
            
            return {
                "username": username,
                "user_type": user_type,
                "theme": user_info.get("theme", "default") if user_type == "user" else "default",
                "roles": roles,
                "permissions": permissions,
                "created_at": user_info.get("created_at"),
                "login_time": user_info.get("login_time") if user_type == "user" else None
            }
            
        except Exception as e:
            self.logger.error(f"获取用户会话信息失败: {str(e)}", exc_info=True)
            return {}