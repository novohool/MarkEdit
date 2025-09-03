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
from app.services.base_service import BaseService
from app.services.auth_session_mixin import AuthSessionMixin

logger = logging.getLogger(__name__)

class SessionService(BaseService, AuthSessionMixin):
    """会话管理服务类"""
    
    def __init__(self):
        super().__init__()
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
    
    # 使用混入类的create_user_session方法
    def create_session(self, username: str, user_type: str = "user", theme: str = "default") -> str:
        """创建新的用户会话（使用混入类的实现）"""
        session_id = str(uuid.uuid4())
        session_data = SessionData(
            username=username,
            user_type=user_type,
            theme=theme,
            access_token=session_id
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
    
    # 权限检查、角色管理等方法现在通过AuthSessionMixin混入类提供
    # check_user_permission, get_user_permissions, get_user_roles 等方法
    # 已在 AuthSessionMixin 中实现
    
    async def assign_default_user_role(self, username: str):
        """为新用户自动分配默认角色（使用混入类的方法）"""
        try:
            # 根据用户名决定角色
            role_name = "user"  # 默认角色
            
            if username == "markedit":
                role_name = "super_admin"
                logger.info(f"为特殊用户 {username} 分配超管权限")
            elif username.endswith("_admin") or username in ["admin", "administrator"]:
                role_name = "admin"
                logger.info(f"为管理员用户 {username} 分配管理员权限")
            else:
                role_name = "user"
                logger.info(f"为普通用户 {username} 分配基础用户权限")
            
            # 使用混入类的方法分配角色
            success = await self.assign_role_to_user(username, role_name)
            
            if success:
                # 初始化用户（复制默认文件等）
                await self.initialize_new_user(username, role_name)
                
        except Exception as e:
            logger.error(f"为用户分配默认角色时出错: {str(e)}", exc_info=True)
    
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