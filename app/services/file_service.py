"""
File service for MarkEdit application.

This module contains business logic for file operations.
"""
from pathlib import Path
from typing import Dict, List, Any, Union
from fastapi import Request, HTTPException
from fastapi.responses import Response

from app.common import (
    get_session_service,
    get_user_src_directory,
    scan_directory, read_text_file, read_image_file, save_text_file,
    delete_file_safely, create_file_safely, create_directory_safely,
    is_text_file, is_image_file, is_previewable_binary,
    create_file_response, create_static_file_response
)

class FileService:
    """文件操作服务类"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def get_user_src_dir(self, request: Request) -> Path:
        """获取当前用户的src目录"""
        session_service = get_session_service()
        session = session_service.get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        return get_user_src_directory(session.username)
    
    def get_user_build_dir(self, request: Request) -> Path:
        """获取当前用户的build目录"""
        session_service = get_session_service()
        session = session_service.get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        user_build_dir = self.base_dir / "users" / session.username / "build"
        user_build_dir.mkdir(parents=True, exist_ok=True)
        return user_build_dir
    
    def list_files(self, request: Request) -> Dict[str, List[Dict[str, Any]]]:
        """列出用户的src和build目录下的所有文件"""
        user_src_dir = self.get_user_src_dir(request)
        user_build_dir = self.get_user_build_dir(request)
        
        return {
            "src": scan_directory(user_src_dir, user_src_dir),
            "build": scan_directory(user_build_dir, user_build_dir)
        }
    
    def read_file(self, file_type: str, file_path: str, request: Request, raw: bool = False) -> Union[Dict[str, Any], Response]:
        """读取指定文件的内容"""
        if file_type == "src":
            user_dir = self.get_user_src_dir(request)
        elif file_type == "build":
            user_dir = self.get_user_build_dir(request)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        full_path = user_dir / file_path
        
        # 特殊处理：如果在build目录下请求illustrations文件但未找到，则尝试在src目录下查找
        if file_type == "build" and file_path.startswith("illustrations/") and not full_path.exists():
            # 尝试在src目录下查找
            src_dir = self.get_user_src_dir(request)
            src_full_path = src_dir / file_path
            
            # 如果在src目录中找到了文件，则使用该文件
            if src_full_path.exists() and src_full_path.is_file():
                full_path = src_full_path
            else:
                # 如果在src目录中没找到，检查是否是带用户名前缀的路径
                # 例如: illustrations/super_admin_markedit/chapter_08.svg
                path_parts = file_path.split("/", 2)
                if len(path_parts) >= 3 and path_parts[1]:  # illustrations/username/filename
                    # 提取用户名和文件名
                    username_prefix = path_parts[1]
                    actual_file_path = path_parts[2]
                    
                    # 获取带前缀的用户名对应的src目录
                    from app.common import get_user_src_directory
                    try:
                        user_src_dir = get_user_src_directory(username_prefix)
                        user_illustrations_path = user_src_dir / "illustrations" / actual_file_path
                        
                        if user_illustrations_path.exists() and user_illustrations_path.is_file():
                            full_path = user_illustrations_path
                        else:
                            raise HTTPException(status_code=404, detail="File not found")
                    except ValueError:
                        # 用户名不合法，抛出404错误
                        raise HTTPException(status_code=404, detail="File not found")
                else:
                    raise HTTPException(status_code=404, detail="File not found")
        elif not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # 如果请求原始文件内容（用于iframe预览）
        if raw:
            return create_file_response(full_path, raw=True)
        
        # 对于文本文件，返回内容（JSON格式）
        if is_text_file(full_path):
            return read_text_file(full_path)
        # 对于图片文件，返回base64编码
        elif is_image_file(full_path):
            return read_image_file(full_path)
        # 对于可预览的二进制文件，返回FileResponse以支持iframe预览
        elif is_previewable_binary(full_path):
            return create_file_response(full_path)
        else:
            # 其他二进制文件
            return {"content": "Binary file", "type": "binary"}
    
    def save_file(self, file_type: str, file_path: str, content: str, request: Request) -> Dict[str, str]:
        """保存文件内容"""
        if file_type != "src":
            raise HTTPException(status_code=400, detail="只能保存src目录下的文件")
        
        user_src_dir = self.get_user_src_dir(request)
        full_path = user_src_dir / file_path
        
        save_text_file(full_path, content)
        
        return {"message": "File saved successfully"}
    
    def delete_file(self, file_type: str, file_path: str, request: Request) -> Dict[str, str]:
        """删除指定文件"""
        if file_type == "src":
            user_dir = self.get_user_src_dir(request)
        elif file_type == "build":
            user_dir = self.get_user_build_dir(request)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型。支持的类型: src, build")
        
        full_path = user_dir / file_path
        
        delete_file_safely(full_path)
        
        return {"message": "File deleted successfully"}
    
    def create_file(self, file_path: str, content: str, request: Request) -> Dict[str, str]:
        """创建新文件"""
        user_src_dir = self.get_user_src_dir(request)
        full_path = user_src_dir / file_path
        
        create_file_safely(full_path, content)
        
        return {"message": "File created successfully"}
    
    def create_directory(self, dir_path: str, request: Request) -> Dict[str, str]:
        """创建新目录"""
        user_src_dir = self.get_user_src_dir(request)
        full_path = user_src_dir / dir_path
        
        create_directory_safely(full_path)
        
        return {"message": "Directory created successfully"}
    
    async def upload_file(self, file_type: str, file_path: str, file: "UploadFile", request: Request, overwrite: bool = False) -> Dict[str, Any]:
        """上传文件到指定路径"""
        from fastapi import UploadFile
        
        # 根据file_type选择目标目录
        if file_type == "src":
            target_dir = self.get_user_src_dir(request)
        elif file_type == "build":
            target_dir = self.get_user_build_dir(request)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Must be 'src' or 'build'")
            
        full_path = target_dir / file_path
        
        # 检查文件是否已存在
        if full_path.exists() and not overwrite:
            raise HTTPException(status_code=400, detail="文件已存在，使用覆盖选项来替换")
        
        # 确保目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 读取上传的文件内容
            content = await file.read()
            
            # 自动格式识别和处理
            file_extension = full_path.suffix.lower()
            
            # 对于EPUB文件的特殊处理
            if file_extension == '.epub':
                if file_type == "src":
                    # src目录的EPUB文件需要转换为Markdown，传递已读取的内容
                    return await self._handle_epub_to_markdown(file, full_path, file_path, request, overwrite, content)
                elif file_type == "build":
                    # build目录的EPUB文件直接保存用于阅读，传递已读取的内容
                    return await self._handle_epub_for_reading(file, full_path, file_path, request, overwrite, content)
            
            # 其他文件的正常处理
            # 保存文件
            with open(full_path, 'wb') as f:
                f.write(content)
            
            # 获取文件信息
            file_size = full_path.stat().st_size
            
            # 根据文件类型返回不同的响应信息
            response_data = {
                "message": "文件上传成功",
                "filename": file.filename,
                "path": file_path,
                "size": file_size,
                "overwritten": full_path.exists() and overwrite,
                "file_type": self._detect_file_type(file_extension),
                "target_directory": file_type
            }
            
            # 对于EPUB文件，添加额外信息
            if file_extension == '.epub':
                if file_type == "build":
                    # build目录的EPUB文件支持预览
                    response_data["supports_preview"] = True
                    response_data["preview_url"] = f"/epub-viewer.html?url=/api/file/build/{file_path}?raw=true"
                elif file_type == "src":
                    # src目录的EPUB文件表示需要转换
                    response_data["requires_conversion"] = True
                    response_data["conversion_note"] = "该EPUB文件将被转换为Markdown格式用于编辑"
                
            return response_data
            
        except Exception as e:
            # 如果保存失败，删除部分上传的文件
            if full_path.exists():
                full_path.unlink()
            raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")
    
    def _detect_file_type(self, file_extension: str) -> str:
        """检测文件类型"""
        if file_extension in {'.md', '.yml', '.yaml', '.css', '.html', '.js', '.json', '.txt', '.xml', '.csv', ''}:
            return 'text'
        elif file_extension in {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'}:
            return 'image'
        elif file_extension in {'.pdf', '.epub'}:
            return 'previewable_binary'
        else:
            return 'binary'
    
    def serve_user_static_file(self, file_path: str, request: Request) -> Response:
        """动态提供用户特定的src目录下的文件"""
        user_src_dir = self.get_user_src_dir(request)
        full_path = user_src_dir / file_path
        
        return create_static_file_response(full_path)
    
    def serve_epub_resource_file(self, resource_path: str, request: Request) -> Response:
        """动态提供EPUB内部资源文件（用于EPUB.js预览）"""
        user_build_dir = self.get_user_build_dir(request)
        
        # EPUB.js访问的资源可能在build目录的illustrations子目录中
        full_path = user_build_dir / resource_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # 安全检查：只允许访问安全的文件类型（图片和其他EPUB相关资源）
        file_extension = full_path.suffix.lower()
        allowed_extensions = {'.svg', '.png', '.jpg', '.jpeg', '.gif', '.css', '.html', '.xhtml'}
        
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        return create_static_file_response(full_path)
    
    def serve_user_illustrations_file(self, file_path: str, request: Request) -> Response:
        """动态提供用户特定的illustrations目录下的文件（向后兼容）"""
        user_src_dir = self.get_user_src_dir(request)
        illustrations_dir = user_src_dir / "illustrations"
        full_path = illustrations_dir / file_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # 只允许图片文件
        if not is_image_file(full_path):
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        return create_static_file_response(full_path)
    
    def serve_user_illustrations_file_with_username(self, username: str, file_path: str, request: Request) -> Response:
        """为指定用户提供插图文件（支持用户名前缀）"""
        from app.common import get_user_src_directory
        
        # 直接使用传入的用户名（已包含前缀）获取其src目录
        user_src_dir = get_user_src_directory(username)
        illustrations_dir = user_src_dir / "illustrations"
        full_path = illustrations_dir / file_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # 只允许图片文件
        if not is_image_file(full_path):
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        return create_static_file_response(full_path)
    
    async def _handle_epub_to_markdown(self, file: "UploadFile", full_path: Path, file_path: str, request: Request, overwrite: bool, content: bytes = None) -> Dict[str, Any]:
        """处理src目录上传的EPUB文件，转换为Markdown格式"""
        import tempfile
        import zipfile
        import shutil
        from app.common import get_epub_service
        
        # 检查文件是否已存在
        if full_path.exists() and not overwrite:
            raise HTTPException(status_code=400, detail="EPUB文件已存在，使用覆盖选项来替换")
        
        # 获取文件内容（如果没有传入则读取）
        if content is None:
            content = await file.read()
        
        # 验证文件大小
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上传的EPUB文件为空")
        
        # 先保存原EPUB文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # 验证EPUB文件的完整性（简单ZIP验证）
        try:
            with zipfile.ZipFile(temp_file_path, 'r') as test_zip:
                # 尝试读取文件列表以验证ZIP结构
                file_list = test_zip.namelist()
                if not file_list:
                    raise HTTPException(status_code=400, detail="EPUB文件似乎为空或损坏")
                
                # 检查EPUB必需的基本文件
                has_mimetype = 'mimetype' in file_list
                has_meta_inf = any('META-INF/' in f for f in file_list)
                
                if not has_mimetype or not has_meta_inf:
                    raise HTTPException(status_code=400, detail="文件不是有效的EPUB格式，缺少必需的结构")
                    
        except zipfile.BadZipFile:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="上传的文件不是有效的EPUB文件（ZIP格式错误）")
        except Exception as e:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
            if "EPUB文件" in str(e) or "ZIP格式" in str(e):
                raise
            else:
                raise HTTPException(status_code=400, detail=f"EPUB文件验证失败: {str(e)}")
        
        try:
            # 获取EPUB服务实例
            epub_service = get_epub_service()
            
            # 获取用户src目录作为输出目录
            user_src_dir = self.get_user_src_dir(request)
            
            # 记录转换前的日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"开始转换EPUB文件: {file.filename}, 大小: {len(content)} 字节")
            
            # 在转换之前清空src目录
            if user_src_dir.exists():
                logger.info(f"清空用户src目录: {user_src_dir}")
                for item in user_src_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            
            # 执行EPUB转换
            result = await epub_service.convert_epub_to_markdown(temp_file_path, str(user_src_dir))
            
            if result.get("status") == "success":
                logger.info(f"EPUB转换成功: {file.filename}")
                # 转换成功，返回成功信息
                return {
                    "message": "EPUB文件已成功转换为Markdown格式",
                    "filename": file.filename,
                    "path": file_path,
                    "conversion_status": "success",
                    "converted_files": result.get("converted_files", []),
                    "chapters_count": result.get("total_chapters", len(result.get("converted_files", []))),
                    "images_count": result.get("illustrations_count", len(result.get("image_files", []))),
                    "file_type": "epub_converted",
                    "target_directory": "src",
                    "note": "原EPUB文件已转换为Markdown文件结构，可在src目录中查看和编辑",
                    "metadata": result.get("metadata", {})
                }
            else:
                error_msg = result.get('message', '未知错误')
                logger.error(f"EPUB转换失败: {file.filename}, 错误: {error_msg}")
                # 转换失败，返回错误信息
                raise HTTPException(status_code=500, detail=f"EPUB转换失败: {error_msg}")
        
        except HTTPException:
            # HTTP异常直接向上抛出
            raise
        except Exception as e:
            logger.error(f"EPUB转换过程中发生错误: {file.filename}, 错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"EPUB转换过程失败: {str(e)}")
        
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
    
    async def _handle_epub_for_reading(self, file: "UploadFile", full_path: Path, file_path: str, request: Request, overwrite: bool, content: bytes = None) -> Dict[str, Any]:
        """处理build目录上传的EPUB文件，直接保存用于阅读"""
        import zipfile
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 检查文件是否已存在
        if full_path.exists() and not overwrite:
            raise HTTPException(status_code=400, detail="EPUB文件已存在，使用覆盖选项来替换")
        
        # 确保目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取文件内容（如果没有传入则读取）
        if content is None:
            content = await file.read()
        
        # 验证文件大小
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上传的EPUB文件为空")
        
        # 保存文件
        with open(full_path, 'wb') as f:
            f.write(content)
        
        # 验证EPUB文件的完整性（简单ZIP验证）
        try:
            with zipfile.ZipFile(full_path, 'r') as test_zip:
                # 尝试读取文件列表以验证ZIP结构
                file_list = test_zip.namelist()
                if not file_list:
                    # 删除无效文件
                    full_path.unlink()
                    raise HTTPException(status_code=400, detail="EPUB文件似乎为空或损坏")
                
                # 检查EPUB必需的基本文件
                has_mimetype = 'mimetype' in file_list
                has_meta_inf = any('META-INF/' in f for f in file_list)
                
                if not has_mimetype or not has_meta_inf:
                    logger.warning(f"EPUB文件 {file.filename} 缺少部分标准结构，但仍尝试保存")
                    
        except zipfile.BadZipFile:
            # 删除无效文件
            full_path.unlink()
            raise HTTPException(status_code=400, detail="上传的文件不是有效的EPUB文件（ZIP格式错误）")
        except Exception as e:
            logger.warning(f"EPUB文件验证警告: {str(e)}，但继续保存")
        
        # 获取文件信息
        file_size = full_path.stat().st_size
        
        logger.info(f"EPUB文件上传成功: {file.filename}, 大小: {file_size} 字节")
        
        return {
            "message": "EPUB文件上传成功，可用于阅读",
            "filename": file.filename,
            "path": file_path,
            "size": file_size,
            "overwritten": overwrite and full_path.exists(),
            "file_type": "previewable_binary",
            "target_directory": "build",
            "supports_preview": True,
            "preview_url": f"/epub-viewer.html?url=/api/file/build/{file_path}?raw=true",
            "note": "该EPUB文件可直接在浏览器中阅读"
        }
    
    def reset_src_directory(self, request: Request) -> Dict[str, str]:
        """重置用户的src目录为初始状态"""
        import shutil
        from pathlib import Path
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 获取用户src目录
        user_src_dir = self.get_user_src_dir(request)
        
        # 获取项目默认src目录
        project_root = Path(__file__).parent.parent.parent
        project_src_dir = project_root / "src"
        
        logger.info(f"重置Src目录: user_src_dir={user_src_dir}, project_src_dir={project_src_dir}")
        
        # 删除用户src目录中的所有内容
        if user_src_dir.exists():
            logger.info(f"删除用户src目录中的内容: {user_src_dir}")
            for item in user_src_dir.iterdir():
                if item.is_file():
                    logger.info(f"删除文件: {item}")
                    item.unlink()
                elif item.is_dir():
                    logger.info(f"删除目录: {item}")
                    shutil.rmtree(item)
        
        # 复制项目默认src目录内容到用户src目录
        if project_src_dir.exists():
            logger.info(f"复制项目默认src目录内容到用户src目录: {project_src_dir} -> {user_src_dir}")
            for item in project_src_dir.iterdir():
                if item.is_file():
                    target_path = user_src_dir / item.name
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    logger.info(f"复制文件: {item} -> {target_path}")
                    shutil.copy2(item, target_path)
                elif item.is_dir():
                    target_path = user_src_dir / item.name
                    if target_path.exists():
                        logger.info(f"删除已存在的目录: {target_path}")
                        shutil.rmtree(target_path)
                    logger.info(f"复制目录: {item} -> {target_path}")
                    shutil.copytree(item, target_path)
        else:
            logger.warning(f"项目默认src目录不存在: {project_src_dir}")
        
        logger.info("Src目录重置完成")
        return {"message": "Src目录已重置为初始状态"}