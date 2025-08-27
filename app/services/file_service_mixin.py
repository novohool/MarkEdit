"""
File service mixin for MarkEdit application.

This module provides common file operation functionality that can be mixed into
other service classes to reduce code duplication.
"""
import os
import json
import zipfile
import logging
import datetime
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from app.utils.file_utils import is_text_file
from app.common import (
    get_user_backup_directory, ensure_user_backup_directory_exists,
    get_user_src_directory, copy_default_files_to_user_directory
)

logger = logging.getLogger(__name__)

class FileOperationMixin:
    """文件操作混入类，提供通用的文件处理功能"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_file_path(self, file_path: Union[str, Path], 
                          allowed_paths: Dict[str, Path] = None) -> Path:
        """验证文件路径是否安全且被允许"""
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        # 检查路径是否在允许列表中
        if allowed_paths:
            file_name = file_path.name
            if file_name not in allowed_paths:
                raise ValueError(f"文件访问被拒绝: {file_name}")
            return allowed_paths[file_name]
        
        # 基本的路径安全检查
        try:
            # 解析相对路径并检查是否安全
            resolved_path = file_path.resolve()
            return resolved_path
        except Exception as e:
            raise ValueError(f"无效的文件路径: {str(e)}")
    
    async def read_file_content(self, file_path: Path, 
                               encodings: List[str] = None) -> Dict[str, Any]:
        """读取文件内容，支持多种编码"""
        if encodings is None:
            encodings = ['utf-8', 'gbk', 'latin-1']
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")
        
        # 检查是否为文本文件
        if is_text_file(file_path):
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    return {
                        "content": content, 
                        "type": "text", 
                        "encoding": encoding,
                        "size": file_path.stat().st_size
                    }
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败
            return {
                "content": "无法解码此文本文件", 
                "type": "text", 
                "encoding": "unknown",
                "size": file_path.stat().st_size
            }
        else:
            # 二进制文件
            return {
                "content": "Binary file", 
                "type": "binary",
                "size": file_path.stat().st_size
            }
    
    async def save_file_content(self, file_path: Path, content: str, 
                               content_type: str = None, 
                               backup: bool = True) -> Dict[str, str]:
        """保存文件内容，支持备份和格式化"""
        try:
            # 创建备份（如果需要且文件存在）
            backup_path = None
            if backup and file_path.exists():
                backup_path = self._create_file_backup(file_path)
            
            # 处理特殊内容类型
            if content_type and 'application/json' in content_type:
                content = self._format_json_content(content)
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result = {
                "status": "success", 
                "message": f"文件 {file_path.name} 保存成功",
                "file_path": str(file_path)
            }
            
            if backup_path:
                result["backup_path"] = str(backup_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}", exc_info=True)
            raise Exception(f"保存文件失败: {str(e)}")
    
    def _create_file_backup(self, file_path: Path) -> Path:
        """创建文件备份"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}.bak"
        backup_path = file_path.parent / backup_name
        
        try:
            backup_path.write_bytes(file_path.read_bytes())
            return backup_path
        except Exception as e:
            self.logger.warning(f"创建文件备份失败: {str(e)}")
            return None
    
    def _format_json_content(self, content: str) -> str:
        """格式化JSON内容"""
        try:
            json_data = json.loads(content)
            formatted_content = json.dumps(json_data, indent=2, ensure_ascii=False)
            # 验证格式化后的JSON是否有效
            json.loads(formatted_content)
            return formatted_content
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON格式: {str(e)}")

class BackupOperationMixin:
    """备份操作混入类，提供通用的备份功能"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    async def create_user_backup(self, username: str, 
                                backup_type: str = "full") -> Dict[str, Any]:
        """创建用户备份的通用方法"""
        try:
            # 获取用户目录
            user_src_dir = get_user_src_directory(username)
            user_backup_dir = ensure_user_backup_directory_exists(username)
            
            if not user_src_dir.exists():
                raise FileNotFoundError(f"用户 {username} 的src目录不存在")
            
            # 生成备份文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{username}_{backup_type}_{timestamp}.zip"
            backup_path = user_backup_dir / backup_filename
            
            # 创建备份
            backup_info = await self._create_zip_backup(
                source_dir=user_src_dir,
                backup_path=backup_path,
                backup_type=backup_type
            )
            
            self.logger.info(f"用户 {username} 创建备份成功: {backup_filename}")
            
            return {
                "status": "success",
                "message": "备份创建成功",
                "filename": backup_filename,
                "size": backup_info["size"],
                "created_at": timestamp,
                "backup_path": str(backup_path),
                "file_count": backup_info.get("file_count", 0)
            }
            
        except Exception as e:
            self.logger.error(f"创建备份失败: {str(e)}")
            raise Exception(f"创建备份失败: {str(e)}")
    
    async def _create_zip_backup(self, source_dir: Path, backup_path: Path, 
                                backup_type: str = "full") -> Dict[str, Any]:
        """创建ZIP备份文件"""
        file_count = 0
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = Path(root) / file
                    
                    # 根据备份类型过滤文件
                    if not self._should_include_in_backup(file_path, backup_type):
                        continue
                    
                    # 计算相对路径
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
                    file_count += 1
        
        return {
            "size": backup_path.stat().st_size,
            "file_count": file_count
        }
    
    def _should_include_in_backup(self, file_path: Path, backup_type: str) -> bool:
        """判断文件是否应该包含在备份中"""
        # 排除的文件类型
        excluded_extensions = {'.tmp', '.log', '.cache'}
        excluded_names = {'__pycache__', '.git', '.svn', 'node_modules'}
        
        # 检查文件扩展名
        if file_path.suffix.lower() in excluded_extensions:
            return False
        
        # 检查文件/目录名
        if file_path.name in excluded_names:
            return False
        
        # 根据备份类型决定
        if backup_type == "documents_only":
            document_extensions = {'.md', '.txt', '.json', '.yaml', '.yml'}
            return file_path.suffix.lower() in document_extensions
        
        # 默认包含所有文件（除了排除的）
        return True
    
    async def list_user_backups(self, username: str) -> List[Dict[str, Any]]:
        """列出用户备份文件的通用方法"""
        backup_files = []
        
        try:
            user_backup_dir = get_user_backup_directory(username)
            
            if not user_backup_dir.exists():
                return []
            
            # 搜索备份文件
            for file_path in user_backup_dir.glob("backup_*.zip"):
                if file_path.is_file():
                    stat = file_path.stat()
                    
                    backup_files.append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "created_at": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                        "backup_path": str(file_path),
                        "username": username,
                        "formatted_size": self._format_file_size(stat.st_size)
                    })
            
            # 按创建时间排序（最新的在前）
            backup_files.sort(key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"列出用户备份失败: {str(e)}")
        
        return backup_files
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"