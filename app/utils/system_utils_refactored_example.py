"""
Refactored system utilities for MarkEdit application (partial example).

This module demonstrates how parts of the original system_utils.py can be
simplified using the new base_utils infrastructure, focusing on the
formatting functions and error handling patterns.

Original system_utils.py: 493 lines
This refactored portion would reduce formatting-related code by ~40%.
"""
import logging
from typing import Dict, Any, Union, Optional
from pathlib import Path

from .base_utils import (
    ExceptionHandler, FormatUtils, ValidationUtils
)

logger = logging.getLogger(__name__)

class SystemUtilsRefactored:
    """重构后的系统工具类，展示如何减少重复代码"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.src_dir = self.base_dir / "src"
        self.build_dir = self.base_dir / "build"
    
    @ExceptionHandler.handle_system_error("获取目录信息")
    def get_directory_info(self, directory_path: Union[str, Path]) -> Dict[str, Any]:
        """获取目录信息（使用统一的异常处理）"""
        if isinstance(directory_path, str):
            directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not directory_path.is_dir():
            raise ValueError(f"路径不是目录: {directory_path}")
        
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in directory_path.rglob("*"):
            if item.is_file():
                file_count += 1
                total_size += item.stat().st_size
            elif item.is_dir():
                dir_count += 1
        
        return {
            "path": str(directory_path),
            "exists": True,
            "total_size": total_size,
            "total_size_formatted": FormatUtils.format_bytes(total_size),
            "file_count": file_count,
            "directory_count": dir_count,
            "last_modified": FormatUtils.format_timestamp(directory_path.stat().st_mtime)
        }
    
    @ExceptionHandler.handle_system_error("获取文件统计")
    def get_file_statistics(self, directory_path: Union[str, Path]) -> Dict[str, Any]:
        """获取文件统计信息（使用统一的格式化工具）"""
        if isinstance(directory_path, str):
            directory_path = Path(directory_path)
        
        stats = {
            "total_files": 0,
            "total_size": 0,
            "file_types": {},
            "size_distribution": {
                "small": 0,    # < 1MB
                "medium": 0,   # 1MB - 10MB  
                "large": 0,    # 10MB - 100MB
                "huge": 0      # > 100MB
            }
        }
        
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                stats["total_files"] += 1
                
                file_size = file_path.stat().st_size
                stats["total_size"] += file_size
                
                # 文件类型统计
                extension = file_path.suffix.lower() or "无扩展名"
                if extension not in stats["file_types"]:
                    stats["file_types"][extension] = {"count": 0, "size": 0}
                stats["file_types"][extension]["count"] += 1
                stats["file_types"][extension]["size"] += file_size
                
                # 大小分布统计
                if file_size < 1024 * 1024:  # < 1MB
                    stats["size_distribution"]["small"] += 1
                elif file_size < 10 * 1024 * 1024:  # < 10MB
                    stats["size_distribution"]["medium"] += 1
                elif file_size < 100 * 1024 * 1024:  # < 100MB
                    stats["size_distribution"]["large"] += 1
                else:
                    stats["size_distribution"]["huge"] += 1
        
        # 格式化文件类型大小
        for ext_info in stats["file_types"].values():
            ext_info["size_formatted"] = FormatUtils.format_bytes(ext_info["size"])
        
        # 格式化总大小
        stats["total_size_formatted"] = FormatUtils.format_bytes(stats["total_size"])
        
        return stats
    
    @ExceptionHandler.handle_system_error("清理临时文件")
    def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """清理临时文件（使用统一的异常处理和格式化）"""
        import time
        
        temp_patterns = ["*.tmp", "*.temp", "*.bak", "*~"]
        cleaned_files = []
        total_freed_space = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for pattern in temp_patterns:
            for temp_file in self.base_dir.rglob(pattern):
                try:
                    if temp_file.is_file():
                        file_age = current_time - temp_file.stat().st_mtime
                        if file_age > max_age_seconds:
                            file_size = temp_file.stat().st_size
                            temp_file.unlink()
                            cleaned_files.append({
                                "path": str(temp_file),
                                "size": file_size,
                                "size_formatted": FormatUtils.format_bytes(file_size),
                                "age": FormatUtils.format_duration(file_age)
                            })
                            total_freed_space += file_size
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {temp_file}, 错误: {str(e)}")
        
        return {
            "cleaned_files_count": len(cleaned_files),
            "cleaned_files": cleaned_files,
            "total_freed_space": total_freed_space,
            "total_freed_space_formatted": FormatUtils.format_bytes(total_freed_space),
            "max_age_hours": max_age_hours
        }

# 独立的格式化函数（使用base_utils）
def format_file_size(size: Union[int, float]) -> str:
    """格式化文件大小（向后兼容）"""
    return FormatUtils.format_bytes(size)

def format_time_duration(seconds: Union[int, float]) -> str:
    """格式化时间持续时间（向后兼容）"""
    return FormatUtils.format_duration(seconds)

def format_system_timestamp(timestamp: Union[int, float], 
                           format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化系统时间戳（向后兼容）"""
    return FormatUtils.format_timestamp(timestamp, format_str)

def validate_system_path(path: str) -> bool:
    """验证系统路径（使用统一的验证工具）"""
    return ValidationUtils.validate_file_path(path)

"""
重构效果对比 - 格式化和工具函数部分：

原始代码问题：
- format_bytes 和 format_duration 函数有重复的错误处理模式
- 每个函数都有独立的异常捕获和日志记录
- 缺乏统一的格式化标准
- 硬编码的格式化逻辑

重构后的优势：
1. **代码重复减少**: 消除了重复的异常处理和格式化逻辑
2. **统一的错误处理**: 使用ExceptionHandler装饰器统一处理异常
3. **可复用的格式化工具**: FormatUtils提供标准化的格式化方法
4. **更好的错误信息**: 统一的错误消息格式和日志记录
5. **向后兼容**: 保持原有接口不变
6. **功能增强**: 新增的验证和清理功能

预估效果：
- 格式化相关代码减少40-50%
- 异常处理代码减少80%+  
- 日志记录标准化100%
- 新增功能无需重复实现基础逻辑

这个示例展示了如何通过base_utils大幅简化原有的system_utils.py中的
格式化函数和工具方法，同时提供更好的错误处理和功能扩展。
"""