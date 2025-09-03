"""
Main page controller for MarkEdit application.

This module contains HTTP route handlers for main pages.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.common import get_session_service
from app.services.user_service import UserService
from app.utils.error_handler import (
    error_handler, ErrorCategory, ErrorLevel, 
    handle_controller_error, create_recovery_suggestions
)
import logging

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 创建路由器
main_router = APIRouter(tags=["main"])

logger = logging.getLogger(__name__)

async def _check_admin_access_permission(username: str) -> bool:
    """检查管理员访问权限"""
    from app.common import admin_table, database, check_user_permission
    
    # 超管用户直接通过
    if username == "markedit":
        return True
    
    # 检查admin表中的用户 - 尝试多种用户名格式
    admin_queries = [
        admin_table.select().where(admin_table.c.username == username),
        admin_table.select().where(admin_table.c.username == f"super_admin_{username}"),
        admin_table.select().where(admin_table.c.username == "super_admin_markedit")
    ]
    
    for query in admin_queries:
        admin_record = await database.fetch_one(query)
        if admin_record:
            return True
    
    # 检查具体权限
    return await check_user_permission(username, "admin_access")

def _render_access_denied_page(request: Request):
    """渲染访问被拒绝页面"""
    # 创建错误上下文和信息
    context = error_handler.create_error_context(request)
    error_info = error_handler.handle_exception(
        PermissionError("权限不足，无法访问角色权限管理功能"),
        context,
        ErrorCategory.AUTHORIZATION,
        user_message="权限不足，无法访问角色权限管理功能。请联系管理员分配相应权限。",
        recovery_suggestions=[
            "请联系管理员分配相应权限",
            "确认您的账户类型是否正确",
            "尝试重新登录后再试"
        ]
    )
    
    return error_handler.create_html_response(error_info, request)

def _render_error_page(request: Request, error_message: str):
    """渲染错误页面"""
    context = error_handler.create_error_context(request)
    error_info = error_handler.handle_exception(
        Exception(error_message),
        context,
        ErrorCategory.SYSTEM,
        user_message="系统访问失败，请重新登录",
        recovery_suggestions=[
            "请重新登录",
            "清除浏览器缓存后重试",
            "如果问题持续存在，请联系管理员"
        ]
    )
    
    return error_handler.create_html_response(error_info, request)

async def get_user_theme_simple(request: Request) -> str:
    """获取用户主题（简化版）"""
    try:
        # 直接从会话中获取主题，避免调用需要认证的服务
        from app.common import get_session_service
        session_service = get_session_service()
        session = session_service.get_session(request)
        # 对于未登录用户，session.theme可能为None，此时返回"default"
        return session.theme if session.theme is not None else "default"
    except:
        # 如果出现任何异常，返回默认主题
        return "default"

@main_router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页"""
    from app.common import get_user_permissions, get_session_service
    
    theme = await get_user_theme_simple(request)
    
    # 获取用户权限信息
    has_admin_access = False
    user_permissions = set()
    username = None
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        if session.username:
            username = session.username
            user_permissions = set(await get_user_permissions(username))
            has_admin_access = "admin_access" in user_permissions or "super_admin" in user_permissions
    except Exception as e:
        # 记录权限获取失败，但不影响页面加载
        logger.warning(f"获取用户权限失败: {str(e)}")
        has_admin_access = False
    
    # 创建permissions对象供header组件使用
    permissions = {
        'has_admin_access': has_admin_access,
        'has_super_admin': 'super_admin' in user_permissions
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "theme": theme,
        "has_admin_access": has_admin_access,
        "permissions": permissions,
        "username": username
    })



@main_router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """管理员登录页面"""
    # 超管登录页面固定使用default主题，避免在未登录状态下尝试获取用户主题
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "theme": "default"
    })

@main_router.get("/admin", response_class=HTMLResponse)
async def admin_home_page(request: Request):
    """系统管理页面 - 重新实现为统一的管理面板"""
    from app.common import get_user_permissions, get_session_service, check_user_permission
    
    theme = await get_user_theme_simple(request)
    
    # 获取用户会话和权限信息
    user_permissions = set()
    username = None
    registration_time = None
    last_login_time = None
    current_theme = theme
    user_role = "普通用户"
    
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        
        # 检查会话是否有效
        if not session or not session.username:
            return templates.TemplateResponse("admin_login.html", {
                "request": request,
                "theme": "default",
                "error": "请先登录"
            })
        
        username = session.username
        user_permissions = set(await get_user_permissions(username))
        
        # 检查用户是否有管理权限
        has_admin_permission = await _check_admin_access_permission(username)
        
        if not has_admin_permission:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "theme": theme,
                "error": {
                    "title": "权限不足",
                    "message": "权限不足，无法访问系统管理功能。请联系管理员分配相应权限。",
                    "suggestions": [
                        "请联系管理员分配相应权限",
                        "确认您的账户类型是否正确",
                        "尝试重新登录后再试"
                    ]
                }
            })
        
        # 获取用户注册时间和最后登录时间
        from app.models import user_table, database
        query = user_table.select().where(user_table.c.username == username)
        user_record = await database.fetch_one(query)
        if user_record:
            registration_time = user_record["created_at"]
            last_login_time = user_record["login_time"]
            current_theme = user_record["theme"] if user_record["theme"] else theme
            
            # 确定用户角色
            from app.common import get_user_roles
            user_roles = await get_user_roles(username)
            if user_roles:
                user_role = ", ".join(user_roles)
            elif "super_admin" in user_permissions:
                user_role = "超级管理员"
            elif "admin_access" in user_permissions:
                user_role = "管理员"
                
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "theme": "default",
            "error": "访问失败，请重新登录"
        })
    
    # 检查各种功能权限 - 超级管理员专用
    permissions = {
        'has_admin_access': 'admin_access' in user_permissions or 'super_admin' in user_permissions,
        'has_super_admin': 'super_admin' in user_permissions,
        'has_user_management': 'user.view' in user_permissions or 'super_admin' in user_permissions,
        'has_role_management': 'role.view' in user_permissions or 'super_admin' in user_permissions,
        'has_permission_management': 'permission.view' in user_permissions or 'super_admin' in user_permissions,
        'has_system_config': 'system.config' in user_permissions or 'super_admin' in user_permissions,
        'has_audit_logs': 'system.audit' in user_permissions or 'super_admin' in user_permissions,
        'has_backup_management': 'backup.manage' in user_permissions or 'super_admin' in user_permissions,
        'has_system_maintenance': 'system.monitor' in user_permissions or 'super_admin' in user_permissions,
        # 保留原有权限以兼容
        'has_content_edit': 'content.edit' in user_permissions,
        'has_epub_conversion': 'epub_conversion' in user_permissions,
        'has_manual_backup': 'manual_backup' in user_permissions,
        'has_build_epub': 'build.epub' in user_permissions,
        'has_build_pdf': 'build.pdf' in user_permissions
    }
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "theme": theme,
        "username": username,
        "registration_time": registration_time,
        "last_login_time": last_login_time,
        "current_theme": current_theme,
        "user_role": user_role,
        "permissions": permissions,
        "user_permissions": list(user_permissions)
    })



@main_router.get("/admin/debug", response_class=HTMLResponse)
async def admin_debug_page(request: Request):
    """管理员诊断页面"""
    from app.common import get_user_permissions, get_session_service, check_user_permission
    
    try:
        session_service = get_session_service()
        session_id = request.cookies.get("session_id")
        
        if not session_id or session_id not in session_service.sessions:
            return templates.TemplateResponse("admin_debug.html", {
                "request": request,
                "username": None,
                "user_permissions": [],
                "permissions": {}
            })
        
        session = session_service.sessions[session_id]
        username = session.username
        
        # 获取用户权限
        user_permissions = []
        permissions = {}
        
        if username:
            try:
                user_permissions = list(await get_user_permissions(username))
                permissions = {
                    'has_admin_access': 'admin_access' in user_permissions or 'super_admin' in user_permissions,
                    'has_super_admin': 'super_admin' in user_permissions,
                    'has_user_list': 'user.list' in user_permissions,
                    'has_role_list': 'role.list' in user_permissions,
                    'has_permission_list': 'permission.list' in user_permissions
                }
            except Exception as e:
                logger.error(f"获取用户权限失败: {str(e)}")
        
        return templates.TemplateResponse("admin_debug.html", {
            "request": request,
            "username": username,
            "user_permissions": user_permissions,
            "permissions": permissions
        })
        
    except Exception as e:
        logger.error(f"诊断页面错误: {str(e)}")
        return templates.TemplateResponse("admin_debug.html", {
            "request": request,
            "username": None,
            "user_permissions": [],
            "permissions": {},
            "error": str(e)
        })


        error_info = error_handler.handle_exception(
            Exception("用户未登录"),
            context,
            ErrorCategory.AUTHENTICATION,
            user_message="请先登录后再访问错误监控面板",
            recovery_suggestions=[
                "点击登录按钮进行登录",
                "检查登录凭据是否正确"
            ]
        )
        return error_handler.create_html_response(error_info, request, "admin_login.html")
    
    # 检查管理员权限
    has_permission = await _check_admin_access_permission(session.username)
    if not has_permission:
        return _render_access_denied_page(request)
    
    # 错误监控面板已移除，重定向到管理面板
    return RedirectResponse(url="/admin", status_code=302)

@main_router.get("/myaccount", response_class=HTMLResponse)
async def read_myaccount(request: Request):
    """我的账户页面"""
    theme = await get_user_theme_simple(request)
    return templates.TemplateResponse("myaccount.html", {
        "request": request,
        "theme": theme
    })

@main_router.get("/epub-viewer.html", response_class=HTMLResponse)
async def read_epub_viewer(request: Request):
    """EPUB查看器页面"""
    from app.common import get_user_permissions, get_session_service
    
    try:
        theme = await get_user_theme_simple(request)
    except Exception as e:
        # 如果获取主题时出现异常，使用默认主题
        logger.warning(f"获取用户主题时出现异常: {str(e)}")
        theme = "default"
    
    # 获取用户权限信息
    has_admin_access = False
    user_permissions = set()
    username = None
    
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        if session and session.username:
            username = session.username
            user_permissions = set(await get_user_permissions(username))
            has_admin_access = "admin_access" in user_permissions or "super_admin" in user_permissions
    except Exception as e:
        # 记录权限获取失败，但不影响页面加载
        logger.warning(f"获取用户权限失败: {str(e)}")
        has_admin_access = False
    
    # 创建permissions对象供header组件使用
    permissions = {
        'has_admin_access': has_admin_access,
        'has_super_admin': 'super_admin' in user_permissions
    }
    
    return templates.TemplateResponse("epub-viewer.html", {
        "request": request,
        "theme": theme,
        "has_admin_access": has_admin_access,
        "permissions": permissions,
        "username": username
    })

@main_router.get("/epub-proxy/{file_path:path}")
@main_router.head("/epub-proxy/{file_path:path}")
async def epub_proxy(file_path: str, request: Request):
    """EPUB文件代理端点，为epub.js提供无认证访问"""
    from app.common import get_session_service
    from fastapi.responses import FileResponse, Response
    from pathlib import Path
    import os
    
    try:
        # 检查用户认证
        session_service = get_session_service()
        session = session_service.get_session(request)
        
        if not session or not session.username:
            raise HTTPException(status_code=401, detail="需要登录才能访问EPUB文件")
        
        # 直接构建文件路径，避免通过文件服务
        from app.common import get_user_directory
        user_dir = get_user_directory(session.username)
        file_full_path = user_dir / "build" / file_path
        
        logger.info(f"EPUB代理访问: {file_full_path}")
        
        # 检查文件是否存在
        if not file_full_path.exists():
            logger.error(f"EPUB文件不存在: {file_full_path}")
            raise HTTPException(status_code=404, detail=f"EPUB文件不存在: {file_path}")
        
        # 检查文件是否在允许的目录内
        if not str(file_full_path).startswith(str(user_dir / "build")):
            logger.error(f"EPUB文件路径不安全: {file_full_path}")
            raise HTTPException(status_code=403, detail="文件路径不被允许")
        
        # 设置CORS头部，允许epub.js访问
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': '*',
            'Cache-Control': 'public, max-age=3600',
            'Accept-Ranges': 'bytes'
        }
        
        # 确定媒体类型
        media_type = "application/epub+zip" if file_path.endswith('.epub') else "application/octet-stream"
        
        # 对于HEAD请求，只返回头部信息
        if request.method == "HEAD":
            file_size = file_full_path.stat().st_size
            headers['Content-Length'] = str(file_size)
            return Response(headers=headers, media_type=media_type)
        
        # 对于GET请求，使用FileResponse直接返回文件
        return FileResponse(
            path=str(file_full_path),
            media_type=media_type,
            headers=headers,
            filename=file_path.split('/')[-1]
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EPUB代理错误: {str(e)}")
        raise HTTPException(status_code=500, detail="EPUB文件访问失败")