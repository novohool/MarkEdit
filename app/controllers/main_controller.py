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
async def read_admin(request: Request):
    """仪表板页面"""
    theme = await get_user_theme_simple(request)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "theme": theme
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