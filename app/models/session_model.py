"""
Session data models for MarkEdit application.

This module contains session-related data models and structures.
"""
from pydantic import BaseModel
from typing import Optional, List

class SessionData(BaseModel):
    """用户会话数据模型"""
    access_token: Optional[str] = None
    username: Optional[str] = None
    theme: Optional[str] = "default"
    user_type: Optional[str] = "user"  # 'admin', 'user'
    roles: List[str] = []  # 用户拥有的角色列表
    permissions: List[str] = []  # 用户拥有的权限列表
    last_permission_check: Optional[float] = None  # 最后一次权限检查时间

class OAuthConfig(BaseModel):
    """OAuth配置模型"""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    
    @property
    def is_configured(self) -> bool:
        """检查OAuth是否已配置"""
        return bool(self.client_id and self.client_secret and self.redirect_uri)

class AuthContext(BaseModel):
    """认证上下文模型"""
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    last_activity: Optional[float] = None