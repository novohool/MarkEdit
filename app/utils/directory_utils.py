"""
Directory management utilities for MarkEdit application.

This module contains utility functions for directory and user workspace management.
"""
import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class DirectoryManager:
    """目录管理器类"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.users_dir = self.base_dir / "users"
        self.global_src_dir = self.base_dir / "src"
    
    def validate_username(self, username: str) -> bool:
        """验证用户名是否合法"""
        # 基本格式验证：3-50个字符，只包含字母、数字和下划线
        if not username or len(username) < 3 or len(username) > 50:
            return False
        if not username.replace('_', '').isalnum():
            return False
        # 安全性检查：防止路径遍历攻击
        if re.search(r'[\/\\\.\0]', username):
            return False
        return True
    
    def get_user_directory(self, username: str) -> Path:
        """获取指定用户的目录路径"""
        if not self.validate_username(username):
            raise ValueError("用户名不合法")
        return self.users_dir / username
    
    def ensure_user_directory_exists(self, username: str) -> Path:
        """确保用户目录存在，如果不存在则创建"""
        user_dir = self.get_user_directory(username)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def get_user_src_directory(self, username: str) -> Path:
        """获取指定用户的src目录路径"""
        return self.ensure_user_directory_exists(username) / "src"
    
    def ensure_user_src_directory_exists(self, username: str) -> Path:
        """确保用户src目录存在，如果不存在则创建"""
        user_src_dir = self.get_user_src_directory(username)
        user_src_dir.mkdir(parents=True, exist_ok=True)
        return user_src_dir
    
    def get_user_backup_directory(self, username: str) -> Path:
        """获取指定用户的备份目录路径"""
        return self.ensure_user_directory_exists(username) / "backup"
    
    def ensure_user_backup_directory_exists(self, username: str) -> Path:
        """确保用户备份目录存在，如果不存在则创建"""
        user_backup_dir = self.get_user_backup_directory(username)
        user_backup_dir.mkdir(parents=True, exist_ok=True)
        return user_backup_dir
    
    def is_user_authorized_for_directory(self, username: str, directory: Path) -> bool:
        """检查用户是否有权访问指定目录"""
        try:
            user_dir = self.get_user_directory(username).resolve()
            target_dir = directory.resolve()
            # 检查目标目录是否在用户目录下
            return target_dir.is_relative_to(user_dir)
        except (ValueError, OSError):
            return False
    
    def copy_default_files_to_user_directory(self, username: str) -> None:
        """将默认文件从全局src目录复制到用户的src目录"""
        # 获取用户的src目录
        user_src_dir = self.get_user_src_directory(username)
        
        # 检查用户的src目录是否是新创建的（不存在）
        if not user_src_dir.exists():
            # 创建用户的src目录
            user_src_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"为用户 {username} 创建了新的src目录: {user_src_dir}")
            
            # 复制全局src目录中的所有文件和子目录到用户的src目录
            if self.global_src_dir.exists():
                shutil.copytree(self.global_src_dir, user_src_dir, dirs_exist_ok=True)
                logger.info(f"已将公共src目录的文件复制到用户 {username} 的src目录")
            else:
                logger.warning(f"公共src目录不存在: {self.global_src_dir}")
        else:
            logger.info(f"用户 {username} 的src目录已存在: {user_src_dir}")
    
    def get_user_workspace_info(self, username: str) -> dict:
        """获取用户工作空间信息"""
        try:
            user_dir = self.get_user_directory(username)
            user_src_dir = self.get_user_src_directory(username)
            
            info = {
                "username": username,
                "user_directory": str(user_dir),
                "src_directory": str(user_src_dir),
                "user_dir_exists": user_dir.exists(),
                "src_dir_exists": user_src_dir.exists(),
                "is_valid_username": self.validate_username(username)
            }
            
            if user_src_dir.exists():
                # 统计文件信息
                total_files = 0
                total_dirs = 0
                total_size = 0
                
                for item in user_src_dir.rglob('*'):
                    if item.is_file():
                        total_files += 1
                        try:
                            total_size += item.stat().st_size
                        except (OSError, PermissionError):
                            pass
                    elif item.is_dir():
                        total_dirs += 1
                
                info.update({
                    "total_files": total_files,
                    "total_directories": total_dirs,
                    "total_size_bytes": total_size
                })
            
            return info
            
        except Exception as e:
            logger.error(f"获取用户工作空间信息失败: {str(e)}")
            return {
                "username": username,
                "error": str(e),
                "is_valid_username": self.validate_username(username)
            }
    
    def cleanup_user_directory(self, username: str, keep_src: bool = True) -> bool:
        """清理用户目录"""
        try:
            user_dir = self.get_user_directory(username)
            
            if not user_dir.exists():
                logger.info(f"用户目录不存在: {user_dir}")
                return True
            
            if keep_src:
                # 保留src目录，删除其他内容
                for item in user_dir.iterdir():
                    if item.name != "src":
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                logger.info(f"清理用户目录（保留src）: {user_dir}")
            else:
                # 删除整个用户目录
                shutil.rmtree(user_dir)
                logger.info(f"完全删除用户目录: {user_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"清理用户目录失败: {str(e)}")
            return False
    
    def get_directory_size(self, directory: Path) -> int:
        """获取目录大小（字节）"""
        total_size = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        pass
        except Exception as e:
            logger.error(f"计算目录大小失败: {str(e)}")
        
        return total_size
    
    def list_user_directories(self) -> list:
        """列出所有用户目录"""
        users = []
        try:
            if self.users_dir.exists():
                for item in self.users_dir.iterdir():
                    if item.is_dir() and self.validate_username(item.name):
                        users.append({
                            "username": item.name,
                            "directory": str(item),
                            "size_bytes": self.get_directory_size(item)
                        })
        except Exception as e:
            logger.error(f"列出用户目录失败: {str(e)}")
        
        return users

# 创建全局目录管理器实例
directory_manager = DirectoryManager()