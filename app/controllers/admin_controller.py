"""
Admin controller for MarkEdit application.

This module contains route handlers for admin operations.
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, Any

# 使用公共模块
from app.common import (
    SessionData, get_admin_service, get_build_service, get_epub_service,
    get_session_service, require_permission, require_role, require_auth_session,
    check_user_permission, get_session, hash_password, verify_password,
    admin_table, database, get_user_src_directory, get_user_directory,
    user_table, role_table, user_role_table, permission_table,
    role_permission_table, audit_log_table, log_user_operation_async
)

from app.utils.error_handler import (
    error_handler, ErrorCategory, ErrorLevel, 
    handle_controller_error, create_recovery_suggestions
)

logger = logging.getLogger(__name__)

# 创建路由器
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# 使用公共模块的服务实例获取器
def get_admin_service_instance():
    return get_admin_service()

def get_build_service_instance():
    try:
        logger.debug("开始获取构建服务实例")
        service = get_build_service()
        logger.debug(f"get_build_service() 返回: {type(service)}")
        if service is None:
            logger.error("get_build_service() returned None")
            raise HTTPException(status_code=500, detail="构建服务初始化失败")
        logger.debug("成功获取构建服务实例")
        return service
    except Exception as e:
        logger.error(f"获取构建服务实例时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取构建服务实例时出错: {str(e)}")

def get_epub_service_instance():
    return get_epub_service()

def get_user_session(request: Request) -> SessionData:
    """获取用户会话数据（包括管理员和普通用户）"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    
    session_service = get_session_service()
    session = session_service.sessions.get(session_id)
    if not session or not session.access_token:
        raise HTTPException(status_code=401, detail="未登录")
    
    return session

async def check_epub_permission(session: SessionData = Depends(get_user_session)):
    """检查用户是否有EPUB转换权限"""
    if not session.username:
        raise HTTPException(status_code=401, detail="用户未登录")
    
    # 检查用户是否有EPUB构建权限
    has_permission = await check_user_permission(session.username, "build.epub")
    if not has_permission:
        raise HTTPException(status_code=403, detail="权限不足，无法执行EPUB转换")
    
    return session

async def check_backup_permission(session: SessionData = Depends(get_user_session)):
    """检查用户是否有手动备份权限"""
    if not session.username:
        raise HTTPException(status_code=401, detail="用户未登录")
    
    # 检查用户是否有手动备份权限
    has_permission = await check_user_permission(session.username, "manual_backup")
    if not has_permission:
        raise HTTPException(status_code=403, detail="权限不足，无法执行手动备份")
    
    return session

# 文件管理相关路由
@admin_router.get("/file/{file_name}")
@require_permission("system.config")
@handle_controller_error("读取管理文件")
async def read_admin_file(file_name: str, request: Request):
    """读取管理文件的内容"""
    admin_service = get_admin_service_instance()
    result = await admin_service.read_admin_file(file_name)
    return result

@admin_router.post("/file/{file_name}")
@require_permission("system.config")
@handle_controller_error("保存管理文件")
async def save_admin_file(file_name: str, request: Request):
    """保存管理文件的内容"""
    # 获取请求体中的内容
    body = await request.body()
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        content = body.decode('utf-8')
    else:
        content = body.decode('utf-8')
    
    admin_service = get_admin_service_instance()
    result = await admin_service.save_admin_file(file_name, content, content_type)
    return result

# 备份管理相关路由
@admin_router.post("/backup")
@handle_controller_error("创建备份")
async def create_backup(session: SessionData = Depends(check_backup_permission)):
    """创建备份"""
    admin_service = get_admin_service_instance()
    result = await admin_service.create_backup(session.username)
    return result

@admin_router.get("/backups")
@require_permission("manual_backup")
async def list_backups(request: Request):
    """列出用户的备份文件"""
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        admin_service = get_admin_service_instance()
        result = await admin_service.list_backups(session.username)
        return {"backups": result}
    except Exception as e:
        logger.error(f"获取备份列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")

@admin_router.post("/restore/{filename}")
@require_permission("manual_backup")
async def restore_backup(filename: str, request: Request):
    """恢复备份"""
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        admin_service = get_admin_service_instance()
        result = await admin_service.restore_backup(filename, session.username)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"恢复备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/backup/{filename}")
@require_permission("manual_backup")
async def delete_backup(filename: str, request: Request):
    """删除备份文件"""
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        admin_service = get_admin_service_instance()
        result = await admin_service.delete_backup(filename, session.username)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/backup/{filename}")
@require_permission("manual_backup")
async def download_backup(filename: str, request: Request):
    """下载备份文件"""
    try:
        from app.common import get_user_backup_directory
        session_service = get_session_service()
        session = session_service.get_session(request)
        
        # 获取用户的备份目录
        user_backup_dir = get_user_backup_directory(session.username)
        backup_path = user_backup_dir / filename
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="备份文件不存在")
        
        return FileResponse(
            path=backup_path,
            filename=filename,
            media_type="application/zip"
        )
    except Exception as e:
        logger.error(f"下载备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载备份失败: {str(e)}")

# Src目录管理相关路由
@admin_router.post("/upload-src")
@require_permission("system.config")
async def upload_src_directory(file: UploadFile = File(...), request: Request = None):
    """上传并替换用户的Src目录"""
    try:
        import tempfile
        import zipfile
        import shutil
        from app.common import get_user_src_directory, get_user_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 验证文件类型
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="只允许上传.zip文件")
        
        # 获取用户特定的目录
        user_src_dir = get_user_src_directory(session.username)
        user_dir = get_user_directory(session.username)
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "upload.zip"
            extract_path = temp_path / "extracted"
            
            # 保存上传的文件
            content = await file.read()
            with open(zip_path, "wb") as f:
                f.write(content)
            
            # 验证ZIP文件
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # 检查ZIP文件完整性
                    zip_ref.testzip()
                    # 解压文件
                    zip_ref.extractall(extract_path)
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail="无效的ZIP文件")
            
            # 先备份当前的Src目录
            if user_src_dir.exists():
                admin_service = get_admin_service_instance()
                backup_result = await admin_service.create_backup(session.username)
                logger.info(f"上传前已备份当前Src目录: {backup_result}")
            
            # 删除当前的Src目录内容
            if user_src_dir.exists():
                shutil.rmtree(user_src_dir)
            
            # 创建新的Src目录
            user_src_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制解压的内容到Src目录
            files_copied = 0
            directories_created = 0
            
            # 查找解压后的src目录或直接使用解压的根目录
            source_dir = extract_path
            src_subdir = extract_path / "src"
            if src_subdir.exists() and src_subdir.is_dir():
                source_dir = src_subdir
            
            # 复制文件
            for item in source_dir.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(source_dir)
                    dest_path = user_src_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
                    files_copied += 1
                elif item.is_dir():
                    rel_path = item.relative_to(source_dir)
                    dest_path = user_src_dir / rel_path
                    dest_path.mkdir(parents=True, exist_ok=True)
                    directories_created += 1
        
        logger.info(f"用户 {session.username} 成功上传了新的Src目录")
        return {
            "status": "success",
            "message": "Src目录上传成功",
            "statistics": {
                "files_copied": files_copied,
                "directories_created": directories_created
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传Src目录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@admin_router.get("/download-src")
@require_permission("system.config")
async def download_src_directory(request: Request):
    """下载用户的Src目录为ZIP文件"""
    try:
        import zipfile
        import tempfile
        from app.common import get_user_src_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的Src目录
        user_src_dir = get_user_src_directory(session.username)
        
        if not user_src_dir.exists():
            raise HTTPException(status_code=404, detail="Src目录不存在")
        
        # 创建临时ZIP文件
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            zip_path = temp_file.name
        
        try:
            # 创建ZIP文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in user_src_dir.rglob('*'):
                    if file_path.is_file():
                        arc_name = f"src/{file_path.relative_to(user_src_dir)}"
                        zipf.write(file_path, arc_name)
            
            # 生成下载文件名
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_filename = f"{session.username}_src_{timestamp}.zip"
            
            return FileResponse(
                path=zip_path,
                filename=download_filename,
                media_type="application/zip"
            )
            
        except Exception as e:
            # 清理临时文件
            Path(zip_path).unlink(missing_ok=True)
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载Src目录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

# 用户Src目录重置相关路由
@admin_router.post("/reset-src")
@require_permission("manual_backup")
async def reset_user_src_directory(request: Request):
    """重置用户的Src目录到默认状态"""
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.reset_user_src_directory(session.username)
        
        logger.info(f"用户 {session.username} 成功重置了src目录")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置用户src目录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@admin_router.post("/admin/reset-user-src/{username}")
@require_permission("user.edit")
async def admin_reset_user_src_directory(username: str, request: Request):
    """管理员重置指定用户的Src目录到默认状态"""
    try:
        if not username or not username.strip():
            raise HTTPException(status_code=400, detail="用户名不能为空")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.reset_user_src_directory(username)
        
        # 获取当前管理员信息用于日志
        session_service = get_session_service()
        admin_session = session_service.get_session(request)
        admin_username = admin_session.username if admin_session else "unknown"
        
        logger.info(f"管理员 {admin_username} 重置了用户 {username} 的src目录")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员重置用户src目录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

# 构建相关路由
@admin_router.post("/build/epub")
async def build_epub_endpoint(session: SessionData = Depends(check_epub_permission)):
    """构建EPUB文件"""
    try:
        from app.common import get_user_src_directory, get_user_directory
        from pathlib import Path
        
        # 获取用户特定的目录
        user_src_dir = get_user_src_directory(session.username)
        user_build_dir = get_user_directory(session.username) / "build"
        user_build_dir.mkdir(parents=True, exist_ok=True)
        
        build_service = get_build_service_instance()
        result = await build_service.build_epub(src_dir=user_src_dir, build_dir=user_build_dir)
        return result
    except Exception as e:
        logger.error(f"构建EPUB失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"构建EPUB失败: {str(e)}")

@admin_router.post("/build/pdf")
@require_permission("build.pdf")
async def build_pdf_endpoint(request: Request):
    """构建PDF文件"""
    try:
        logger.debug("开始处理PDF构建请求")
        from app.common import get_user_src_directory, get_user_directory
        from pathlib import Path
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的目录
        user_src_dir = get_user_src_directory(session.username)
        user_build_dir = get_user_directory(session.username) / "build"
        user_build_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("获取构建服务实例")
        build_service = get_build_service_instance()
        logger.debug(f"构建服务实例类型: {type(build_service)}")
        result = await build_service.build_pdf(src_dir=user_src_dir, build_dir=user_build_dir)
        logger.debug("PDF构建完成")
        return result
    except Exception as e:
        logger.error(f"构建PDF失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"构建PDF失败: {str(e)}")

@admin_router.post("/build/pdf-wkhtmltopdf")
@require_permission("build.pdf")
async def build_pdf_wkhtmltopdf_endpoint(request: Request):
    """使用wkhtmltopdf构建PDF文件"""
    try:
        logger.debug("开始处理wkhtmltopdf PDF构建请求")
        from app.common import get_user_src_directory, get_user_directory
        from pathlib import Path
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的目录
        user_src_dir = get_user_src_directory(session.username)
        user_build_dir = get_user_directory(session.username) / "build"
        user_build_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("获取构建服务实例")
        build_service = get_build_service_instance()
        logger.debug(f"构建服务实例类型: {type(build_service)}")
        result = await build_service.build_pdf_with_wkhtmltopdf(src_dir=user_src_dir, build_dir=user_build_dir)
        logger.debug("wkhtmltopdf PDF构建完成")
        return result
    except Exception as e:
        logger.error(f"wkhtmltopdf构建PDF失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"wkhtmltopdf构建PDF失败: {str(e)}")

@admin_router.post("/build/html")
@require_permission("build.epub")
async def build_html_endpoint(request: Request):
    """构建HTML文件"""
    try:
        from app.common import get_user_src_directory, get_user_directory
        from pathlib import Path
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的目录
        user_src_dir = get_user_src_directory(session.username)
        user_build_dir = get_user_directory(session.username) / "build"
        user_build_dir.mkdir(parents=True, exist_ok=True)
        
        build_service = get_build_service_instance()
        result = await build_service.build_html(src_dir=user_src_dir, build_dir=user_build_dir)
        return result
    except Exception as e:
        logger.error(f"构建HTML失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"构建HTML失败: {str(e)}")

@admin_router.get("/build/info")
@require_permission("build.epub")
async def get_build_info(request: Request):
    """获取构建信息"""
    try:
        from app.common import get_user_directory
        from pathlib import Path
        import datetime
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的构建目录
        user_build_dir = get_user_directory(session.username) / "build"
        
        build_info = {
            "build_dir": str(user_build_dir),
            "build_files": [],
            "last_build_time": None
        }
        
        # 检查构建目录中的文件
        if user_build_dir.exists():
            for file_path in user_build_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.epub', '.pdf', '.html']:
                    stat = file_path.stat()
                    build_info["build_files"].append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "created_at": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # 按修改时间排序
            build_info["build_files"].sort(key=lambda x: x["modified_at"], reverse=True)
            
            # 获取最新构建时间
            if build_info["build_files"]:
                build_info["last_build_time"] = build_info["build_files"][0]["modified_at"]
        
        return build_info
    except Exception as e:
        logger.error(f"获取构建信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取构建信息失败: {str(e)}")

@admin_router.get("/build/{filename}")
@require_permission("build.epub")
async def download_build_file(filename: str, request: Request):
    """下载构建文件"""
    try:
        from app.common import get_user_directory
        from pathlib import Path
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的构建目录
        user_build_dir = get_user_directory(session.username) / "build"
        file_path = user_build_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="构建文件不存在")
        
        # 根据文件扩展名设置合适的媒体类型
        media_type = "application/octet-stream"
        if filename.endswith('.epub'):
            media_type = "application/epub+zip"
        elif filename.endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.endswith('.html'):
            media_type = "text/html"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
    except Exception as e:
        logger.error(f"下载构建文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载构建文件失败: {str(e)}")

# 章节管理相关路由
@admin_router.get("/chapter-config")
@require_permission("content.edit")
async def get_chapter_config(request: Request):
    """获取章节配置"""
    try:
        import json
        from app.common import get_user_src_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的src目录
        user_src_dir = get_user_src_directory(session.username)
        config_path = user_src_dir / "chapter-config.json"
        
        if not config_path.exists():
            # 如果配置文件不存在，创建默认配置
            default_config = {"chapters": []}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return config
        
    except Exception as e:
        logger.error(f"获取章节配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取章节配置失败: {str(e)}")

@admin_router.post("/chapter-config")
@require_permission("content.edit")
async def save_chapter_config(request: Request):
    """保存章节配置"""
    try:
        import json
        from app.common import get_user_src_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取请求体
        body = await request.json()
        
        # 获取用户特定的src目录
        user_src_dir = get_user_src_directory(session.username)
        config_path = user_src_dir / "chapter-config.json"
        
        # 确保src目录存在
        user_src_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(body, f, indent=2, ensure_ascii=False)
        
        logger.info(f"用户 {session.username} 保存章节配置成功")
        
        return {
            "status": "success",
            "message": "章节配置保存成功"
        }
        
    except Exception as e:
        logger.error(f"保存章节配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存章节配置失败: {str(e)}")

@admin_router.post("/chapter-config/add")
@require_permission("content.edit")
async def add_chapter(request: Request):
    """添加新章节"""
    try:
        import json
        from app.common import get_user_src_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取请求体
        body = await request.json()
        title = body.get('title', '').strip()
        file = body.get('file', '').strip()
        
        if not title:
            raise HTTPException(status_code=400, detail="章节标题不能为空")
        
        if not file:
            raise HTTPException(status_code=400, detail="章节文件不能为空")
        
        # 获取用户特定的src目录
        user_src_dir = get_user_src_directory(session.username)
        config_path = user_src_dir / "chapter-config.json"
        
        # 读取现有配置
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"chapters": []}
        
        # 检查文件是否已存在
        for chapter in config["chapters"]:
            if chapter.get("file") == file:
                raise HTTPException(status_code=400, detail="该文件已被其他章节使用")
        
        # 添加新章节
        new_chapter = {
            "title": title,
            "file": file,
            "order": len(config["chapters"]) + 1
        }
        config["chapters"].append(new_chapter)
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"用户 {session.username} 添加章节成功: {title}")
        
        return {
            "status": "success",
            "message": "章节添加成功",
            "chapter": new_chapter
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加章节失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加章节失败: {str(e)}")

@admin_router.put("/chapter-config/{index}")
@require_permission("content.edit")
async def update_chapter(index: int, request: Request):
    """更新章节信息"""
    try:
        import json
        from app.common import get_user_src_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取请求体
        body = await request.json()
        title = body.get('title', '').strip()
        file = body.get('file', '').strip()
        
        if not title:
            raise HTTPException(status_code=400, detail="章节标题不能为空")
        
        if not file:
            raise HTTPException(status_code=400, detail="章节文件不能为空")
        
        # 获取用户特定的src目录
        user_src_dir = get_user_src_directory(session.username)
        config_path = user_src_dir / "chapter-config.json"
        
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="章节配置文件不存在")
        
        # 读取现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if index < 0 or index >= len(config["chapters"]):
            raise HTTPException(status_code=404, detail="章节索引无效")
        
        # 检查文件是否被其他章节使用
        for i, chapter in enumerate(config["chapters"]):
            if i != index and chapter.get("file") == file:
                raise HTTPException(status_code=400, detail="该文件已被其他章节使用")
        
        # 更新章节
        config["chapters"][index]["title"] = title
        config["chapters"][index]["file"] = file
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"用户 {session.username} 更新章节成功: {title}")
        
        return {
            "status": "success",
            "message": "章节更新成功",
            "chapter": config["chapters"][index]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新章节失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新章节失败: {str(e)}")

@admin_router.delete("/chapter-config/{index}")
@require_permission("content.edit")
async def delete_chapter(index: int, request: Request):
    """删除章节"""
    try:
        import json
        from app.common import get_user_src_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的src目录
        user_src_dir = get_user_src_directory(session.username)
        config_path = user_src_dir / "chapter-config.json"
        
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="章节配置文件不存在")
        
        # 读取现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if index < 0 or index >= len(config["chapters"]):
            raise HTTPException(status_code=404, detail="章节索引无效")
        
        # 删除章节
        deleted_chapter = config["chapters"].pop(index)
        
        # 重新排序
        for i, chapter in enumerate(config["chapters"]):
            chapter["order"] = i + 1
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"用户 {session.username} 删除章节成功: {deleted_chapter.get('title', '')}")
        
        return {
            "status": "success",
            "message": "章节删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除章节失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除章节失败: {str(e)}")

# 兼容前端的构建 API 调用
@admin_router.post("/build/{script_name}")
async def run_build_script(script_name: str, request: Request):
    """运行构建脚本（兼容前端调用）"""
    try:
        logger.debug(f"开始处理构建脚本请求: {script_name}")
        from app.common import get_user_src_directory, get_user_directory
        from pathlib import Path
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的目录
        user_src_dir = get_user_src_directory(session.username)
        user_build_dir = get_user_directory(session.username) / "build"
        user_build_dir.mkdir(parents=True, exist_ok=True)
        
        # 根据 script_name 检查对应权限并执行构建
        logger.debug("获取构建服务实例")
        build_service = get_build_service_instance()
        logger.debug(f"构建服务实例类型: {type(build_service)}")
        
        if script_name == "epub" or script_name == "build-epub.js" or script_name == "build":
            # 检查EPUB构建权限
            has_permission = await check_user_permission(session.username, "build.epub")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行EPUB构建")
            
            # 如果是生成所有格式，则同时构建 EPUB、PDF 和 HTML
            if script_name == "build":
                results = {}
                
                # 构建 EPUB
                logger.debug("开始构建EPUB")
                epub_result = await build_service.build_epub(src_dir=user_src_dir, build_dir=user_build_dir)
                results["epub"] = epub_result
                logger.debug("EPUB构建完成")
                
                # 检查是否有PDF构建权限
                has_pdf_permission = await check_user_permission(session.username, "build.pdf")
                if has_pdf_permission:
                    # 生成Pandoc版本的PDF
                    logger.debug("开始构建Pandoc PDF")
                    pdf_pandoc_result = await build_service.build_pdf(src_dir=user_src_dir, build_dir=user_build_dir)
                    results["pdf_pandoc"] = pdf_pandoc_result
                    logger.debug("Pandoc PDF构建完成")
                    
                    # 生成wkhtmltopdf版本的PDF
                    logger.debug("开始构建wkhtmltopdf PDF")
                    pdf_wkhtmltopdf_result = await build_service.build_pdf_with_wkhtmltopdf(src_dir=user_src_dir, build_dir=user_build_dir)
                    results["pdf_wkhtmltopdf"] = pdf_wkhtmltopdf_result
                    logger.debug("wkhtmltopdf PDF构建完成")
                
                # 构建 HTML（使用EPUB权限）
                logger.debug("开始构建HTML")
                html_result = await build_service.build_html(src_dir=user_src_dir, build_dir=user_build_dir)
                results["html"] = html_result
                logger.debug("HTML构建完成")
                
                # 返回所有结果
                success_count = sum(1 for r in results.values() if r.get("status") == "success")
                total_count = len(results)
                
                logger.debug(f"构建完成: {success_count}/{total_count} 成功")
                if success_count == total_count:
                    return {
                        "status": "success",
                        "message": f"所有格式构建成功 ({success_count}/{total_count})",
                        "results": results
                    }
                else:
                    return {
                        "status": "partial",
                        "message": f"部分格式构建成功 ({success_count}/{total_count})",
                        "results": results
                    }
            else:
                logger.debug("开始构建EPUB")
                result = await build_service.build_epub(src_dir=user_src_dir, build_dir=user_build_dir)
                logger.debug("EPUB构建完成")
        elif script_name == "pdf" or script_name == "build-pdf.js":
            # 检查PDF构建权限
            has_permission = await check_user_permission(session.username, "build.pdf")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行PDF构建")
            logger.debug("开始构建PDF")
            result = await build_service.build_pdf(src_dir=user_src_dir, build_dir=user_build_dir)
            logger.debug("PDF构建完成")
        elif script_name == "html" or script_name == "build-html.js":
            # 检查HTML构建权限（使用EPUB权限）
            has_permission = await check_user_permission(session.username, "build.epub")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行HTML构建")
            logger.debug("开始构建HTML")
            result = await build_service.build_html(src_dir=user_src_dir, build_dir=user_build_dir)
            logger.debug("HTML构建完成")
        elif script_name == "pdf-wkhtmltopdf":
            # 检查PDF构建权限
            has_permission = await check_user_permission(session.username, "build.pdf")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行PDF构建")
            logger.debug("开始构建wkhtmltopdf PDF")
            result = await build_service.build_pdf_with_wkhtmltopdf(src_dir=user_src_dir, build_dir=user_build_dir)
            logger.debug("wkhtmltopdf PDF构建完成")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的构建类型: {script_name}")
        
        logger.debug("构建脚本执行完成")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行构建脚本失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"构建失败: {str(e)}")

# EPUB相关路由
@admin_router.post("/epub/extract-info")
@require_permission("epub_conversion")
async def extract_epub_info(file: UploadFile = File(...), request: Request = None):
    """从上传的EPUB文件中提取信息"""
    try:
        import tempfile
        
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 提取EPUB信息
            epub_service = get_epub_service_instance()
            result = await epub_service.extract_epub_info(temp_file_path)
            return result
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"提取EPUB信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取EPUB信息失败: {str(e)}")

@admin_router.post("/epub/validate")
@require_permission("epub_conversion")
async def validate_epub_structure(file: UploadFile = File(...), request: Request = None):
    """验证上传的EPUB文件结构"""
    try:
        import tempfile
        
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 验证EPUB结构
            epub_service = get_epub_service_instance()
            result = await epub_service.validate_epub_structure(temp_file_path)
            return result
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"验证EPUB结构失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"验证EPUB结构失败: {str(e)}")

@admin_router.post("/epub/convert")
@require_permission("epub_conversion")
async def convert_epub_to_markdown(file: UploadFile = File(...), request: Request = None):
    """将上传的EPUB文件转换为Markdown格式"""
    try:
        import tempfile
        from app.common import get_user_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 获取用户特定的目录
            user_dir = get_user_directory(session.username)
            converted_dir = user_dir / "epub_converted"
            converted_dir.mkdir(parents=True, exist_ok=True)
            
            # 执行EPUB转换
            epub_service = get_epub_service_instance()
            result = await epub_service.convert_epub_to_markdown(temp_file_path, str(converted_dir))
            
            if result.get("status") == "success":
                # 将转换结果打包为ZIP文件
                import zipfile
                zip_path = converted_dir / "converted.zip"
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in converted_dir.rglob('*'):
                        if file_path.is_file() and file_path != zip_path:
                            # 计算相对路径，并在前面加上src/
                            arc_name = "src" / file_path.relative_to(converted_dir)
                            zipf.write(file_path, arc_name)
                
                result["download_available"] = True
                result["zip_file"] = str(zip_path)
                result["zip_size"] = zip_path.stat().st_size
            
            return result
            
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"EPUB转换失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"EPUB转换失败: {str(e)}")

@admin_router.get("/epub/download-converted")
@require_permission("epub_conversion")
async def download_converted_files(request: Request):
    """下载转换后的文件"""
    try:
        from app.common import get_user_directory
        
        # 获取会话信息
        session = get_session(request)
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户特定的转换目录
        user_dir = get_user_directory(session.username)
        converted_dir = user_dir / "epub_converted"
        zip_path = converted_dir / "converted.zip"
        
        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="转换文件不存在，请先进行转换")
        
        return FileResponse(
            path=zip_path,
            filename="epub_converted.zip",
            media_type="application/zip"
        )
        
    except Exception as e:
        logger.error(f"下载转换文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载转换文件失败: {str(e)}")

# 管理员登录相关路由
@admin_router.post("/login")
async def admin_login(request: Request):
    """管理员登录"""
    try:
        # 获取请求数据
        body = await request.json()
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        # 先尝试使用原始用户名查找
        query = admin_table.select().where(admin_table.c.username == username)
        admin_user = await database.fetch_one(query)
        
        # 如果找不到，且用户名是“markedit”，尝试查找super_admin_markedit
        actual_username = username
        if not admin_user and username == "markedit":
            prefixed_username = f"super_admin_{username}"
            query = admin_table.select().where(admin_table.c.username == prefixed_username)
            admin_user = await database.fetch_one(query)
            
            # 如果找到了，更新实际用户名
            if admin_user:
                actual_username = prefixed_username
                logger.info(f"管理员登录：{username} 映射到 {actual_username}")
        
        if not admin_user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 验证密码
        if not verify_password(password, admin_user["password"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 创建会话（使用实际的系统用户名）
        session_service = get_session_service()
        session_id = session_service.create_session(actual_username, user_type="admin")
        
        # 加载用户权限
        session = session_service.get_session_by_id(session_id)
        if session:
            await session_service.assign_default_user_role(actual_username)
            await session_service.load_user_permissions_and_roles(session)
        
        # 返回成功响应（显示的用户名不包含前缀）
        from fastapi.responses import JSONResponse
        display_username = username  # 始终显示原始输入的用户名
        response = JSONResponse({"message": "登录成功", "username": display_username})
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,  # 开发环境使用HTTP
            samesite="lax",
            max_age=86400  # 24小时
        )
        
        logger.info(f"管理员 {username} 登录成功")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员登录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

# 用户管理相关路由
@admin_router.get("/users")
@require_permission("user.list")
async def get_user_list(request: Request):
    """获取用户列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_user_list()
        return {"users": result}
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")

@admin_router.post("/users")
@require_permission("user.create")
async def create_user(request: Request):
    """创建新用户"""
    try:
        body = await request.json()
        username = body.get('username')
        password = body.get('password')
        theme = body.get('theme', 'default')
        
        if not username:
            raise HTTPException(status_code=400, detail="用户名不能为空")
        
        if not password:
            raise HTTPException(status_code=400, detail="密码不能为空")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.create_user(username, password, theme)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.put("/users/{user_id}")
@require_permission("user.edit")
async def update_user(user_id: int, request: Request):
    """更新用户信息"""
    try:
        body = await request.json()
        username = body.get('username')
        password = body.get('password')
        theme = body.get('theme')
        
        admin_service = get_admin_service_instance()
        result = await admin_service.update_user(user_id, username, password, theme)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/user/{user_id}")
@require_permission("user.delete")
async def delete_user(user_id: int, request: Request):
    """删除用户"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.delete_user(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 用户角色管理相关路由
@admin_router.get("/users/{user_id}/roles")
@require_permission("user.edit")
async def get_user_roles(user_id: int, request: Request):
    """获取用户的角色列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_user_roles(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取用户角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/users/{user_id}/roles")
@require_permission("user.edit")
async def assign_user_roles(user_id: int, request: Request):
    """为用户分配角色"""
    try:
        body = await request.json()
        role_ids = body.get('role_ids', [])
        
        admin_service = get_admin_service_instance()
        result = await admin_service.assign_user_roles(user_id, role_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"分配用户角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/users/{user_id}")
@require_permission("user.delete")
async def delete_user(user_id: int, request: Request):
    """删除用户"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.delete_user(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/users/{user_id}/roles/{role_name}")
@require_permission("user.edit")
async def remove_user_role(user_id: int, role_name: str, request: Request):
    """移除用户的特定角色"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.remove_user_role(user_id, role_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"移除用户角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 角色管理相关路由
@admin_router.get("/roles")
@require_permission("role.list")
async def get_roles(request: Request):
    """获取所有角色列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_roles()
        return {"roles": result}
    except Exception as e:
        logger.error(f"获取角色列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/roles")
@require_permission("role.create")
async def create_role(request: Request):
    """创建新角色"""
    try:
        body = await request.json()
        name = body.get('name')
        description = body.get('description', '')
        
        if not name:
            raise HTTPException(status_code=400, detail="角色名称不能为空")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.create_role(name, description)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.put("/roles/{role_id}")
@require_permission("role.edit")
async def update_role(role_id: int, request: Request):
    """更新角色信息"""
    try:
        body = await request.json()
        name = body.get('name')
        description = body.get('description')
        
        admin_service = get_admin_service_instance()
        result = await admin_service.update_role(role_id, name, description)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/roles/{role_id}")
@require_permission("role.delete")
async def delete_role(role_id: int, request: Request):
    """删除角色"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.delete_role(role_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 权限管理相关路由
@admin_router.get("/permissions")
@require_permission("permission.list")
async def get_permissions(request: Request):
    """获取所有权限列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_permissions()
        return {"permissions": result}
    except Exception as e:
        logger.error(f"获取权限列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/permissions")
@require_permission("permission.create")
async def create_permission(request: Request):
    """创建新权限"""
    try:
        body = await request.json()
        name = body.get('name')
        description = body.get('description', '')
        
        if not name:
            raise HTTPException(status_code=400, detail="权限名称不能为空")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.create_permission(name, description)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.put("/permissions/{permission_id}")
@require_permission("permission.edit")
async def update_permission(permission_id: int, request: Request):
    """更新权限信息"""
    try:
        body = await request.json()
        name = body.get('name')
        description = body.get('description')
        
        admin_service = get_admin_service_instance()
        result = await admin_service.update_permission(permission_id, name, description)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/permissions/{permission_id}")
@require_permission("permission.delete")
async def delete_permission(permission_id: int, request: Request):
    """删除权限"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.delete_permission(permission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 角色权限管理相关路由
@admin_router.get("/roles/{role_id}/permissions")
@require_permission("role.list")
async def get_role_permissions(role_id: int, request: Request):
    """获取角色的权限列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_role_permissions(role_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取角色权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/roles/{role_id}/permissions")
@require_permission("role.edit")
async def assign_role_permissions(role_id: int, request: Request):
    """为角色分配权限"""
    try:
        body = await request.json()
        permission_ids = body.get('permission_ids', [])
        
        admin_service = get_admin_service_instance()
        result = await admin_service.assign_role_permissions(role_id, permission_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"分配角色权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.delete("/roles/{role_id}/permissions/{permission_id}")
@require_permission("role.edit")
async def remove_role_permission(role_id: int, permission_id: int, request: Request):
    """移除角色的特定权限"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.remove_role_permission(role_id, permission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"移除角色权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 权限分组和层级管理相关路由
@admin_router.get("/permission-groups")
@require_permission("permission.list")
async def get_permission_groups(request: Request):
    """获取权限分组"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_permission_groups()
        return {"groups": result}
    except Exception as e:
        logger.error(f"获取权限分组失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/assignable-permissions")
@require_permission("permission.list")
async def get_assignable_permissions(request: Request):
    """获取可分配的权限列表（用于前端勾选）"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_assignable_permissions()
        return {"groups": result}
    except Exception as e:
        logger.error(f"获取可分配权限列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/role-hierarchy")
@require_permission("role.list")
async def get_role_hierarchy(request: Request):
    """获取角色层级结构"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_role_hierarchy()
        return {"hierarchy": result}
    except Exception as e:
        logger.error(f"获取角色层级失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 初始化默认角色和权限
@admin_router.post("/initialize-default-roles")
@require_permission("super_admin")
async def initialize_default_roles(request: Request):
    """初始化默认角色和权限"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.initialize_default_roles_and_permissions()
        return result
    except Exception as e:
        logger.error(f"初始化默认角色和权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 批量操作相关路由
@admin_router.post("/batch-assign-role")
@require_permission("user.edit")
async def batch_assign_users_to_role(request: Request):
    """批量为用户分配角色"""
    try:
        body = await request.json()
        user_ids = body.get('user_ids', [])
        role_id = body.get('role_id')
        
        if not user_ids or not role_id:
            raise HTTPException(status_code=400, detail="用户ID列表和角色ID不能为空")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.batch_assign_users_to_role(user_ids, role_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量分配角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/batch-remove-role")
@require_permission("user.edit")
async def batch_remove_users_from_role(request: Request):
    """批量移除用户角色"""
    try:
        body = await request.json()
        user_ids = body.get('user_ids', [])
        role_id = body.get('role_id')
        
        if not user_ids or not role_id:
            raise HTTPException(status_code=400, detail="用户ID列表和角色ID不能为空")
        
        admin_service = get_admin_service_instance()
        result = await admin_service.batch_remove_users_from_role(user_ids, role_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量移除角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 审计日志相关路由
@admin_router.get("/audit-log/permissions")
@require_permission("super_admin")
async def get_permission_audit_log(request: Request, days: int = 30, operation: str = None, 
                                 operator: str = None, target_type: str = None,
                                 limit: int = 100, offset: int = 0):
    """获取权限审计日志"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_permission_audit_log(
            days=days, operation=operation, operator=operator, 
            target_type=target_type, limit=limit, offset=offset
        )
        return {"logs": result}
    except Exception as e:
        logger.error(f"获取审计日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/audit-log/statistics")
@require_permission("super_admin")
async def get_audit_log_statistics(request: Request, days: int = 30):
    """获取审计日志统计信息"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_audit_log_statistics(days=days)
        return result
    except Exception as e:
        logger.error(f"获取审计统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/reset-password")
@require_permission("super_admin")
async def reset_admin_password(request: Request):
    """重置管理员密码"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.reset_admin_password()
        return result
    except Exception as e:
        logger.error(f"重置管理员密码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 统计信息相关路由
@admin_router.get("/stats")
@require_permission("admin_access")
async def get_admin_stats(request: Request):
    """获取管理面板统计信息"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_admin_stats()
        return result
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/users/{user_id}/reset-password")
@require_permission("user.edit")
async def reset_user_password(user_id: int, request: Request):
    """重置用户密码"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.reset_user_password(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"重置用户密码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 系统信息相关路由
@admin_router.get("/system/info")
@require_permission("admin_access")
async def get_system_info(request: Request):
    """获取系统信息"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_system_info()
        return result
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

# 权限测试相关路由
@admin_router.get("/test-permissions")
@require_permission("admin_access")
async def test_permissions(request: Request):
    """测试当前用户的权限"""
    try:
        session = get_session(request)
        
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 测试各种权限
        test_permissions = [
            "user.list", "user.create", "user.edit", "user.delete",
            "content.edit", "epub_conversion", "manual_backup",
            "admin_access", "super_admin"
        ]
        
        permission_results = {}
        for perm in test_permissions:
            has_perm = await check_user_permission(session.username, perm)
            permission_results[perm] = has_perm
        
        return {
            "username": session.username,
            "user_type": session.user_type,
            "roles": session.roles,
            "permissions": permission_results
        }
    except Exception as e:
        logger.error(f"测试权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试权限失败: {str(e)}")

@admin_router.post("/reload-user-permissions")
@require_permission("admin_access")
async def reload_user_permissions(request: Request):
    """重新加载所有用户权限"""
    try:
        from app.common import sessions, get_user_permissions, get_user_roles
        
        # 更新所有活跃会话的权限信息
        updated_count = 0
        session_proxy = sessions.sessions if hasattr(sessions, 'sessions') else sessions
        for session_id, session in session_proxy.items():
            if session.username:
                try:
                    session.roles = await get_user_roles(session.username)
                    session.permissions = await get_user_permissions(session.username)
                    session.last_permission_check = None  # 强制下次检查时更新
                    updated_count += 1
                except Exception as e:
                    logger.error(f"更新用户 {session.username} 权限失败: {str(e)}")
        
        return {
            "status": "success",
            "message": f"已更新 {updated_count} 个用户会话的权限信息"
        }
    except Exception as e:
        logger.error(f"重新加载用户权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重新加载用户权限失败: {str(e)}")

# 用户角色信息相关路由
@admin_router.get("/role-info")
async def get_role_info(request: Request):
    """获取当前用户的角色和权限信息"""
    try:
        from app.common import get_session_service, get_user_permissions, get_user_roles
        
        session_service = get_session_service()
        session = session_service.get_session(request)
        
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 获取用户权限和角色
        user_permissions = await get_user_permissions(session.username)
        user_roles = await get_user_roles(session.username)
        
        # 确定用户角色（向后兼容）
        role = "user"  # 默认角色
        if "super_admin" in user_permissions:
            role = "admin"  # 超级管理员显示为admin（向后兼容）
        elif "admin_access" in user_permissions:
            role = "admin"
        
        return {
            "role": role,
            "info": {
                "permissions": user_permissions,
                "roles": user_roles,
                "user_type": session.user_type or "user",
                "username": session.username  # 添加用户名信息
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色信息失败: {str(e)}")
        # 返回默认信息而不是抛出异常，避免阻塞前端
        return {
            "role": "user",
            "info": {
                "permissions": [],
                "roles": [],
                "user_type": "user",
                "username": None  # 添加默认用户名信息
            }
        }

# 章节配置相关路由已在上面定义

# Duplicate save_chapter_config function removed

# 权限检查相关路由
@admin_router.get("/check-permissions")
@require_permission("admin_access")
async def check_permissions(request: Request):
    """检查当前用户的所有权限"""
    try:
        session = get_session(request)
        
        if not session.username:
            raise HTTPException(status_code=401, detail="用户未登录")
        
        # 测试各种权限
        test_permissions_list = [
            "user.list", "user.create", "user.edit", "user.delete",
            "role.list", "role.create", "role.edit", "role.delete",
            "permission.list", "permission.create", "permission.edit", "permission.delete",
            "content.edit", "epub_conversion", "manual_backup",
            "admin_access", "super_admin", "system.backup", "system.config"
        ]
        
        permission_results = {}
        for perm in test_permissions_list:
            has_perm = await check_user_permission(session.username, perm)
            permission_results[perm] = has_perm
        
        return {
            "username": session.username,
            "user_type": session.user_type,
            "roles": session.roles,
            "permissions": permission_results
        }
    except Exception as e:
        logger.error(f"检查权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查权限失败: {str(e)}")

# 角色管理相关路由
@admin_router.get("/roles")
@require_permission("role.list")
async def get_roles_list(request: Request):
    """获取角色列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_role_list()
        return {"roles": result}
    except Exception as e:
        logger.error(f"获取角色列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")

@admin_router.get("/permissions")
@require_permission("permission.list")
async def get_permissions_list(request: Request):
    """获取权限列表"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_permission_list()
        return {"permissions": result}
    except Exception as e:
        logger.error(f"获取权限列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取权限列表失败: {str(e)}")

@admin_router.get("/assignable-permissions")
@require_permission("permission.list")
async def get_assignable_permissions(request: Request):
    """获取可分配的权限列表（按分组）"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.get_assignable_permissions()
        return result
    except Exception as e:
        logger.error(f"获取可分配权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取可分配权限失败: {str(e)}")

@admin_router.get("/audit-log/permissions")
@require_permission("permission.list")
async def get_audit_logs(request: Request):
    """获取权限相关的审计日志"""
    try:
        # 获取最近的审计日志
        query = audit_log_table.select().order_by(audit_log_table.c.timestamp.desc()).limit(100)
        logs = await database.fetch_all(query)
        
        # 格式化日志数据
        formatted_logs = []
        for log in logs:
            log_dict = dict(log)
            # 构建目标对象描述
            log_dict["target_object"] = f"{log['target_type']}:{log['target_name']}" if log['target_name'] else log['target_type']
            formatted_logs.append(log_dict)
        
        return {"logs": formatted_logs}
        
    except Exception as e:
        logger.error(f"获取审计日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/initialize-default-roles")
@require_permission("super_admin")
async def initialize_default_roles(request: Request):
    """初始化默认角色和权限"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.initialize_default_roles()
        return result
    except Exception as e:
        logger.error(f"初始化默认角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"初始化默认角色失败: {str(e)}")

@admin_router.get("/check-permission")
async def check_permission_endpoint(permission: str, request: Request):
    """检查当前用户权限（诊断用）"""
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        
        if not session.username:
            return {"has_permission": False, "error": "用户未登录"}
        
        has_permission = await check_user_permission(session.username, permission)
        return {
            "username": session.username,
            "permission": permission,
            "has_permission": has_permission
        }
        
    except Exception as e:
        logger.error(f"检查权限失败: {str(e)}")
        return {"has_permission": False, "error": str(e)}
# ==================== 超级管理员专用API ====================

@admin_router.get("/users")
@require_permission("user.view")
async def get_users(request: Request):
    """获取用户列表"""
    try:
        # 查询所有用户
        query = """
        SELECT u.id, u.username, u.email, u.is_active, u.created_at, u.last_login,
               GROUP_CONCAT(r.name) as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        GROUP BY u.id, u.username, u.email, u.is_active, u.created_at, u.last_login
        ORDER BY u.created_at DESC
        """
        
        result = await database.fetch_all(query)
        
        users = []
        for row in result:
            user_data = dict(row)
            user_data['roles'] = user_data['roles'].split(',') if user_data['roles'] else []
            users.append(user_data)
        
        return {"users": users}
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")

@admin_router.get("/roles")
@require_permission("role.view")
async def get_roles(request: Request):
    """获取角色列表"""
    try:
        # 查询所有角色及其权限数量
        query = """
        SELECT r.id, r.name, r.description, r.is_default,
               COUNT(rp.permission_id) as permission_count,
               COUNT(ur.user_id) as user_count
        FROM roles r
        LEFT JOIN role_permissions rp ON r.id = rp.role_id
        LEFT JOIN user_roles ur ON r.id = ur.role_id
        GROUP BY r.id, r.name, r.description, r.is_default
        ORDER BY r.created_at DESC
        """
        
        result = await database.fetch_all(query)
        
        roles = []
        for row in result:
            role_data = dict(row)
            
            # 获取角色的权限列表
            permissions_query = """
            SELECT p.id, p.name, p.description
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = :role_id
            """
            permissions = await database.fetch_all(permissions_query, {"role_id": role_data['id']})
            role_data['permissions'] = [dict(p) for p in permissions]
            
            roles.append(role_data)
        
        return {"roles": roles}
        
    except Exception as e:
        logger.error(f"获取角色列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")

@admin_router.get("/permissions")
@require_permission("permission.view")
async def get_permissions(request: Request):
    """获取权限列表"""
    try:
        query = """
        SELECT id, name, description, is_default, created_at
        FROM permissions
        ORDER BY name
        """
        
        result = await database.fetch_all(query)
        permissions = [dict(row) for row in result]
        
        return {"permissions": permissions}
        
    except Exception as e:
        logger.error(f"获取权限列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取权限列表失败: {str(e)}")

@admin_router.get("/roles/{role_id}/permissions")
@require_permission("role.view")
async def get_role_permissions(role_id: str, request: Request):
    """获取角色的权限"""
    try:
        query = """
        SELECT p.id, p.name, p.description
        FROM permissions p
        JOIN role_permissions rp ON p.id = rp.permission_id
        WHERE rp.role_id = :role_id
        """
        
        result = await database.fetch_all(query, {"role_id": role_id})
        permissions = [dict(row) for row in result]
        
        return {"permissions": permissions}
        
    except Exception as e:
        logger.error(f"获取角色权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取角色权限失败: {str(e)}")

@admin_router.post("/roles/{role_id}/permissions")
@require_permission("role.edit")
async def update_role_permissions(role_id: str, request: Request):
    """更新角色权限"""
    try:
        body = await request.json()
        permission_ids = body.get('permission_ids', [])
        
        # 删除现有权限
        delete_query = "DELETE FROM role_permissions WHERE role_id = :role_id"
        await database.execute(delete_query, {"role_id": role_id})
        
        # 添加新权限
        if permission_ids:
            insert_query = "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"
            for permission_id in permission_ids:
                await database.execute(insert_query, {
                    "role_id": role_id,
                    "permission_id": permission_id
                })
        
        # 记录审计日志
        session = get_session(request)
        await log_admin_action(
            session.username,
            "update_role_permissions",
            f"更新角色 {role_id} 的权限",
            request.client.host if request.client else "unknown"
        )
        
        return {"status": "success", "message": "角色权限更新成功"}
        
    except Exception as e:
        logger.error(f"更新角色权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新角色权限失败: {str(e)}")

@admin_router.delete("/users/{user_id}")
@require_permission("user.delete")
async def delete_user(user_id: str, request: Request):
    """删除用户"""
    try:
        # 检查用户是否存在
        user_query = "SELECT username FROM users WHERE id = :user_id"
        user = await database.fetch_one(user_query, {"user_id": user_id})
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 删除用户角色关联
        await database.execute("DELETE FROM user_roles WHERE user_id = :user_id", {"user_id": user_id})
        
        # 删除用户
        await database.execute("DELETE FROM users WHERE id = :user_id", {"user_id": user_id})
        
        # 记录审计日志
        session = get_session(request)
        await log_admin_action(
            session.username,
            "delete_user",
            f"删除用户 {user['username']}",
            request.client.host if request.client else "unknown"
        )
        
        return {"status": "success", "message": "用户删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")

@admin_router.post("/users/{user_id}/reset-password")
@require_permission("user.edit")
async def reset_user_password(user_id: str, request: Request):
    """重置用户密码"""
    try:
        import secrets
        import string
        
        # 生成随机密码
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # 更新密码
        hashed_password = hash_password(new_password)
        update_query = "UPDATE users SET password_hash = :password_hash WHERE id = :user_id"
        await database.execute(update_query, {
            "password_hash": hashed_password,
            "user_id": user_id
        })
        
        # 记录审计日志
        session = get_session(request)
        await log_admin_action(
            session.username,
            "reset_password",
            f"重置用户 {user_id} 的密码",
            request.client.host if request.client else "unknown"
        )
        
        return {"status": "success", "new_password": new_password}
        
    except Exception as e:
        logger.error(f"重置密码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")

@admin_router.get("/audit-logs")
@require_permission("system.audit")
async def get_audit_logs(request: Request, limit: int = 100, offset: int = 0):
    """获取审计日志"""
    try:
        query = """
        SELECT id, username, action, description, ip_address, created_at
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        result = await database.fetch_all(query, {"limit": limit, "offset": offset})
        logs = [dict(row) for row in result]
        
        # 获取总数
        count_query = "SELECT COUNT(*) as total FROM audit_logs"
        total_result = await database.fetch_one(count_query)
        total = total_result['total'] if total_result else 0
        
        return {"logs": logs, "total": total}
        
    except Exception as e:
        logger.error(f"获取审计日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {str(e)}")

@admin_router.get("/system-status")
@require_permission("system.monitor")
async def get_system_status(request: Request):
    """获取系统状态"""
    try:
        import psutil
        import time
        
        # 获取系统资源使用情况
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 计算运行时间
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = int(uptime_seconds // 3600)
        uptime_days = uptime_hours // 24
        uptime_hours = uptime_hours % 24
        
        uptime_str = f"{uptime_days}天 {uptime_hours}小时" if uptime_days > 0 else f"{uptime_hours}小时"
        
        # 计算系统健康度
        health = 100
        if cpu_usage > 80:
            health -= 20
        if memory.percent > 80:
            health -= 20
        if disk.percent > 80:
            health -= 20
        
        return {
            "cpu_usage": round(cpu_usage, 1),
            "memory_usage": round(memory.percent, 1),
            "disk_usage": round(disk.percent, 1),
            "health": max(health, 0),
            "uptime": uptime_str
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        # 返回默认值而不是抛出异常
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "health": 100,
            "uptime": "未知"
        }

@admin_router.get("/users/export")
@require_permission("user.export")
async def export_users(request: Request):
    """导出用户数据"""
    try:
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        # 查询用户数据
        query = """
        SELECT u.username, u.email, u.is_active, u.created_at, u.last_login,
               GROUP_CONCAT(r.name) as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        GROUP BY u.id, u.username, u.email, u.is_active, u.created_at, u.last_login
        ORDER BY u.created_at DESC
        """
        
        result = await database.fetch_all(query)
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow(['用户名', '邮箱', '状态', '注册时间', '最后登录', '角色'])
        
        # 写入数据行
        for row in result:
            writer.writerow([
                row['username'],
                row['email'] or '',
                '活跃' if row['is_active'] else '非活跃',
                row['created_at'] or '',
                row['last_login'] or '从未登录',
                row['roles'] or ''
            ])
        
        # 记录审计日志
        session = get_session(request)
        await log_admin_action(
            session.username,
            "export_users",
            "导出用户数据",
            request.client.host if request.client else "unknown"
        )
        
        # 返回CSV文件
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"}
        )
        
    except Exception as e:
        logger.error(f"导出用户数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出用户数据失败: {str(e)}")

# 辅助函数：记录管理员操作日志
async def log_admin_action(username: str, action: str, description: str, ip_address: str):
    """记录管理员操作到审计日志"""
    try:
        from datetime import datetime
        
        insert_query = """
        INSERT INTO audit_logs (username, action, description, ip_address, created_at)
        VALUES (:username, :action, :description, :ip_address, :created_at)
        """
        
        await database.execute(insert_query, {
            "username": username,
            "action": action,
            "description": description,
            "ip_address": ip_address,
            "created_at": datetime.now()
        })
        
    except Exception as e:
        logger.error(f"记录审计日志失败: {str(e)}")
        # 不抛出异常，避免影响主要操作