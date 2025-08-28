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
    # GitHub OAuth配置
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    github_redirect_uri: Optional[str] = None
    
    # Gmail OAuth配置
    gmail_client_id: Optional[str] = None
    gmail_client_secret: Optional[str] = None
    gmail_redirect_uri: Optional[str] = None
    
    # 向后兼容属性
    @property
    def client_id(self) -> Optional[str]:
        """GitHub client_id的向后兼容属性"""
        return self.github_client_id
    
    @property
    def client_secret(self) -> Optional[str]:
        """GitHub client_secret的向后兼容属性"""
        return self.github_client_secret
    
    @property
    def redirect_uri(self) -> Optional[str]:
        """GitHub redirect_uri的向后兼容属性"""
        return self.github_redirect_uri
    
    @property
    def is_configured(self) -> bool:
        """检查是否至少有一种OAuth已配置"""
        github_configured = bool(self.github_client_id and self.github_client_secret and self.github_redirect_uri)
        gmail_configured = bool(self.gmail_client_id and self.gmail_client_secret and self.gmail_redirect_uri)
        return github_configured or gmail_configured
    
    @property
    def is_github_configured(self) -> bool:
        """检查GitHub OAuth是否已配置"""
        return bool(self.github_client_id and self.github_client_secret and self.github_redirect_uri)
    
    @property
    def is_gmail_configured(self) -> bool:
        """检查Gmail OAuth是否已配置"""
        return bool(self.gmail_client_id and self.gmail_client_secret and self.gmail_redirect_uri)

class AuthContext(BaseModel):
    """认证上下文模型"""
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    last_activity: Optional[float] = None