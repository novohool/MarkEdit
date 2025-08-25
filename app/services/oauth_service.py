"""
OAuth service for MarkEdit application.

This module contains business logic for OAuth authentication including:
- GitHub OAuth integration
- Token management
- User authentication flow
"""
import os
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from app.common import (
    SessionData, OAuthConfig,
    database, user_table, admin_table,
    get_session_service, hash_password,
    copy_default_files_to_user_directory
)

logger = logging.getLogger(__name__)

class OAuthService:
    """OAuth认证服务类"""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=os.getenv('GITHUB_APP_CLIENT_ID'),
            client_secret=os.getenv('GITHUB_APP_CLIENT_SECRET'),
            redirect_uri=os.getenv('GITHUB_APP_REDIRECT_URI')
        )
    
    def is_configured(self) -> bool:
        """检查OAuth是否已配置"""
        configured = self.config.is_configured
        logger.debug(f"OAuth configuration check:")
        logger.debug(f"  Client ID: {'SET' if self.config.client_id else 'MISSING'}")
        logger.debug(f"  Client Secret: {'SET' if self.config.client_secret else 'MISSING'}")
        logger.debug(f"  Redirect URI: {self.config.redirect_uri or 'MISSING'}")
        logger.debug(f"  Overall configured: {configured}")
        return configured
    
    def get_authorization_url(self, state: str = None) -> str:
        """获取GitHub授权URL"""
        if not self.is_configured():
            raise ValueError("GitHub OAuth未配置")
        
        params = {
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'scope': 'user:email'
        }
        
        if state:
            params['state'] = state
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    async def handle_oauth_callback(self, code: str, request: Request, session: SessionData = None) -> RedirectResponse:
        """处理OAuth回调"""
        try:
            logger.info(f"Starting OAuth callback processing with code: {code[:10]}...")
            logger.debug(f"Full callback URL: {request.url}")
            logger.debug(f"Request headers: {dict(request.headers)}")
            
            # 检查OAuth配置
            if not self.is_configured():
                logger.error("GitHub OAuth not configured")
                logger.error(f"Client ID: {'configured' if self.config.client_id else 'missing'}")
                logger.error(f"Client Secret: {'configured' if self.config.client_secret else 'missing'}")
                logger.error(f"Redirect URI: {self.config.redirect_uri or 'missing'}")
                raise HTTPException(status_code=500, detail="GitHub OAuth未配置")
            
            logger.debug(f"OAuth config - Client ID: {self.config.client_id[:8] if self.config.client_id else 'None'}...")
            logger.debug(f"OAuth config - Redirect URI: {self.config.redirect_uri}")
            
            # 交换访问令牌
            logger.info("Exchanging authorization code for access token")
            token_data = await self._exchange_code_for_token(code)
            access_token = token_data.get('access_token')
            
            if not access_token:
                logger.error("No access token received from GitHub")
                logger.error(f"Token response data: {token_data}")
                raise HTTPException(status_code=400, detail="获取访问令牌失败")
            
            logger.info("Access token received successfully")
            logger.debug(f"Token type: {token_data.get('token_type', 'unknown')}")
            logger.debug(f"Token scope: {token_data.get('scope', 'unknown')}")
            
            # 获取用户信息
            logger.info("Fetching user information from GitHub")
            user_info = await self._get_user_info(access_token)
            username = user_info.get('login')
            
            if not username:
                logger.error("No username found in user info")
                logger.error(f"User info received: {user_info}")
                raise HTTPException(status_code=400, detail="获取用户信息失败")
            
            logger.info(f"Processing login for user: {username}")
            logger.debug(f"User ID: {user_info.get('id')}")
            logger.debug(f"User email: {user_info.get('email', 'not provided')}")
            logger.debug(f"User name: {user_info.get('name', 'not provided')}")
            
            # 创建或更新用户
            logger.info("Creating or updating user in database")
            await self._create_or_update_user(username, user_info)
            
            # 创建会话
            logger.info("Creating user session")
            session_service = get_session_service()
            session_id = session_service.create_session(username)
            logger.debug(f"Created session ID: {session_id}")
            
            # 加载用户权限
            logger.info("Loading user permissions and roles")
            session = session_service.get_session_by_id(session_id)
            if session:
                await session_service.assign_default_user_role(username)
                await session_service.load_user_permissions_and_roles(session)
                logger.debug(f"User roles: {session.roles}")
                logger.debug(f"User permissions: {list(session.permissions)[:10]}{'...' if len(session.permissions) > 10 else ''}")
            else:
                logger.warning(f"Could not retrieve session for user {username}")
            
            # 复制默认文件到用户目录
            logger.info("Setting up user directory")
            copy_default_files_to_user_directory(username)
            
            # 创建重定向响应
            logger.info("Creating redirect response")
            response = RedirectResponse(url="/")
            response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                secure=False,  # 开发环境使用HTTP，生产环境应设为True
                samesite="lax",
                max_age=86400  # 24小时
            )
            
            logger.info(f"用户 {username} 通过GitHub OAuth登录成功")
            return response
            
        except HTTPException as e:
            logger.error(f"HTTPException in OAuth callback: {e.status_code} - {e.detail}")
            # 重新抛出HTTPException
            raise
        except Exception as e:
            logger.error(f"OAuth回调处理失败: {str(e)}", exc_info=True)
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception args: {e.args}")
            # 为用户提供更友好的错误信息
            error_msg = f"登录过程中发生错误: {str(e)}"
            raise HTTPException(status_code=500, detail=error_msg)
    
    async def _exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """交换授权码获取访问令牌"""
        token_url = "https://github.com/login/oauth/access_token"
        
        data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'code': code,
            'redirect_uri': self.config.redirect_uri
        }
        
        headers = {'Accept': 'application/json'}
        
        logger.debug(f"Token exchange request to: {token_url}")
        logger.debug(f"Request data: {dict(data, client_secret='***')}")
        logger.debug(f"Request headers: {headers}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("Sending token exchange request to GitHub")
                response = await client.post(token_url, data=data, headers=headers)
                
                logger.debug(f"GitHub response status: {response.status_code}")
                logger.debug(f"GitHub response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                token_data = response.json()
                
                logger.debug(f"GitHub response body: {dict(token_data, access_token='***' if 'access_token' in token_data else token_data.get('access_token'))}")
                
                # 检查是否有错误
                if 'error' in token_data:
                    error_desc = token_data.get('error_description', token_data['error'])
                    logger.error(f"GitHub OAuth token exchange failed: {error_desc}")
                    logger.error(f"Full error response: {token_data}")
                    raise HTTPException(status_code=400, detail=f"OAuth认证失败: {error_desc}")
                
                logger.info("Successfully exchanged code for access token")
                return token_data
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during token exchange: {e}")
            raise HTTPException(status_code=500, detail="GitHub服务器响应超时")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token exchange: {e}")
            logger.error(f"Response content: {e.response.content if hasattr(e, 'response') else 'N/A'}")
            raise HTTPException(status_code=500, detail="无法获取访问令牌")
        except httpx.RequestError as e:
            logger.error(f"Request error during token exchange: {e}")
            raise HTTPException(status_code=500, detail="网络连接错误")
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="OAuth认证过程中发生错误")
    
    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """使用访问令牌获取用户信息"""
        user_url = "https://api.github.com/user"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        logger.debug(f"User info request to: {user_url}")
        logger.debug(f"Request headers: {dict(headers, Authorization='Bearer ***')}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("Sending user info request to GitHub")
                response = await client.get(user_url, headers=headers)
                
                logger.debug(f"GitHub user API response status: {response.status_code}")
                logger.debug(f"GitHub user API response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                user_data = response.json()
                
                # 记录用户信息（但不记录敏感信息）
                safe_user_data = {
                    'login': user_data.get('login'),
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'public_repos': user_data.get('public_repos'),
                    'followers': user_data.get('followers'),
                    'created_at': user_data.get('created_at')
                }
                logger.debug(f"User data received: {safe_user_data}")
                
                logger.info(f"Successfully retrieved user info for: {user_data.get('login', 'unknown')}")
                return user_data
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during user info retrieval: {e}")
            raise HTTPException(status_code=500, detail="GitHub服务器响应超时")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during user info retrieval: {e}")
            logger.error(f"Response content: {e.response.content if hasattr(e, 'response') else 'N/A'}")
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="访问令牌无效或已过期")
            else:
                raise HTTPException(status_code=500, detail="无法获取用户信息")
        except httpx.RequestError as e:
            logger.error(f"Request error during user info retrieval: {e}")
            raise HTTPException(status_code=500, detail="网络连接错误")
        except Exception as e:
            logger.error(f"Unexpected error during user info retrieval: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="获取用户信息时发生错误")
    
    async def _create_or_update_user(self, username: str, user_info: Dict[str, Any]):
        """创建或更新用户信息"""
        try:
            logger.info(f"Processing user data for: {username}")
            
            # 检查用户是否已存在
            query = user_table.select().where(user_table.c.username == username)
            existing_user = await database.fetch_one(query)
            
            if existing_user:
                # 更新现有用户的登录时间
                logger.info(f"Updating login time for existing user: {username}")
                query = user_table.update().where(user_table.c.username == username).values(
                    login_time=datetime.utcnow()
                )
                await database.execute(query)
                logger.info(f"更新用户 {username} 的登录时间")
            else:
                # 创建新用户
                logger.info(f"Creating new user: {username}")
                
                # 生成随机密码（OAuth用户不需要密码登录）
                from app.utils.crypto_utils import generate_random_password
                random_password = generate_random_password()
                hashed_password = hash_password(random_password)
                
                # 在user表中创建用户
                logger.debug(f"Inserting user {username} into user_table")
                query = user_table.insert().values(
                    username=username,
                    password=hashed_password,
                    user_type="user",
                    theme="default"
                )
                user_id = await database.execute(query)
                logger.info(f"User {username} created with ID: {user_id}")
                
                # 同时在admin表中创建记录（向后兼容）
                try:
                    logger.debug(f"Inserting user {username} into admin_table for compatibility")
                    query = admin_table.insert().values(
                        username=username,
                        password=hashed_password
                    )
                    await database.execute(query)
                    logger.info(f"User {username} also added to admin_table for compatibility")
                except Exception as e:
                    # admin表插入失败不影响主流程
                    logger.warning(f"在admin表中创建用户记录失败: {str(e)}")
                
                logger.info(f"创建新用户: {username}")
                
        except Exception as e:
            logger.error(f"创建或更新用户失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="用户数据处理失败")
    
    def logout_user(self, session_id: str) -> bool:
        """用户登出"""
        session_service = get_session_service()
        return session_service.destroy_session(session_id)
    
    def get_login_url(self, next_url: str = None) -> str:
        """获取登录URL"""
        if not self.is_configured():
            # 如果GitHub OAuth未配置，返回管理员登录页面
            return "/admin/login"
        
        state = next_url if next_url else "/"
        return self.get_authorization_url(state)
    
    async def revoke_token(self, access_token: str) -> bool:
        """撤销访问令牌"""
        try:
            # GitHub API的正确端点
            revoke_url = f"https://api.github.com/applications/{self.config.client_id}/token"
            
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            # 使用Basic认证（client_id:client_secret）
            auth = (self.config.client_id, self.config.client_secret)
            
            data = {'access_token': access_token}
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    revoke_url,
                    headers=headers,
                    auth=auth,
                    json=data
                )
                
                if response.status_code == 204:
                    logger.info("Successfully revoked access token")
                    return True
                else:
                    logger.warning(f"Token revocation returned status: {response.status_code}")
                    return False
                
        except Exception as e:
            logger.error(f"撤销令牌失败: {str(e)}")
            return False
    
    def get_oauth_status(self) -> Dict[str, Any]:
        """获取OAuth配置状态"""
        return {
            "configured": self.is_configured(),
            "client_id": self.config.client_id[:8] + "..." if self.config.client_id else None,
            "redirect_uri": self.config.redirect_uri,
            "available": True
        }
    
    def render_login_page(self, session: SessionData) -> str:
        """渲染登录页面"""
        # 如果用户已登录，重定向到首页
        if session.username:
            return RedirectResponse(url="/")
        
        # 如果OAuth未配置，返回管理员登录页面
        if not self.is_configured():
            return RedirectResponse(url="/admin/login")
        
        # 生成GitHub OAuth登录链接
        auth_url = self.get_authorization_url()
        
        # 返回登录页面HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MarkEdit - 登录</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }}
                .login-container {{
                    background: white;
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .login-btn {{
                    background: #333;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 4px;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 1rem;
                }}
                .login-btn:hover {{
                    background: #555;
                }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>MarkEdit</h1>
                <p>请使用GitHub账号登录</p>
                <a href="{auth_url}" class="login-btn">通过GitHub登录</a>
                <p><a href="/admin/login">管理员登录</a></p>
            </div>
        </body>
        </html>
        """
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
    
    def handle_login_post(self, session: SessionData):
        """处理登录表单提交"""
        # 如果用户已登录，重定向到首页
        if session.username:
            return RedirectResponse(url="/")
        
        # 重定向到GitHub OAuth
        if self.is_configured():
            auth_url = self.get_authorization_url()
            return RedirectResponse(url=auth_url)
        else:
            return RedirectResponse(url="/admin/login")
    
    def handle_logout(self, request, session: SessionData):
        """处理用户登出"""
        # 从request cookie中获取session_id
        session_id = request.cookies.get("session_id")
        if session_id:
            session_service = get_session_service()
            session_service.destroy_session(session_id)
        
        # 创建重定向响应
        response = RedirectResponse(url="/login")
        
        # 清除cookie
        response.delete_cookie("session_id")
        
        return response
    
    async def auth_middleware(self, request: Request, call_next):
        """认证中间件"""
        try:
            # 获取当前会话
            session_service = get_session_service()
            session = session_service.get_session(request)
            
            # 如果用户已登录，更新会话权限
            if session.username:
                try:
                    await session_service.update_session_permissions(session)
                except Exception as e:
                    logger.warning(f"更新会话权限失败: {str(e)}")
            
            # 定义需要登录的页面路径
            protected_paths = {
                "/",  # 主页
                "/dashboard",  # 仪表板
                "/admin",  # 管理页面
                "/myaccount",  # 我的账户
                "/epub-viewer.html",  # EPUB查看器
            }
            
            # 定义需要登录的API路径前缀
            protected_api_prefixes = [
                "/api/files",  # 文件操作 API
                "/api/admin",  # 管理 API
                "/user-src",  # 用户源文件
                "/user-illustrations",  # 用户插图
            ]
            
            # 定义不需要登录的页面和API
            public_paths = {
                "/login",  # 登录页面
                "/admin/login",  # 管理员登录页面
                "/callback",  # OAuth回调
                "/logout",  # 登出
            }
            
            # 定义公共路径前缀（不需要登录）
            public_prefixes = [
                "/static",  # 静态文件
                "/docs",  # API文档
                "/openapi.json",  # OpenAPI規格
                "/redoc",  # ReDoc文档
            ]
            
            # 检查是否为公共路径
            path = request.url.path
            is_public = (
                path in public_paths or
                any(path.startswith(prefix) for prefix in public_prefixes)
            )
            
            # 检查是否为受保护的路径
            is_protected = (
                path in protected_paths or
                any(path.startswith(prefix) for prefix in protected_api_prefixes)
            )
            
            # 如果是受保护的路径且用户未登录，重定向到登录页
            if is_protected and not session.username:
                from fastapi.responses import RedirectResponse
                
                # 对于API请求，返回401状态码
                if path.startswith("/api/") or path.startswith("/user-"):
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=401, 
                        detail="未登录，请先登录",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                
                # 对于页面请求，重定向到登录页
                logger.info(f"用户未登录访问受保护路径 {path}，重定向到登录页")
                return RedirectResponse(url="/login")
            
            # 继续处理请求
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.warning(f"认证中间件错误: {str(e)}")
            # 即使中间件出错，也要继续处理请求
            return await call_next(request)

# 创建全局OAuth服务实例
oauth_service = OAuthService()