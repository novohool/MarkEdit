"""
Authentication compatibility module for MarkEdit application.

This module provides backward compatibility by exposing components through the common module.
"""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
import logging
from typing import Optional

# 导入公共模块
from app.common import (
    SessionData, get_session_service, get_oauth_service,
    get_session, require_auth_session, require_permission, require_role,
    require_admin, require_super_admin, optional_auth,
    check_user_permission, get_user_permissions, get_user_roles,
    assign_default_user_role, sessions, update_session_permissions,
    load_user_permissions_and_roles, copy_default_files_to_user_directory,
    CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
)

# 设置日志记录
logger = logging.getLogger(__name__)

# ==========================================
# 向后兼容性接口
# 这些函数重新导向到公共模块
# ==========================================

def require_auth(request: Request, session: SessionData = Depends(get_session)) -> SessionData:
    """依赖项：检查用户是否已登录，未登录则重定向到登录页（向后兼容）"""
    return get_session_service().require_auth(request, session)

# ==========================================
# FastAPI 路由设置
# ==========================================

def setup_auth_routes(app: FastAPI):
    """设置认证相关路由"""
    # 注意：启动和关闭事件已移至 main.py，避免重复注册

    @app.get("/login", response_class=HTMLResponse)
    def login_page_get(session: SessionData = Depends(get_session)):
        """登录页面：显示GitHub登录按钮"""
        oauth_service = get_oauth_service()
        return oauth_service.render_login_page(session)

    @app.post("/login")
    async def login_post(request: Request, session: SessionData = Depends(get_session)):
        """处理登录表单提交"""
        oauth_service = get_oauth_service()
        return oauth_service.handle_login_post(session)

    @app.get("/callback")
    async def callback(code: str, request: Request, state: str = None, session: SessionData = Depends(get_session)):
        """处理GitHub回调，获取access_token"""
        try:
            logger.info(f"OAuth callback received - code: {code[:10] if code else 'None'}..., state: {state}")
            logger.debug(f"Full request URL: {request.url}")
            logger.debug(f"Request query params: {dict(request.query_params)}")
            
            if not code:
                logger.error("No authorization code received in callback")
                raise HTTPException(status_code=400, detail="未收到授权码")
            
            oauth_service = get_oauth_service()
            result = await oauth_service.handle_oauth_callback(code, request, session)
            logger.info("OAuth callback processed successfully")
            return result
            
        except HTTPException as e:
            logger.error(f"HTTPException in callback route: {e.status_code} - {e.detail}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in callback route: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="回调处理失败")

    @app.get("/logout")
    def logout(request: Request, session: SessionData = Depends(get_session)):
        """退出登录：清除会话信息"""
        oauth_service = get_oauth_service()
        return oauth_service.handle_logout(request, session)

    # 添加认证中间件
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """认证中间件"""
        oauth_service = get_oauth_service()
        return await oauth_service.auth_middleware(request, call_next)