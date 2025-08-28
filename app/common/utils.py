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

def generate_user_illustration_path(username: str, filename: str) -> str:
    """生成包含用户前缀的插图路径。
    
    Args:
        username: 系统用户名（已包含前缀，如github_aaa或gmail_bbb）
        filename: 文件名（如chapter_01.svg）
    
    Returns:
        包含用户前缀的路径（如/user-illustrations/github_aaa/chapter_01.svg）
    """
    return f"/user-illustrations/{username}/{filename}"

def get_username_prefix(username: str) -> str:
    """从系统用户名中提取前缀。
    
    Args:
        username: 系统用户名（如github_aaa、gmail_bbb或super_admin_markedit）
    
    Returns:
        前缀字符串（如'github'、'gmail'或'super_admin'），无前缀则返回''
    """
    if username.startswith('super_admin_'):
        return 'super_admin'
    elif username.startswith('github_'):
        return 'github'
    elif username.startswith('gmail_'):
        return 'gmail'
    else:
        return ''

def get_original_username(username: str) -> str:
    """从系统用户名中提取原始用户名。
    
    Args:
        username: 系统用户名（如github_aaa、gmail_bbb或super_admin_markedit）
    
    Returns:
        原始用户名（如'aaa'、'bbb'或'markedit'）
    """
    if username.startswith('super_admin_'):
        return username[12:]  # 去掉'super_admin_'前缀
    elif username.startswith('github_'):
        return username[7:]  # 去掉'github_'前缀
    elif username.startswith('gmail_'):
        return username[6:]  # 去掉'gmail_'前缀
    else:
        return username