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
    
    async def delete_file_safely(self, file_path: Path, 
                                create_backup: bool = True) -> Dict[str, Any]:
        """安全删除文件，支持备份"""
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            result = {
                "status": "success",
                "message": f"文件 {file_path.name} 删除成功",
                "file_path": str(file_path)
            }
            
            # 创建备份（如果需要）
            if create_backup:
                backup_path = self._create_file_backup(file_path)
                if backup_path:
                    result["backup_path"] = str(backup_path)
            
            # 删除文件
            file_path.unlink()
            
            return result
            
        except Exception as e:
            self.logger.error(f"删除文件失败: {str(e)}", exc_info=True)
            raise Exception(f"删除文件失败: {str(e)}")
    
    async def copy_file_safely(self, source_path: Path, dest_path: Path, 
                              overwrite: bool = False) -> Dict[str, Any]:
        """安全复制文件"""
        try:
            if not source_path.exists():
                raise FileNotFoundError(f"源文件不存在: {source_path}")
            
            if dest_path.exists() and not overwrite:
                raise ValueError(f"目标文件已存在: {dest_path}")
            
            # 确保目标目录存在
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            import shutil
            shutil.copy2(source_path, dest_path)
            
            return {
                "status": "success",
                "message": f"文件复制成功: {source_path.name} -> {dest_path.name}",
                "source_path": str(source_path),
                "dest_path": str(dest_path)
            }
            
        except Exception as e:
            self.logger.error(f"复制文件失败: {str(e)}", exc_info=True)
            raise Exception(f"复制文件失败: {str(e)}")
    
    async def move_file_safely(self, source_path: Path, dest_path: Path, 
                              overwrite: bool = False) -> Dict[str, Any]:
        """安全移动文件"""
        try:
            if not source_path.exists():
                raise FileNotFoundError(f"源文件不存在: {source_path}")
            
            if dest_path.exists() and not overwrite:
                raise ValueError(f"目标文件已存在: {dest_path}")
            
            # 确保目标目录存在
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            import shutil
            shutil.move(str(source_path), str(dest_path))
            
            return {
                "status": "success",
                "message": f"文件移动成功: {source_path.name} -> {dest_path.name}",
                "source_path": str(source_path),
                "dest_path": str(dest_path)
            }
            
        except Exception as e:
            self.logger.error(f"移动文件失败: {str(e)}", exc_info=True)
            raise Exception(f"移动文件失败: {str(e)}")
    
    async def list_directory_contents(self, dir_path: Path, 
                                     include_hidden: bool = False,
                                     file_types: List[str] = None) -> Dict[str, Any]:
        """列出目录内容"""
        try:
            if not dir_path.exists():
                raise FileNotFoundError(f"目录不存在: {dir_path}")
            
            if not dir_path.is_dir():
                raise ValueError(f"路径不是目录: {dir_path}")
            
            files = []
            directories = []
            
            for item in dir_path.iterdir():
                # 跳过隐藏文件（如果不包括）
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                if item.is_file():
                    # 过滤文件类型
                    if file_types and item.suffix.lower() not in [ft.lower() for ft in file_types]:
                        continue
                    
                    stat_info = item.stat()
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "size": stat_info.st_size,
                        "formatted_size": self._format_file_size(stat_info.st_size),
                        "modified": datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "extension": item.suffix
                    })
                elif item.is_dir():
                    directories.append({
                        "name": item.name,
                        "path": str(item)
                    })
            
            return {
                "directory": str(dir_path),
                "files": sorted(files, key=lambda x: x["name"]),
                "directories": sorted(directories, key=lambda x: x["name"]),
                "total_files": len(files),
                "total_directories": len(directories)
            }
            
        except Exception as e:
            self.logger.error(f"列出目录内容失败: {str(e)}", exc_info=True)
            raise Exception(f"列出目录内容失败: {str(e)}")
    
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

class FileManagementMixin(FileOperationMixin, BackupOperationMixin):
    """文件管理混入类，整合所有文件操作功能"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """获取文件详细信息"""
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            stat_info = file_path.stat()
            
            file_info = {
                "name": file_path.name,
                "path": str(file_path),
                "size": stat_info.st_size,
                "formatted_size": self._format_file_size(stat_info.st_size),
                "created": datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "extension": file_path.suffix,
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir(),
                "is_text_file": is_text_file(file_path) if file_path.is_file() else False
            }
            
            # 如果是文本文件，获取编码信息
            if file_info["is_text_file"]:
                try:
                    content_info = await self.read_file_content(file_path)
                    file_info["encoding"] = content_info.get("encoding", "unknown")
                    file_info["line_count"] = len(content_info.get("content", "").splitlines())
                except Exception:
                    file_info["encoding"] = "unknown"
                    file_info["line_count"] = 0
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {str(e)}", exc_info=True)
            raise Exception(f"获取文件信息失败: {str(e)}")
    
    async def create_directory_safely(self, dir_path: Path, 
                                     exist_ok: bool = True) -> Dict[str, Any]:
        """安全创建目录"""
        try:
            if dir_path.exists() and not exist_ok:
                raise ValueError(f"目录已存在: {dir_path}")
            
            dir_path.mkdir(parents=True, exist_ok=exist_ok)
            
            return {
                "status": "success",
                "message": f"目录创建成功: {dir_path.name}",
                "directory_path": str(dir_path)
            }
            
        except Exception as e:
            self.logger.error(f"创建目录失败: {str(e)}", exc_info=True)
            raise Exception(f"创建目录失败: {str(e)}")
    
    async def delete_directory_safely(self, dir_path: Path, 
                                     recursive: bool = False,
                                     create_backup: bool = True) -> Dict[str, Any]:
        """安全删除目录"""
        try:
            if not dir_path.exists():
                raise FileNotFoundError(f"目录不存在: {dir_path}")
            
            if not dir_path.is_dir():
                raise ValueError(f"路径不是目录: {dir_path}")
            
            result = {
                "status": "success",
                "message": f"目录删除成功: {dir_path.name}",
                "directory_path": str(dir_path)
            }
            
            # 创建备份（如果需要）
            if create_backup:
                try:
                    backup_info = await self._create_directory_backup(dir_path)
                    result["backup_path"] = backup_info["backup_path"]
                except Exception as e:
                    self.logger.warning(f"创建目录备份失败: {str(e)}")
            
            # 删除目录
            import shutil
            if recursive:
                shutil.rmtree(dir_path)
            else:
                dir_path.rmdir()  # 只能删除空目录
            
            return result
            
        except Exception as e:
            self.logger.error(f"删除目录失败: {str(e)}", exc_info=True)
            raise Exception(f"删除目录失败: {str(e)}")
    
    async def _create_directory_backup(self, dir_path: Path) -> Dict[str, Any]:
        """为目录创建备份"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{dir_path.name}_backup_{timestamp}.zip"
        backup_path = dir_path.parent / backup_name
        
        file_count = 0
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(dir_path)
                    zipf.write(file_path, arcname)
                    file_count += 1
        
        return {
            "backup_path": str(backup_path),
            "file_count": file_count,
            "size": backup_path.stat().st_size
        }
    
    async def search_files(self, search_dir: Path, 
                          pattern: str = "*",
                          file_types: List[str] = None,
                          include_content: bool = False,
                          max_results: int = 100) -> Dict[str, Any]:
        """在目录中搜索文件"""
        try:
            if not search_dir.exists() or not search_dir.is_dir():
                raise ValueError(f"搜索目录不存在或不是目录: {search_dir}")
            
            import glob
            results = []
            search_pattern = str(search_dir / "**" / pattern)
            
            for file_path_str in glob.glob(search_pattern, recursive=True):
                file_path = Path(file_path_str)
                
                if not file_path.is_file():
                    continue
                
                # 过滤文件类型
                if file_types and file_path.suffix.lower() not in [ft.lower() for ft in file_types]:
                    continue
                
                file_info = await self.get_file_info(file_path)
                
                # 如果需要包含内容（只限文本文件）
                if include_content and file_info["is_text_file"]:
                    try:
                        content_info = await self.read_file_content(file_path)
                        file_info["content_preview"] = content_info["content"][:500]  # 只显示前500字符
                    except Exception:
                        file_info["content_preview"] = "无法读取内容"
                
                results.append(file_info)
                
                # 限制结果数量
                if len(results) >= max_results:
                    break
            
            return {
                "search_directory": str(search_dir),
                "pattern": pattern,
                "results": results,
                "total_found": len(results),
                "limited_results": len(results) >= max_results
            }
            
        except Exception as e:
            self.logger.error(f"搜索文件失败: {str(e)}", exc_info=True)
            raise Exception(f"搜索文件失败: {str(e)}")