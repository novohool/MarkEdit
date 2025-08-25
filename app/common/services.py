"""
Service instance management module for MarkEdit application.

This module provides delayed loading of service instances to avoid circular imports.
All service instances are accessed through getter functions.
"""

# ==========================================
# Service instances - 服务实例
# ==========================================

# 延迟初始化的服务实例
_session_service = None
_oauth_service = None
_startup_service = None
_admin_service = None
_build_service = None
_epub_service = None
_file_service = None
_user_service = None
# auth_service 已经迁移到 startup_service，不再使用
_auth_service = None

def get_session_service():
    """获取会话服务实例（延迟加载）"""
    global _session_service
    if _session_service is None:
        from app.services.session_service import session_service
        _session_service = session_service
    return _session_service

def get_oauth_service():
    """获取OAuth服务实例（延迟加载）"""
    global _oauth_service
    if _oauth_service is None:
        from app.services.oauth_service import oauth_service
        _oauth_service = oauth_service
    return _oauth_service

def get_startup_service():
    """获取启动服务实例（延迟加载）"""
    global _startup_service
    if _startup_service is None:
        from app.services.startup_service import StartupService
        _startup_service = StartupService()
    return _startup_service

def get_admin_service():
    """获取管理员服务实例（延迟加载）"""
    global _admin_service
    if _admin_service is None:
        from app.services.admin_service import AdminService
        _admin_service = AdminService()
    return _admin_service

def get_build_service():
    """获取构建服务实例（延迟加载）"""
    global _build_service
    if _build_service is None:
        from app.services.build_service import BuildService
        _build_service = BuildService()
    return _build_service

def get_epub_service():
    """获取EPUB服务实例（延迟加载）"""
    global _epub_service
    if _epub_service is None:
        from app.services.epub_service import EpubService
        _epub_service = EpubService()
    return _epub_service

def get_file_service():
    """获取文件服务实例（延迟加载）"""
    global _file_service
    if _file_service is None:
        from pathlib import Path
        from app.services.file_service import FileService
        base_dir = Path(__file__).resolve().parent.parent.parent
        _file_service = FileService(base_dir)
    return _file_service

def get_user_service():
    """获取用户服务实例（延迟加载）"""
    global _user_service
    if _user_service is None:
        from app.services.user_service import UserService
        _user_service = UserService()
    return _user_service

# get_auth_service 已经迁移到 startup_service，不再使用

# ==========================================
# Utility managers - 工具管理器
# ==========================================

_global_state_manager = None
_directory_manager = None

def get_global_state_manager():
    """获取全局状态管理器（延迟加载）"""
    global _global_state_manager
    if _global_state_manager is None:
        from app.utils.global_state import global_state_manager
        _global_state_manager = global_state_manager
    return _global_state_manager

def get_directory_manager():
    """获取目录管理器（延迟加载）"""
    global _directory_manager
    if _directory_manager is None:
        from app.utils.directory_utils import directory_manager
        _directory_manager = directory_manager
    return _directory_manager

# ==========================================
# Session management - 会话管理
# ==========================================

class SessionsProxy:
    """会话代理类，避免循环导入"""
    @property
    def sessions(self):
        return get_session_service().sessions

# 创建代理实例
sessions = SessionsProxy()