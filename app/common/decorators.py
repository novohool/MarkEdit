"""
Authentication decorators module for MarkEdit application.

This module provides decorators for authentication and permission checking.
"""
# 直接从 utils.auth_decorators 导入实现，避免代码重复
from app.utils.auth_decorators import (
    require_permission,
    require_role,
    require_admin,
    require_super_admin,
    optional_auth,
    require_auth_session
)