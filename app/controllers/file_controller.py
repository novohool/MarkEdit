"""
File operation controller for MarkEdit application.

This module contains HTTP route handlers for file operations.
"""
from pathlib import Path
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import Response

from app.common import get_file_service, require_auth_session, SessionData

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 创建路由器
file_router = APIRouter(prefix="/api", tags=["files"])

# 创建文件服务实例
file_service = get_file_service()

@file_router.get("/files")
async def list_files(request: Request, session: SessionData = Depends(require_auth_session)):
    """列出用户的src和build目录下的所有文件"""
    return file_service.list_files(request)

@file_router.get("/file/{file_type}/{file_path:path}")
async def read_file(file_type: str, file_path: str, request: Request, raw: bool = False, session: SessionData = Depends(require_auth_session)):
    """读取指定文件的内容"""
    return file_service.read_file(file_type, file_path, request, raw)

@file_router.post("/file/{file_type}/{file_path:path}")
async def save_file(file_type: str, file_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """保存文件内容"""
    # 获取请求体中的内容
    body = await request.body()
    content = body.decode('utf-8')
    
    return file_service.save_file(file_type, file_path, content, request)

@file_router.delete("/file/{file_type}/{file_path:path}")
async def delete_file(file_type: str, file_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """删除指定文件"""
    return file_service.delete_file(file_type, file_path, request)

@file_router.post("/create-file/{file_path:path}")
async def create_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """创建新文件"""
    # 获取请求体中的内容（可选）
    body = await request.body()
    content = body.decode('utf-8') if body else ""
    
    return file_service.create_file(file_path, content, request)

@file_router.post("/create-directory/{dir_path:path}")
async def create_directory(dir_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """创建新目录"""
    return file_service.create_directory(dir_path, request)

@file_router.post("/upload-file/{file_type}/{file_path:path}")
async def upload_file(file_type: str, file_path: str, file: UploadFile = File(...), request: Request = None, session: SessionData = Depends(require_auth_session)):
    """上传文件到指定目录和路径"""
    return await file_service.upload_file(file_type, file_path, file, request, overwrite=False)

@file_router.post("/upload-file/{file_type}/{file_path:path}/overwrite")
async def upload_file_overwrite(file_type: str, file_path: str, file: UploadFile = File(...), request: Request = None, session: SessionData = Depends(require_auth_session)):
    """上传文件到指定目录和路径（允许覆盖）"""
    return await file_service.upload_file(file_type, file_path, file, request, overwrite=True)

# 静态文件服务路由
static_router = APIRouter(tags=["static"])

@static_router.get("/user-src/{file_path:path}")
async def serve_user_static_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供用户特定的src目录下的文件"""
    return file_service.serve_user_static_file(file_path, request)

@static_router.get("/user-illustrations/{file_path:path}")
async def serve_user_illustrations_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供用户特定的illustrations目录下的文件"""
    return file_service.serve_user_illustrations_file(file_path, request)

@static_router.get("/EPUB/illustrations/{file_path:path}")
async def serve_epub_illustrations_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供EPUB内部illustrations目录下的文件（用于EPUB.js预览）"""
    return file_service.serve_epub_resource_file(f"illustrations/{file_path}", request)

@static_router.get("/EPUB/{resource_path:path}")
async def serve_epub_resource_file(resource_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供EPUB内部资源文件（用于EPUB.js预览）"""
    return file_service.serve_epub_resource_file(resource_path, request)