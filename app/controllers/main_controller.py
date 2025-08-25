"""
Main page controller for MarkEdit application.

This module contains HTTP route handlers for main pages.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.common import get_session_service
from app.services.user_service import UserService

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 创建路由器
main_router = APIRouter(tags=["main"])

async def get_user_theme_simple(request: Request) -> str:
    """获取用户主题（简化版）"""
    try:
        user_service = UserService()
        result = await user_service.get_user_theme(request)
        return result.get("theme", "default")
    except:
        return "default"

@main_router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页"""
    from app.common import get_user_permissions, get_session_service
    
    theme = await get_user_theme_simple(request)
    
    # 获取用户权限信息
    has_admin_access = False
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        if session.username:
            user_permissions = await get_user_permissions(session.username)
            has_admin_access = "admin_access" in user_permissions or "super_admin" in user_permissions
    except Exception:
        # 如果获取权限失败，默认为普通用户
        has_admin_access = False
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "theme": theme,
        "has_admin_access": has_admin_access
    })

@main_router.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """仪表板页面 - 根据用户权限显示不同内容"""
    from app.common import get_user_permissions, get_session_service, check_user_permission
    
    theme = await get_user_theme_simple(request)
    
    # 获取用户会话和权限信息
    user_permissions = set()
    username = None
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        if session.username:
            username = session.username
            user_permissions = set(await get_user_permissions(username))
    except Exception:
        # 如果获取权限失败，默认为空权限
        pass
    
    # 检查各种功能权限
    permissions = {
        'has_admin_access': 'admin_access' in user_permissions or 'super_admin' in user_permissions,
        'has_super_admin': 'super_admin' in user_permissions,
        'has_content_edit': 'content.edit' in user_permissions,
        'has_epub_conversion': 'epub_conversion' in user_permissions,
        'has_manual_backup': 'manual_backup' in user_permissions,
        'has_build_epub': 'build.epub' in user_permissions,
        'has_build_pdf': 'build.pdf' in user_permissions,
        'has_system_config': 'system.config' in user_permissions,
        'has_user_management': 'user.list' in user_permissions,
        'has_role_management': 'role.list' in user_permissions,
        'has_permission_management': 'permission.list' in user_permissions
    }
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "theme": theme,
        "username": username,
        "permissions": permissions,
        "user_permissions": list(user_permissions)
    })

@main_router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """管理员登录页面"""
    theme = await get_user_theme_simple(request)
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "theme": theme
    })

@main_router.get("/admin", response_class=HTMLResponse)
async def admin_home_page(request: Request):
    """管理员首页"""
    theme = await get_user_theme_simple(request)
    return templates.TemplateResponse("admin_home.html", {
        "request": request,
        "theme": theme
    })

@main_router.get("/admin/role-permission", response_class=HTMLResponse)
async def role_permission_management_page(request: Request):
    """角色权限管理页面"""
    from app.common import get_user_permissions, get_session_service, check_user_permission
    
    # 检查用户是否有管理权限
    try:
        session_service = get_session_service()
        session = session_service.get_session(request)
        if not session.username:
            return templates.TemplateResponse("admin_login.html", {
                "request": request,
                "theme": "default",
                "error": "请先登录"
            })
        
        # 检查用户是否有管理权限
        has_admin_permission = await check_user_permission(session.username, "admin_access") or \
                              await check_user_permission(session.username, "super_admin")
        
        if not has_admin_permission:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "theme": "default",
                "error": "权限不足，无法访问管理功能"
            })
        
        theme = await get_user_theme_simple(request)
        return templates.TemplateResponse("role_permission_management.html", {
            "request": request,
            "theme": theme
        })
        
    except Exception as e:
        theme = await get_user_theme_simple(request)
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "theme": theme,
            "error": "访问失败，请重新登录"
        })

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
    theme = await get_user_theme_simple(request)
    return templates.TemplateResponse("epub-viewer.html", {
        "request": request,
        "theme": theme
    })