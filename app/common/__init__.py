"""
Common module for MarkEdit application.

This module serves as a central hub for all shared components, dependencies, and utilities
to eliminate circular import issues throughout the application.

All modules should import from this common module instead of importing from each other directly.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Union
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from functools import wraps

# ==========================================
# Core imports - 核心导入
# ==========================================

# Configuration
from app.config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI

# Models
from app.models.session_model import SessionData, OAuthConfig, AuthContext
from app.models import (
    database, metadata, DATABASE_URL,
    user_table, role_table, permission_table, user_role_table, role_permission_table, admin_table
)

# ==========================================
# Common module imports - 通用模块导入
# ==========================================

# Service management
from app.common.services import (
    get_session_service, get_oauth_service, get_startup_service,
    get_admin_service, get_build_service, get_epub_service,
    get_file_service, get_user_service,
    get_global_state_manager, get_directory_manager,
    sessions
)

# Authentication functions
from app.common.auth import (
    get_session, require_auth_session, require_auth,
    check_user_permission, get_user_permissions, get_user_roles,
    assign_default_user_role, update_session_permissions,
    load_user_permissions_and_roles
)

# Authentication decorators
from app.common.decorators import (
    require_permission, require_role, require_admin, 
    require_super_admin, optional_auth
)

# Utility functions
from app.common.utils import (
    copy_default_files_to_user_directory, get_user_directory,
    ensure_user_directory_exists, get_user_src_directory,
    ensure_user_src_directory_exists, get_user_backup_directory,
    ensure_user_backup_directory_exists, is_user_authorized_for_directory,
    validate_username, set_startup_backup_filename, get_startup_backup_filename,
    set_config_value, get_config_value,
    scan_directory, read_text_file, read_image_file, save_text_file,
    delete_file_safely, create_file_safely, create_directory_safely,
    is_text_file, is_image_file, is_previewable_binary,
    create_file_response, create_static_file_response,
    generate_random_password, hash_password, verify_password,
    validate_json_and_parse, validate_theme_name
)

# ==========================================
# GitHub OAuth 配置（向后兼容）
# ==========================================

CLIENT_ID = GITHUB_CLIENT_ID
CLIENT_SECRET = GITHUB_CLIENT_SECRET
REDIRECT_URI = GITHUB_REDIRECT_URI

# ==========================================
# Exported symbols for backward compatibility
# ==========================================

__all__ = [
    # Core models
    'SessionData', 'OAuthConfig', 'AuthContext',
    # Database
    'database', 'metadata', 'DATABASE_URL',
    'user_table', 'role_table', 'permission_table', 
    'user_role_table', 'role_permission_table', 'admin_table',
    # Service getters
    'get_session_service', 'get_oauth_service', 'get_startup_service',
    'get_admin_service', 'get_build_service', 'get_epub_service',
    'get_file_service', 'get_user_service',
    # Utility getters
    'get_global_state_manager', 'get_directory_manager',
    # Authentication functions
    'get_session', 'require_auth_session', 'require_auth',
    'check_user_permission', 'get_user_permissions', 'get_user_roles',
    'assign_default_user_role', 'update_session_permissions',
    'load_user_permissions_and_roles',
    # Authentication decorators
    'require_permission', 'require_role', 'require_admin', 
    'require_super_admin', 'optional_auth',
    # Session management
    'sessions',
    # Utility functions
    'copy_default_files_to_user_directory', 'get_user_directory',
    'ensure_user_directory_exists', 'get_user_src_directory',
    'ensure_user_src_directory_exists', 'get_user_backup_directory',
    'ensure_user_backup_directory_exists', 'is_user_authorized_for_directory',
    'validate_username', 'set_startup_backup_filename', 'get_startup_backup_filename',
    'set_config_value', 'get_config_value',
    'scan_directory', 'read_text_file', 'read_image_file', 'save_text_file',
    'delete_file_safely', 'create_file_safely', 'create_directory_safely',
    'is_text_file', 'is_image_file', 'is_previewable_binary',
    'create_file_response', 'create_static_file_response',
    'generate_random_password', 'hash_password', 'verify_password',
    'validate_json_and_parse', 'validate_theme_name',
    # OAuth config (backward compatibility)
    'CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI'
]