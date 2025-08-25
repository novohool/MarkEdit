"""
Admin controller for MarkEdit application.

This module contains route handlers for admin operations.
"""
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
    admin_table, database, get_user_src_directory, get_user_directory
)

logger = logging.getLogger(__name__)

# 创建路由器
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# 使用公共模块的服务实例获取器
def get_admin_service_instance():
    return get_admin_service()

def get_build_service_instance():
    return get_build_service()

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
async def read_admin_file(file_name: str, request: Request):
    """读取管理文件的内容"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.read_admin_file(file_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"读取管理文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

@admin_router.post("/file/{file_name}")
@require_permission("system.config")
async def save_admin_file(file_name: str, request: Request):
    """保存管理文件的内容"""
    try:
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"保存管理文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

# 备份管理相关路由
@admin_router.post("/backup")
async def create_backup(session: SessionData = Depends(check_backup_permission)):
    """创建备份"""
    try:
        admin_service = get_admin_service_instance()
        result = await admin_service.create_backup(session.username)
        return result
    except Exception as e:
        logger.error(f"创建备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        result = await build_service.build_pdf(src_dir=user_src_dir, build_dir=user_build_dir)
        return result
    except Exception as e:
        logger.error(f"构建PDF失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"构建PDF失败: {str(e)}")

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

# 兼容前端的构建 API 调用
@admin_router.post("/build/{script_name}")
async def run_build_script(script_name: str, request: Request):
    """运行构建脚本（兼容前端调用）"""
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
        
        # 根据 script_name 检查对应权限并执行构建
        build_service = get_build_service_instance()
        
        if script_name == "epub" or script_name == "build-epub.js" or script_name == "build":
            # 检查EPUB构建权限
            has_permission = await check_user_permission(session.username, "build.epub")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行EPUB构建")
            
            # 如果是生成所有格式，则同时构建 EPUB、PDF 和 HTML
            if script_name == "build":
                results = {}
                
                # 构建 EPUB
                epub_result = await build_service.build_epub(src_dir=user_src_dir, build_dir=user_build_dir)
                results["epub"] = epub_result
                
                # 检查是否有PDF构建权限
                has_pdf_permission = await check_user_permission(session.username, "build.pdf")
                if has_pdf_permission:
                    pdf_result = await build_service.build_pdf(src_dir=user_src_dir, build_dir=user_build_dir)
                    results["pdf"] = pdf_result
                
                # 构建 HTML（使用EPUB权限）
                html_result = await build_service.build_html(src_dir=user_src_dir, build_dir=user_build_dir)
                results["html"] = html_result
                
                # 返回所有结果
                success_count = sum(1 for r in results.values() if r.get("status") == "success")
                total_count = len(results)
                
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
                result = await build_service.build_epub(src_dir=user_src_dir, build_dir=user_build_dir)
        elif script_name == "pdf" or script_name == "build-pdf.js":
            # 检查PDF构建权限
            has_permission = await check_user_permission(session.username, "build.pdf")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行PDF构建")
            result = await build_service.build_pdf(src_dir=user_src_dir, build_dir=user_build_dir)
        elif script_name == "html" or script_name == "build-html.js":
            # 检查HTML构建权限（使用EPUB权限）
            has_permission = await check_user_permission(session.username, "build.epub")
            if not has_permission:
                raise HTTPException(status_code=403, detail="权限不足，无法执行HTML构建")
            result = await build_service.build_html(src_dir=user_src_dir, build_dir=user_build_dir)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的构建类型: {script_name}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行构建脚本失败: {str(e)}")
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
        
        # 查询管理员用户
        query = admin_table.select().where(admin_table.c.username == username)
        admin_user = await database.fetch_one(query)
        
        if not admin_user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 验证密码
        if not verify_password(password, admin_user["password"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 创建会话
        session_service = get_session_service()
        session_id = session_service.create_session(username, user_type="admin")
        
        # 加载用户权限
        session = session_service.get_session_by_id(session_id)
        if session:
            await session_service.assign_default_user_role(username)
            await session_service.load_user_permissions_and_roles(session)
        
        # 返回成功响应
        from fastapi.responses import JSONResponse
        response = JSONResponse({"message": "登录成功", "username": username})
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
                "user_type": session.user_type or "user"
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
                "user_type": "user"
            }
        }

# 章节配置相关路由
@admin_router.get("/chapter-config")
async def get_chapter_config(request: Request):
    """获取章节配置"""
    try:
        from pathlib import Path
        import json
        
        # 章节配置文件路径
        config_path = Path("src/chapter-config.json")
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return config_data
        else:
            # 如果配置文件不存在，返回默认配置
            return {"chapters": []}
    except Exception as e:
        logger.error(f"获取章节配置失败: {str(e)}")
        # 返回默认配置而不是抛出异常
        return {"chapters": []}

@admin_router.post("/chapter-config")
@require_permission("content.edit")
async def save_chapter_config(request: Request):
    """保存章节配置"""
    try:
        from pathlib import Path
        import json
        
        # 获取请求体
        config_data = await request.json()
        
        # 章节配置文件路径
        config_path = Path("src/chapter-config.json")
        
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        return {"status": "success", "message": "章节配置保存成功"}
    except Exception as e:
        logger.error(f"保存章节配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存章节配置失败: {str(e)}")

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