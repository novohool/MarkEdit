# 共享模块，用于存储全局变量和提供共享功能
from pathlib import Path
import os
import re
import shutil

# 全局变量存储启动备份文件名
startup_backup_filename = None

# 用户目录基础路径
USERS_DIR = Path(__file__).resolve().parent.parent / "users"

def set_startup_backup_filename(filename):
    """设置启动备份文件名"""
    global startup_backup_filename
    startup_backup_filename = filename

def get_startup_backup_filename():
    """获取启动备份文件名"""
    return startup_backup_filename

def validate_username(username: str) -> bool:
    """验证用户名是否合法"""
    if not username:
        return False
    # 检查用户名是否包含非法字符（路径遍历字符等）
    if re.search(r'[\/\\\.\0]', username):
        return False
    return True

def get_user_directory(username: str) -> Path:
    """获取指定用户的目录路径"""
    if not validate_username(username):
        raise ValueError("用户名不合法")
    return USERS_DIR / username

def ensure_user_directory_exists(username: str) -> Path:
    """确保用户目录存在，如果不存在则创建"""
    user_dir = get_user_directory(username)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def get_user_src_directory(username: str) -> Path:
    """获取指定用户的src目录路径"""
    return ensure_user_directory_exists(username) / "src"

def ensure_user_src_directory_exists(username: str) -> Path:
    """确保用户src目录存在，如果不存在则创建"""
    user_src_dir = get_user_src_directory(username)
    user_src_dir.mkdir(parents=True, exist_ok=True)
    return user_src_dir

def is_user_authorized_for_directory(username: str, directory: Path) -> bool:
    """检查用户是否有权访问指定目录"""
    try:
        user_dir = get_user_directory(username).resolve()
        target_dir = directory.resolve()
        # 检查目标目录是否在用户目录下
        return target_dir.is_relative_to(user_dir)
    except (ValueError, OSError):
        return False

def copy_default_files_to_user_directory(username: str) -> None:
    """将默认文件从全局src目录复制到用户的src目录"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 获取全局src目录
    global_src_dir = Path(__file__).resolve().parent.parent / "src"
    
    # 获取用户的src目录
    user_src_dir = get_user_src_directory(username)
    
    # 检查用户的src目录是否是新创建的（不存在）
    if not user_src_dir.exists():
        # 创建用户的src目录
        user_src_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"为用户 {username} 创建了新的src目录: {user_src_dir}")
        
        # 复制全局src目录中的所有文件和子目录到用户的src目录
        if global_src_dir.exists():
            shutil.copytree(global_src_dir, user_src_dir, dirs_exist_ok=True)
            logger.info(f"已将公共src目录的文件复制到用户 {username} 的src目录")
        else:
            logger.warning(f"公共src目录不存在: {global_src_dir}")
    else:
        logger.info(f"用户 {username} 的src目录已存在: {user_src_dir}")