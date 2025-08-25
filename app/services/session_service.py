"""
Session management service for MarkEdit application.

This module contains business logic for session management including:
- Session creation and management
- Permission checking
- User role management
- Session data updates
"""
import logging
import time
import uuid
from typing import Dict, List, Optional
from fastapi import Request

from app.common import (
    SessionData, AuthContext,
    database, user_table, role_table, user_role_table, permission_table, role_permission_table,
    copy_default_files_to_user_directory
)

logger = logging.getLogger(__name__)

class SessionService:
    """会话管理服务类"""
    
    def __init__(self):
        # 存储会话信息（实际生产环境建议用Redis等）
        self.sessions: Dict[str, SessionData] = {}
    
    def get_session(self, request: Request) -> SessionData:
        """获取当前会话数据"""
        session_id = request.cookies.get("session_id")
        if not session_id:
            # 如果没有session_id，创建一个新的
            session_id = str(uuid.uuid4())
            # 设置临时会话数据
            self.sessions[session_id] = SessionData()
            # 在响应中设置cookie
            request.state.new_session_id = session_id
        elif session_id not in self.sessions:
            self.sessions[session_id] = SessionData()
        return self.sessions[session_id]
    
    def create_session(self, username: str, user_type: str = "user", theme: str = "default") -> str:
        """创建新的用户会话"""
        session_id = str(uuid.uuid4())
        session_data = SessionData(
            username=username,
            user_type=user_type,
            theme=theme,
            access_token=session_id  # 暂时使用session_id作为token
        )
        self.sessions[session_id] = session_data
        logger.info(f"为用户 {username} 创建新会话: {session_id}")
        return session_id
    
    def destroy_session(self, session_id: str) -> bool:
        """销毁会话"""
        if session_id in self.sessions:
            username = self.sessions[session_id].username
            del self.sessions[session_id]
            logger.info(f"销毁用户 {username} 的会话: {session_id}")
            return True
        return False
    
    def get_session_by_id(self, session_id: str) -> Optional[SessionData]:
        """根据session_id获取会话数据"""
        return self.sessions.get(session_id)
    
    async def check_user_permission(self, username: str, permission_name: str) -> bool:
        """检查用户是否具有特定权限"""
        try:
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
            
            # 执行查询
            result = await database.fetch_one(query)
            
            # 如果查询结果存在，说明用户具有该权限
            return result is not None
        except Exception as e:
            logger.error(f"检查用户权限时出错: {str(e)}", exc_info=True)
            return False
    
    async def get_user_permissions(self, username: str) -> List[str]:
        """获取用户所有权限"""
        try:
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
            logger.error(f"获取用户权限时出错: {str(e)}", exc_info=True)
            return []
    
    async def get_user_roles(self, username: str) -> List[str]:
        """获取用户所有角色"""
        try:
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
            logger.error(f"获取用户角色时出错: {str(e)}", exc_info=True)
            return []
    
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
                    session.user_type = user_info["user_type"] if user_info["user_type"] else "user"
        
        return session
    
    async def assign_default_user_role(self, username: str):
        """为新用户自动分配默认角色"""
        try:
            # 获取用户信息
            query = user_table.select().where(user_table.c.username == username)
            user_info = await database.fetch_one(query)
            
            if not user_info:
                logger.error(f"用户 {username} 不存在，无法分配角色")
                return
            
            user_id = user_info["id"]
            
            # 检查用户是否已有角色
            query = user_role_table.select().where(user_role_table.c.user_id == user_id)
            existing_roles = await database.fetch_all(query)
            
            if existing_roles:
                logger.info(f"用户 {username} 已有角色，跳过自动分配")
                return
            
            # 根据用户名决定分配的角色
            role_name = "user"  # 默认角色
            
            if username == "markedit":
                role_name = "super_admin"  # markedit用户获得超管权限
                logger.info(f"为特殊用户 {username} 分配超管权限")
            elif username.endswith("_admin") or username in ["admin", "administrator"]:
                role_name = "admin"  # 管理员用户
                logger.info(f"为管理员用户 {username} 分配管理员权限")
            else:
                # 为所有其他用户（包括GitHub登录用户）分配充分的普通用户权限
                role_name = "user"
                logger.info(f"为普通用户 {username} 分配基础用户权限（包含内容编辑、备份、EPUB转换等权限）")
            
            # 获取角色ID
            query = role_table.select().where(role_table.c.name == role_name)
            role_info = await database.fetch_one(query)
            
            if not role_info:
                logger.error(f"角色 {role_name} 不存在，无法分配")
                return
            
            role_id = role_info["id"]
            
            # 分配角色给用户
            query = user_role_table.insert().values(
                user_id=user_id,
                role_id=role_id
            )
            await database.execute(query)
            
            logger.info(f"成功为用户 {username} 分配角色 {role_name}")
            
        except Exception as e:
            logger.error(f"为用户 {username} 分配角色时出错: {str(e)}", exc_info=True)
    
    async def load_user_permissions_and_roles(self, session: SessionData):
        """加载用户权限和角色到会话中"""
        if session.username:
            try:
                session.roles = await self.get_user_roles(session.username)
                session.permissions = await self.get_user_permissions(session.username)
                
                # 获取用户类型和主题
                query = user_table.select().where(user_table.c.username == session.username)
                user_info = await database.fetch_one(query)
                if user_info:
                    session.user_type = user_info["user_type"] if user_info["user_type"] else "user"
                    session.theme = user_info["theme"] if user_info["theme"] else "default"
                
                logger.info(f"为用户 {session.username} 加载了 {len(session.permissions)} 个权限")
            except Exception as e:
                logger.error(f"加载用户权限和角色时出错: {str(e)}", exc_info=True)
    
    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        return len(self.sessions)
    
    def get_sessions_by_user(self, username: str) -> List[str]:
        """获取指定用户的所有会话ID"""
        session_ids = []
        for session_id, session_data in self.sessions.items():
            if session_data.username == username:
                session_ids.append(session_id)
        return session_ids
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 86400):
        """清理过期会话（默认24小时）"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if (session_data.last_permission_check and 
                current_time - session_data.last_permission_check > max_age_seconds):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.destroy_session(session_id)
        
        if expired_sessions:
            logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
        
        return len(expired_sessions)
    
    def require_auth(self, request: Request, session: SessionData) -> SessionData:
        """检查用户是否已登录，未登录则重定向到登录页"""
        from fastapi import HTTPException
        from fastapi.responses import RedirectResponse
        
        if not session.username:
            # 如果用户未登录，抛出重定向异常
            # 这里使用HTTPException而不是直接返回RedirectResponse
            # 因为这是作为依赖项使用的
            raise HTTPException(
                status_code=307,  # 临时重定向
                detail="需要登录",
                headers={"Location": "/login"}
            )
        
        return session
    
    async def require_auth_session(self, request: Request) -> SessionData:
        """异步版本的认证检查依赖项"""
        from fastapi import HTTPException
        
        session = self.get_session(request)
        
        if not session.username:
            # 如果用户未登录，抛出重定向异常
            raise HTTPException(
                status_code=307,  # 临时重定向
                detail="需要登录",
                headers={"Location": "/login"}
            )
        
        # 更新会话权限信息
        await self.update_session_permissions(session)
        
        return session

# 创建全局会话服务实例
session_service = SessionService()