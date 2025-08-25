"""
Global state management utilities for MarkEdit application.

This module contains utility functions for managing global application state.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class GlobalStateManager:
    """全局状态管理器类"""
    
    def __init__(self):
        self._startup_backup_filename: Optional[str] = None
        self._app_config: Dict[str, Any] = {}
        self._base_dir = Path(__file__).resolve().parent.parent.parent
    
    def set_startup_backup_filename(self, filename: Optional[str]) -> None:
        """设置启动备份文件名"""
        self._startup_backup_filename = filename
        logger.info(f"启动备份文件名已设置: {filename}")
    
    def get_startup_backup_filename(self) -> Optional[str]:
        """获取启动备份文件名"""
        return self._startup_backup_filename
    
    def set_config_value(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._app_config[key] = value
        logger.debug(f"配置值已设置: {key} = {value}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._app_config.get(key, default)
    
    def update_config(self, config_dict: Dict[str, Any]) -> None:
        """批量更新配置"""
        self._app_config.update(config_dict)
        logger.debug(f"配置已批量更新: {len(config_dict)} 个配置项")
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._app_config.copy()
    
    def clear_config(self) -> None:
        """清空所有配置"""
        self._app_config.clear()
        logger.info("所有配置已清空")
    
    def get_base_directory(self) -> Path:
        """获取应用程序基础目录"""
        return self._base_dir
    
    def get_users_directory(self) -> Path:
        """获取用户目录基础路径"""
        return self._base_dir / "users"
    
    def get_src_directory(self) -> Path:
        """获取源代码目录路径"""
        return self._base_dir / "src"
    
    def get_build_directory(self) -> Path:
        """获取构建目录路径"""
        return self._base_dir / "build"
    
    def get_app_state_summary(self) -> Dict[str, Any]:
        """获取应用程序状态摘要"""
        return {
            "startup_backup_filename": self._startup_backup_filename,
            "config_items_count": len(self._app_config),
            "base_directory": str(self._base_dir),
            "users_directory": str(self.get_users_directory()),
            "src_directory": str(self.get_src_directory()),
            "build_directory": str(self.get_build_directory()),
            "directories_exist": {
                "users": self.get_users_directory().exists(),
                "src": self.get_src_directory().exists(),
                "build": self.get_build_directory().exists()
            }
        }
    
    def reset_state(self) -> None:
        """重置全局状态"""
        self._startup_backup_filename = None
        self._app_config.clear()
        logger.info("全局状态已重置")

# 创建全局状态管理器实例
global_state_manager = GlobalStateManager()

# 向后兼容的函数
def set_startup_backup_filename(filename: Optional[str]) -> None:
    """设置启动备份文件名（向后兼容）"""
    global_state_manager.set_startup_backup_filename(filename)

def get_startup_backup_filename() -> Optional[str]:
    """获取启动备份文件名（向后兼容）"""
    return global_state_manager.get_startup_backup_filename()

def set_config_value(key: str, value: Any) -> None:
    """设置配置值（向后兼容）"""
    global_state_manager.set_config_value(key, value)

def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值（向后兼容）"""
    return global_state_manager.get_config_value(key, default)

# 应用程序状态管理函数
def set_application_status(status: str) -> None:
    global_state_manager.set_config_value("application_status", status)
    logger.info(f"应用程序状态更新: {status}")

def get_application_status() -> str:
    """获取应用程序状态"""
    return global_state_manager.get_config_value("application_status", "unknown")

def set_database_status(status: str) -> None:
    """设置数据库状态"""
    global_state_manager.set_config_value("database_status", status)

def get_database_status() -> str:
    """获取数据库状态"""
    return global_state_manager.get_config_value("database_status", "unknown")

def set_startup_time(timestamp: float) -> None:
    """设置应用启动时间"""
    global_state_manager.set_config_value("startup_time", timestamp)

def get_startup_time() -> Optional[float]:
    """获取应用启动时间"""
    return global_state_manager.get_config_value("startup_time")

# 计数器管理函数
def increment_counter(counter_name: str) -> int:
    current_value = global_state_manager.get_config_value(counter_name, 0)
    new_value = current_value + 1
    global_state_manager.set_config_value(counter_name, new_value)
    return new_value

def get_counter_value(counter_name: str) -> int:
    """获取计数器值"""
    return global_state_manager.get_config_value(counter_name, 0)

def reset_counter(counter_name: str) -> None:
    """重置计数器"""
    global_state_manager.set_config_value(counter_name, 0)

def get_application_info() -> Dict[str, Any]:
    """获取应用程序信息摘要"""
    return {
        "startup_backup_filename": get_startup_backup_filename(),
        "application_status": get_application_status(),
        "database_status": get_database_status(),
        "startup_time": get_startup_time(),
        "total_states": len(global_state_manager.get_all_config())
    }

def cleanup_expired_state(max_age_seconds: int = 86400) -> int:
    """清理过期状态（基于时间戳的状态）"""
    import time
    current_time = time.time()
    
    all_states = global_state_manager.get_all_config()
    expired_keys = []
    
    for key, value in all_states.items():
        # 检查是否为时间戳类型的状态
        if key.endswith("_timestamp") and isinstance(value, (int, float)):
            if current_time - value > max_age_seconds:
                expired_keys.append(key)
    
    # 删除过期状态
    for key in expired_keys:
        global_state_manager.set_config_value(key, None)  # 清除值
    
    if expired_keys:
        logger.info(f"清理了 {len(expired_keys)} 个过期状态")
    
    return len(expired_keys)

# 特殊状态管理（用于维护兼容性）
class BackupState:
    """备份状态管理"""
    
    @staticmethod
    def set_startup_backup(filename: str) -> None:
        """设置启动备份文件名"""
        set_startup_backup_filename(filename)
        global_state_manager.set_config_value("last_backup_time", time.time())
    
    @staticmethod
    def get_backup_info() -> Dict[str, Any]:
        """获取备份信息"""
        return {
            "startup_backup_filename": get_startup_backup_filename(),
            "last_backup_time": global_state_manager.get_config_value("last_backup_time"),
            "backup_count": get_counter_value("backup_count")
        }
    
    @staticmethod
    def increment_backup_count() -> int:
        """递增备份计数"""
        return increment_counter("backup_count")