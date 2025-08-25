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
        
        if not full_path.exists():
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
        if file_type != "src":
            raise HTTPException(status_code=400, detail="只能删除src目录下的文件")
        
        user_src_dir = self.get_user_src_dir(request)
        full_path = user_src_dir / file_path
        
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
    
    def serve_user_static_file(self, file_path: str, request: Request) -> Response:
        """动态提供用户特定的src目录下的文件"""
        user_src_dir = self.get_user_src_dir(request)
        full_path = user_src_dir / file_path
        
        return create_static_file_response(full_path)
    
    def serve_user_illustrations_file(self, file_path: str, request: Request) -> Response:
        """动态提供用户特定的illustrations目录下的文件"""
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