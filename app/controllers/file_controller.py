"""
File operation controller for MarkEdit application.

This module contains HTTP route handlers for file operations.
"""
import logging
from pathlib import Path
from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.common import get_file_service, require_auth_session, SessionData
from app.controllers.base_controller import (
    BaseController, FileControllerMixin, controller_exception_handler
)

logger = logging.getLogger(__name__)

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 创建文件控制器实例
file_controller = BaseController("FileController")

# 创建文件操作混入类实例
class FileController(BaseController, FileControllerMixin):
    def __init__(self):
        super().__init__("FileController")
        FileControllerMixin.__init__(self)

# 创建控制器实例
file_ctrl = FileController()

# 创建路由器
file_router = APIRouter(prefix="/api", tags=["files"])

# 创建文件服务实例
file_service = get_file_service()

@file_router.get("/files")
@controller_exception_handler("列出用户文件")
async def list_files(request: Request, session: SessionData = Depends(require_auth_session)):
    """列出用户的src和build目录下的所有文件"""
    result = file_service.list_files(request)
    return file_ctrl.create_success_response(result)

@file_router.get("/file/{file_type}/{file_path:path}")
@file_router.head("/file/{file_type}/{file_path:path}")
@controller_exception_handler("读取文件")
async def read_file(file_type: str, file_path: str, request: Request, raw: bool = False, session: SessionData = Depends(require_auth_session)):
    """读取指定文件的内容"""
    return await file_ctrl.handle_file_read_operation(
        file_service.read_file, file_type, file_path, request, raw
    )

@file_router.post("/file/{file_type}/{file_path:path}")
@controller_exception_handler("保存文件")
async def save_file(file_type: str, file_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """保存文件内容"""
    # 获取请求体中的内容
    body = await request.body()
    content = body.decode('utf-8')
    
    result = file_service.save_file(file_type, file_path, content, request)
    return file_ctrl.create_success_response(result, "文件保存成功")

@file_router.delete("/file/{file_type}/{file_path:path}")
@controller_exception_handler("删除文件")
async def delete_file(file_type: str, file_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """删除指定文件"""
    # 验证文件类型和路径
    file_ctrl.validate_file_type(file_type)
    file_ctrl.validate_file_path(file_path)
    
    # 使用统一的权限检查
    await file_ctrl._check_file_type_permission(session, file_type)
    
    result = file_service.delete_file(file_type, file_path, request)
    return file_ctrl.create_success_response(result, "文件删除成功")

@file_router.post("/create-file/{file_path:path}")
@controller_exception_handler("创建文件")
async def create_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """创建新文件"""
    # 验证文件路径
    file_ctrl.validate_file_path(file_path)
    
    # 获取请求体中的内容（可选）
    body = await request.body()
    content = body.decode('utf-8') if body else ""
    
    result = file_service.create_file(file_path, content, request)
    return file_ctrl.create_success_response(result, "文件创建成功")

@file_router.post("/create-directory/{dir_path:path}")
@controller_exception_handler("创建目录")
async def create_directory(dir_path: str, request: Request, session: SessionData = Depends(require_auth_session)):
    """创建新目录"""
    # 验证目录路径
    file_ctrl.validate_file_path(dir_path)
    
    result = file_service.create_directory(dir_path, request)
    return file_ctrl.create_success_response(result, "目录创建成功")

@file_router.post("/upload-file/{file_type}/{file_path:path}")
async def upload_file(file_type: str, file_path: str, file: UploadFile = File(...), request: Request = None, session: SessionData = Depends(require_auth_session)):
    """上传文件到指定目录和路径"""
    import traceback
    
    try:
        logger.info(f"开始上传文件: {file.filename} 到 {file_type}/{file_path}")
        logger.debug(f"文件信息: 类型={file.content_type}, 大小={file.size if hasattr(file, 'size') else '未知'}")
        
        # 添加更详细的请求信息
        logger.debug(f"请求信息: method={request.method}, url={request.url}, headers={dict(request.headers)}")
        
        result = await file_service.upload_file(file_type, file_path, file, request, overwrite=False)
        
        logger.info(f"文件上传成功: {file.filename}")
        return result
        
    except HTTPException as e:
        logger.warning(f"文件上传HTTP错误: {file.filename}, 状态码={e.status_code}, 错误={e.detail}")
        # 记录完整的异常堆栈
        logger.debug(f"HTTP异常堆栈:\n{traceback.format_exc()}")
        raise
    except Exception as e:
        # 记录完整的错误信息和堆栈跟踪
        error_traceback = traceback.format_exc()
        logger.error(f"文件上传失败详细信息:")
        logger.error(f"  - 文件名: {file.filename}")
        logger.error(f"  - 文件类型: {file_type}")
        logger.error(f"  - 文件路径: {file_path}")
        logger.error(f"  - 错误类型: {type(e).__name__}")
        logger.error(f"  - 错误信息: {str(e)}")
        logger.error(f"  - 完整堆栈跟踪:\n{error_traceback}")
        
        # 根据异常类型提供更具体的错误信息
        if isinstance(e, ImportError):
            detail_msg = f"依赖库缺失: {str(e)}。请检查系统是否安装了所有必需的工具（如Pandoc）"
        elif isinstance(e, FileNotFoundError):
            detail_msg = f"文件或工具未找到: {str(e)}。请检查系统配置和工具安装"
        elif isinstance(e, PermissionError):
            detail_msg = f"权限错误: {str(e)}。请检查文件系统权限"
        elif "pandoc" in str(e).lower():
            detail_msg = f"Pandoc转换错误: {str(e)}。请确保Pandoc已正确安装并在系统PATH中"
        else:
            detail_msg = f"文件上传失败: {str(e)}"
        
        raise HTTPException(status_code=500, detail=detail_msg)

@file_router.post("/upload-file/{file_type}/{file_path:path}/overwrite")
async def upload_file_overwrite(file_type: str, file_path: str, file: UploadFile = File(...), request: Request = None, session: SessionData = Depends(require_auth_session)):
    """上传文件到指定目录和路径（允许覆盖）"""
    import traceback
    
    try:
        logger.info(f"开始覆盖上传文件: {file.filename} 到 {file_type}/{file_path}")
        logger.debug(f"文件信息: 类型={file.content_type}, 大小={file.size if hasattr(file, 'size') else '未知'}")
        
        # 添加更详细的请求信息
        logger.debug(f"请求信息: method={request.method}, url={request.url}, headers={dict(request.headers)}")
        
        result = await file_service.upload_file(file_type, file_path, file, request, overwrite=True)
        
        logger.info(f"文件覆盖上传成功: {file.filename}")
        return result
        
    except HTTPException as e:
        logger.warning(f"文件覆盖上传HTTP错误: {file.filename}, 状态码={e.status_code}, 错误={e.detail}")
        # 记录完整的异常堆栈
        logger.debug(f"HTTP异常堆栈:\n{traceback.format_exc()}")
        raise
    except Exception as e:
        # 记录完整的错误信息和堆栈跟踪
        error_traceback = traceback.format_exc()
        logger.error(f"文件覆盖上传失败详细信息:")
        logger.error(f"  - 文件名: {file.filename}")
        logger.error(f"  - 文件类型: {file_type}")
        logger.error(f"  - 文件路径: {file_path}")
        logger.error(f"  - 错误类型: {type(e).__name__}")
        logger.error(f"  - 错误信息: {str(e)}")
        logger.error(f"  - 完整堆栈跟踪:\n{error_traceback}")
        
        # 根据异常类型提供更具体的错误信息
        if isinstance(e, ImportError):
            detail_msg = f"依赖库缺失: {str(e)}。请检查系统是否安装了所有必需的工具（如Pandoc）"
        elif isinstance(e, FileNotFoundError):
            detail_msg = f"文件或工具未找到: {str(e)}。请检查系统配置和工具安装"
        elif isinstance(e, PermissionError):
            detail_msg = f"权限错误: {str(e)}。请检查文件系统权限"
        elif "pandoc" in str(e).lower():
            detail_msg = f"Pandoc转换错误: {str(e)}。请确保Pandoc已正确安装并在系统PATH中"
        else:
            detail_msg = f"文件覆盖上传失败: {str(e)}"
        
        raise HTTPException(status_code=500, detail=detail_msg)

# 静态文件服务路由
static_router = APIRouter(tags=["static"])

@static_router.get("/user-src/{file_path:path}")
async def serve_user_static_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供用户特定的src目录下的文件"""
    return file_service.serve_user_static_file(file_path, request)

@static_router.get("/user-illustrations/{username}/{file_path:path}")
async def serve_user_illustrations_file_with_username(username: str, file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """为指定用户提供插图文件（支持用户名前缀）"""
    return file_service.serve_user_illustrations_file_with_username(username, file_path, request)

@static_router.get("/illustrations/{username}/{file_path:path}")
async def serve_public_user_illustrations_file(username: str, file_path: str, request: Request) -> Response:
    """为指定用户提供插图文件（公开访问，无需认证）"""
    return file_service.serve_user_illustrations_file_with_username(username, file_path, request)

@static_router.get("/user-illustrations/{file_path:path}")
async def serve_user_illustrations_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供用户特定的illustrations目录下的文件（向后兼容）"""
    return file_service.serve_user_illustrations_file(file_path, request)

@static_router.get("/EPUB/illustrations/{file_path:path}")
async def serve_epub_illustrations_file(file_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供EPUB内部illustrations目录下的文件（用于EPUB.js预览）"""
    return file_service.serve_epub_resource_file(f"illustrations/{file_path}", request)

@static_router.get("/EPUB/{resource_path:path}")
async def serve_epub_resource_file(resource_path: str, request: Request, session: SessionData = Depends(require_auth_session)) -> Response:
    """动态提供EPUB内部资源文件（用于EPUB.js预览）"""
    return file_service.serve_epub_resource_file(resource_path, request)

@file_router.post("/reset-src")
@controller_exception_handler("重置Src目录")
async def reset_src_directory(request: Request, session: SessionData = Depends(require_auth_session)):
    """重置用户的src目录为初始状态"""
    result = file_service.reset_src_directory(request)
    return file_ctrl.create_success_response(result, "Src目录重置成功")