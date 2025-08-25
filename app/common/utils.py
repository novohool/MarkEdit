"""
Utility functions module for MarkEdit application.

This module provides common utility functions for directory management,
global state management, and other shared functionality.
"""
from pathlib import Path
from typing import Any, Optional

# File operations
from app.utils.file_utils import (
    scan_directory, read_text_file, read_image_file, save_text_file,
    delete_file_safely, create_file_safely, create_directory_safely,
    is_text_file, is_image_file, is_previewable_binary
)

# Response utils
from app.utils.response_utils import (
    create_file_response, create_static_file_response
)

# Crypto utils
from app.utils.crypto_utils import (
    generate_random_password, hash_password, verify_password
)

# Validation utils
from app.utils.validation_utils import (
    validate_json_and_parse, validate_theme_name
)


def copy_default_files_to_user_directory(username: str):
    """复制默认文件到用户目录"""
    from app.common.services import get_directory_manager
    return get_directory_manager().copy_default_files_to_user_directory(username)

def get_user_directory(username: str) -> Path:
    """获取用户目录路径"""
    from app.common.services import get_directory_manager
    return get_directory_manager().get_user_directory(username)

def ensure_user_directory_exists(username: str) -> Path:
    """确保用户目录存在"""
    from app.common.services import get_directory_manager
    return get_directory_manager().ensure_user_directory_exists(username)

def get_user_src_directory(username: str) -> Path:
    """获取用户源文件目录路径"""
    from app.common.services import get_directory_manager
    return get_directory_manager().get_user_src_directory(username)

def ensure_user_src_directory_exists(username: str) -> Path:
    """确保用户源文件目录存在"""
    from app.common.services import get_directory_manager
    return get_directory_manager().ensure_user_src_directory_exists(username)

def get_user_backup_directory(username: str) -> Path:
    """获取用户备份目录路径"""
    from app.common.services import get_directory_manager
    return get_directory_manager().get_user_backup_directory(username)

def ensure_user_backup_directory_exists(username: str) -> Path:
    """确保用户备份目录存在"""
    from app.common.services import get_directory_manager
    return get_directory_manager().ensure_user_backup_directory_exists(username)

def is_user_authorized_for_directory(username: str, directory_path: str) -> bool:
    """检查用户是否有权限访问指定目录"""
    from app.common.services import get_directory_manager
    return get_directory_manager().is_user_authorized_for_directory(username, directory_path)

def validate_username(username: str) -> bool:
    """验证用户名格式"""
    from app.common.services import get_directory_manager
    return get_directory_manager().validate_username(username)

def set_startup_backup_filename(filename: str):
    """设置启动备份文件名"""
    from app.common.services import get_global_state_manager
    return get_global_state_manager().set_startup_backup_filename(filename)

def get_startup_backup_filename() -> Optional[str]:
    """获取启动备份文件名"""
    from app.common.services import get_global_state_manager
    return get_global_state_manager().get_startup_backup_filename()

def set_config_value(key: str, value: Any):
    """设置配置值"""
    from app.common.services import get_global_state_manager
    return get_global_state_manager().set_config_value(key, value)

def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值"""
    from app.common.services import get_global_state_manager
    return get_global_state_manager().get_config_value(key, default)