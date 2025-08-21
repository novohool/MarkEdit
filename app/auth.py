from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
import requests
import os
import logging
from typing import Optional

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub OAuth 配置
CLIENT_ID = os.getenv('GITHUB_APP_CLIENT_ID')
CLIENT_SECRET = os.getenv('GITHUB_APP_CLIENT_SECRET')
REDIRECT_URI = os.getenv('GITHUB_APP_REDIRECT_URI')

# 存储会话信息（实际生产环境建议用Redis等）
class SessionData(BaseModel):
    access_token: Optional[str] = None

sessions = {}

def get_session(request: Request) -> SessionData:
    """获取当前会话数据"""
    session_id = request.cookies.get("session_id", "default")
    if session_id not in sessions:
        sessions[session_id] = SessionData()
    return sessions[session_id]

def require_auth(request: Request, session: SessionData = Depends(get_session)) -> SessionData:
    """依赖项：检查用户是否已登录，未登录则重定向到登录页"""
    if not session.access_token:
        response = RedirectResponse(url="/login")
        return response
    return session

# 登录页面路由
def setup_auth_routes(app: FastAPI):
    @app.get("/login", response_class=HTMLResponse)
    def login_page_get(session: SessionData = Depends(get_session)):
        """登录页面：显示GitHub登录按钮"""
        # 如果已经登录，重定向到主页
        if session.access_token:
            return RedirectResponse(url="/")
        
        # 未登录，显示授权链接
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope=user:email"
        )
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>用户登录</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #1d5f82;
                }}
                .login-container {{
                    text-align: center;
                    padding: 2rem;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .login-button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #24292e;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                    transition: background-color 0.2s;
                }}
                .login-button:hover {{
                    background-color: #0a0c0d;
                }}
                h1 {{
                    color: #333;
                }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>欢迎使用我们的应用</h1>
                <p>请使用GitHub账户登录以继续</p>
                <a href="{auth_url}" class="login-button">使用GitHub登录</a>
            </div>
        </body>
        </html>
        """

    @app.post("/login")
    async def login_post(request: Request, session: SessionData = Depends(get_session)):
        """处理登录表单提交"""
        # 如果已经登录，重定向到主页
        if session.access_token:
            return RedirectResponse(url="/")
        
        # 重定向到GitHub OAuth授权页面
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope=user:email"
        )
        return RedirectResponse(url=auth_url, status_code=303)

    @app.get("/callback")
    def callback(code: str, request: Request, session: SessionData = Depends(get_session)):
        """处理GitHub回调，获取access_token"""
        logger.info(f"Received callback with code: {code}")
        
        try:
            # 用临时code换取access_token
            token_response = requests.post(
                "https://github.com/login/oauth/access_token",
                params={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": REDIRECT_URI
                },
                headers={"Accept": "application/json"}
            )
            
            logger.info(f"Token response status: {token_response.status_code}")
            logger.info(f"Token response content: {token_response.text}")
            
            # 检查响应状态
            if token_response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"GitHub API request failed with status {token_response.status_code}")
            
            # 解析JSON响应
            token_data = token_response.json()
            logger.info(f"Token data: {token_data}")
            
            # 检查是否获取到token
            access_token = token_data.get("access_token")
            if not access_token:
                error_description = token_data.get("error_description", "Unknown error")
                raise HTTPException(status_code=400, detail=f"获取token失败: {error_description}")

            # 存储token到会话
            session.access_token = access_token
            logger.info(f"Access token stored in session")
            
            response = RedirectResponse(url="/")
            # 设置会话Cookie（实际生产环境建议用安全的Cookie配置）
            response.set_cookie("session_id", "default", httponly=True)
            logger.info("Redirecting to home page")
            return response
        except Exception as e:
            logger.error(f"Callback processing failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"回调处理失败: {str(e)}")

    @app.get("/logout")
    def logout(request: Request, session: SessionData = Depends(get_session)):
        """退出登录：清除会话信息"""
        session.access_token = None
        response = RedirectResponse(url="/login")
        response.delete_cookie("session_id")
        return response

    # 添加一个中间件来检查用户是否已登录
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # 允许访问登录相关页面和静态资源，无需登录
        if (request.url.path.startswith("/login") or
            request.url.path.startswith("/callback") or
            request.url.path.startswith("/static") or
            request.url.path.startswith("/src") or
            request.url.path.startswith("/illustrations")):
            response = await call_next(request)
            return response
        
        # 检查会话
        session_id = request.cookies.get("session_id", "default")
        session = sessions.get(session_id, SessionData())
        
        # 如果没有访问令牌，重定向到登录页面
        if not session.access_token:
            # 特殊处理根路径，避免重定向循环
            if request.url.path == "/":
                # 重定向到登录页面
                return RedirectResponse(url="/login")
            else:
                # 对于其他路径，重定向到登录页面
                return RedirectResponse(url="/login")
        
        # 用户已登录，继续处理请求
        response = await call_next(request)
        return response