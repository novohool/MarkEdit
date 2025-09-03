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
    """多平台OAuth认证服务类"""
    
    def __init__(self):
        self.config = OAuthConfig(
            # GitHub OAuth配置
            github_client_id=os.getenv('GITHUB_APP_CLIENT_ID'),
            github_client_secret=os.getenv('GITHUB_APP_CLIENT_SECRET'),
            github_redirect_uri=os.getenv('GITHUB_APP_REDIRECT_URI'),
            # Gmail OAuth配置
            gmail_client_id=os.getenv('GMAIL_CLIENT_ID'),
            gmail_client_secret=os.getenv('GMAIL_CLIENT_SECRET'),
            gmail_redirect_uri=os.getenv('GMAIL_REDIRECT_URI')
        )
    
    def is_configured(self) -> bool:
        """检查是否至少有一种OAuth已配置"""
        configured = self.config.is_configured
        logger.debug(f"OAuth configuration check:")
        logger.debug(f"  GitHub Client ID: {'SET' if self.config.github_client_id else 'MISSING'}")
        logger.debug(f"  GitHub Client Secret: {'SET' if self.config.github_client_secret else 'MISSING'}")
        logger.debug(f"  GitHub Redirect URI: {self.config.github_redirect_uri or 'MISSING'}")
        logger.debug(f"  Gmail Client ID: {'SET' if self.config.gmail_client_id else 'MISSING'}")
        logger.debug(f"  Gmail Client Secret: {'SET' if self.config.gmail_client_secret else 'MISSING'}")
        logger.debug(f"  Gmail Redirect URI: {self.config.gmail_redirect_uri or 'MISSING'}")
        logger.debug(f"  Overall configured: {configured}")
        return configured
    
    def _detect_oauth_provider(self, request: Request) -> str:
        """检测请求来自哪个OAuth提供商"""
        # 通过state参数或者referer来判断
        state = request.query_params.get("state", "")
        referer = request.headers.get("referer", "")
        
        # 如果state包含提供商信息
        if "gmail" in state.lower():
            return "gmail"
        if "github" in state.lower():
            return "github"
        
        # 如果referer包含提供商信息
        if "accounts.google.com" in referer:
            return "gmail"
        if "github.com" in referer:
            return "github"
        
        # 默认为GitHub（向后兼容）
        return "github"
    
    def get_authorization_url(self, state: str = None, provider: str = "github") -> str:
        """获取OAuth授权URL"""
        if provider == "github":
            return self._get_github_authorization_url(state)
        elif provider == "gmail":
            return self._get_gmail_authorization_url(state)
        else:
            raise ValueError(f"不支持的OAuth提供商: {provider}")
    
    def _get_github_authorization_url(self, state: str = None) -> str:
        """获取GitHub授权URL"""
        if not self.config.is_github_configured:
            raise ValueError("GitHub OAuth未配置")
        
        params = {
            'client_id': self.config.github_client_id,
            'redirect_uri': self.config.github_redirect_uri,
            'scope': 'user:email'
        }
        
        if state:
            params['state'] = f"github_{state}"
        else:
            params['state'] = "github"
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    def _get_gmail_authorization_url(self, state: str = None) -> str:
        """获取Gmail授权URL"""
        if not self.config.is_gmail_configured:
            raise ValueError("Gmail OAuth未配置")
        
        params = {
            'client_id': self.config.gmail_client_id,
            'redirect_uri': self.config.gmail_redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline'
        }
        
        if state:
            params['state'] = f"gmail_{state}"
        else:
            params['state'] = "gmail"
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    async def handle_oauth_callback(self, code: str, request: Request, session: SessionData = None) -> RedirectResponse:
        """处理OAuth回调"""
        try:
            logger.info(f"Starting OAuth callback processing with code: {code[:10]}...")
            logger.debug(f"Full callback URL: {request.url}")
            logger.debug(f"Request headers: {dict(request.headers)}")
            
            # 检测是哪个提供商
            provider = self._detect_oauth_provider(request)
            logger.info(f"Detected OAuth provider: {provider}")
            
            # 根据提供商调用不同的处理方法
            if provider == "github":
                return await self._handle_github_callback(code, request, session)
            elif provider == "gmail":
                return await self._handle_gmail_callback(code, request, session)
            else:
                raise HTTPException(status_code=400, detail=f"不支持的OAuth提供商: {provider}")
                
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
    
    async def _handle_github_callback(self, code: str, request: Request, session: SessionData = None) -> RedirectResponse:
        """处理GitHub OAuth回调"""
        # 检查GitHub OAuth配置
        if not self.config.is_github_configured:
            logger.error("GitHub OAuth not configured")
            logger.error(f"Client ID: {'configured' if self.config.github_client_id else 'missing'}")
            logger.error(f"Client Secret: {'configured' if self.config.github_client_secret else 'missing'}")
            logger.error(f"Redirect URI: {self.config.github_redirect_uri or 'missing'}")
            raise HTTPException(status_code=500, detail="GitHub OAuth未配置")
        
        logger.debug(f"GitHub OAuth config - Client ID: {self.config.github_client_id[:8] if self.config.github_client_id else 'None'}...")
        logger.debug(f"GitHub OAuth config - Redirect URI: {self.config.github_redirect_uri}")
        
        # 交换访问令牌
        logger.info("Exchanging authorization code for access token")
        token_data = await self._exchange_github_code_for_token(code)
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
        user_info = await self._get_github_user_info(access_token)
        original_username = user_info.get('login')
        
        if not original_username:
            logger.error("No username found in user info")
            logger.error(f"User info received: {user_info}")
            raise HTTPException(status_code=400, detail="获取用户信息失败")
        
        # 为GitHub用户添加github_前缀
        username = f"github_{original_username}"
        
        logger.info(f"Processing login for user: {original_username} -> {username}")
        logger.debug(f"User ID: {user_info.get('id')}")
        logger.debug(f"User email: {user_info.get('email', 'not provided')}")
        logger.debug(f"User name: {user_info.get('name', 'not provided')}")
        logger.debug(f"Original GitHub username: {original_username}")
        logger.debug(f"System username with prefix: {username}")
        
        return await self._complete_oauth_login(username, user_info, original_username, "GitHub")
    
    async def _handle_gmail_callback(self, code: str, request: Request, session: SessionData = None) -> RedirectResponse:
        """处理Gmail OAuth回调"""
        # 检查Gmail OAuth配置
        if not self.config.is_gmail_configured:
            logger.error("Gmail OAuth not configured")
            logger.error(f"Client ID: {'configured' if self.config.gmail_client_id else 'missing'}")
            logger.error(f"Client Secret: {'configured' if self.config.gmail_client_secret else 'missing'}")
            logger.error(f"Redirect URI: {self.config.gmail_redirect_uri or 'missing'}")
            raise HTTPException(status_code=500, detail="Gmail OAuth未配置")
        
        logger.debug(f"Gmail OAuth config - Client ID: {self.config.gmail_client_id[:8] if self.config.gmail_client_id else 'None'}...")
        logger.debug(f"Gmail OAuth config - Redirect URI: {self.config.gmail_redirect_uri}")
        
        # 交换访问令牌
        logger.info("Exchanging authorization code for access token")
        token_data = await self._exchange_gmail_code_for_token(code)
        access_token = token_data.get('access_token')
        
        if not access_token:
            logger.error("No access token received from Gmail")
            logger.error(f"Token response data: {token_data}")
            raise HTTPException(status_code=400, detail="获取访问令牌失败")
        
        logger.info("Access token received successfully")
        logger.debug(f"Token type: {token_data.get('token_type', 'unknown')}")
        logger.debug(f"Token scope: {token_data.get('scope', 'unknown')}")
        
        # 获取用户信息
        logger.info("Fetching user information from Gmail")
        user_info = await self._get_gmail_user_info(access_token)
        email = user_info.get('email')
        
        if not email:
            logger.error("No email found in user info")
            logger.error(f"User info received: {user_info}")
            raise HTTPException(status_code=400, detail="获取用户信息失败")
        
        # 从邮箱地址提取用户名（@之前的部分）
        original_username = email.split('@')[0]
        # 为Gmail用户添加gmail_前缀
        username = f"gmail_{original_username}"
        
        logger.info(f"Processing login for user: {email} -> {username}")
        logger.debug(f"User ID: {user_info.get('sub')}")
        logger.debug(f"User email: {email}")
        logger.debug(f"User name: {user_info.get('name', 'not provided')}")
        logger.debug(f"Original email username: {original_username}")
        logger.debug(f"System username with prefix: {username}")
        
        return await self._complete_oauth_login(username, user_info, original_username, "Gmail")
    
    async def _complete_oauth_login(self, username: str, user_info: Dict[str, Any], original_username: str, provider: str) -> RedirectResponse:
        """完成OAuth登录流程"""
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
        
        logger.info(f"用户 {original_username} (系统用户名: {username}) 通过{provider} OAuth登录成功")
        return response
    
    async def _exchange_github_code_for_token(self, code: str) -> Dict[str, Any]:
        """交换GitHub授权码获取访问令牌"""
        token_url = "https://github.com/login/oauth/access_token"
        
        data = {
            'client_id': self.config.github_client_id,
            'client_secret': self.config.github_client_secret,
            'code': code,
            'redirect_uri': self.config.github_redirect_uri
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
    
    async def _exchange_gmail_code_for_token(self, code: str) -> Dict[str, Any]:
        """交换Gmail授权码获取访问令牌"""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': self.config.gmail_client_id,
            'client_secret': self.config.gmail_client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.config.gmail_redirect_uri
        }
        
        headers = {'Accept': 'application/json'}
        
        logger.debug(f"Token exchange request to: {token_url}")
        logger.debug(f"Request data: {dict(data, client_secret='***')}")
        logger.debug(f"Request headers: {headers}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("Sending token exchange request to Gmail")
                response = await client.post(token_url, data=data, headers=headers)
                
                logger.debug(f"Gmail response status: {response.status_code}")
                logger.debug(f"Gmail response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                token_data = response.json()
                
                logger.debug(f"Gmail response body: {dict(token_data, access_token='***' if 'access_token' in token_data else token_data.get('access_token'))}")
                
                # 检查是否有错误
                if 'error' in token_data:
                    error_desc = token_data.get('error_description', token_data['error'])
                    logger.error(f"Gmail OAuth token exchange failed: {error_desc}")
                    logger.error(f"Full error response: {token_data}")
                    raise HTTPException(status_code=400, detail=f"OAuth认证失败: {error_desc}")
                
                logger.info("Successfully exchanged code for access token")
                return token_data
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during token exchange: {e}")
            raise HTTPException(status_code=500, detail="Gmail服务器响应超时")
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
    
    async def _get_github_user_info(self, access_token: str) -> Dict[str, Any]:
        """使用访问令牌获取GitHub用户信息"""
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
    
    async def _get_gmail_user_info(self, access_token: str) -> Dict[str, Any]:
        """使用访问令牌获取Gmail用户信息"""
        user_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        logger.debug(f"User info request to: {user_url}")
        logger.debug(f"Request headers: {dict(headers, Authorization='Bearer ***')}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("Sending user info request to Gmail")
                response = await client.get(user_url, headers=headers)
                
                logger.debug(f"Gmail user API response status: {response.status_code}")
                logger.debug(f"Gmail user API response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                user_data = response.json()
                
                # 记录用户信息（但不记录敏感信息）
                safe_user_data = {
                    'email': user_data.get('email'),
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'verified_email': user_data.get('verified_email'),
                    'picture': user_data.get('picture')
                }
                logger.debug(f"User data received: {safe_user_data}")
                
                logger.info(f"Successfully retrieved user info for: {user_data.get('email', 'unknown')}")
                return user_data
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during user info retrieval: {e}")
            raise HTTPException(status_code=500, detail="Gmail服务器响应超时")
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
            # 提取原始用户名（去掉前缀）
            original_username = user_info.get('login')
            logger.info(f"Processing user data for: {original_username} (system username: {username})")
            
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
    
    def get_login_url(self, next_url: str = None, provider: str = None) -> str:
        """获取登录URL"""
        if not self.is_configured():
            # 如果OAuth未配置，返回管理员登录页面
            return "/admin/login"
        
        state = next_url if next_url else "/"
        
        if provider:
            # 指定了提供商
            return self.get_authorization_url(state, provider)
        else:
            # 未指定提供商，优先使用GitHub，然后是Gmail
            if self.config.is_github_configured:
                return self.get_authorization_url(state, "github")
            elif self.config.is_gmail_configured:
                return self.get_authorization_url(state, "gmail")
            else:
                return "/admin/login"
    
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
            "github": {
                "configured": self.config.is_github_configured,
                "client_id": self.config.github_client_id[:8] + "..." if self.config.github_client_id else None,
                "redirect_uri": self.config.github_redirect_uri
            },
            "gmail": {
                "configured": self.config.is_gmail_configured,
                "client_id": self.config.gmail_client_id[:8] + "..." if self.config.gmail_client_id else None,
                "redirect_uri": self.config.gmail_redirect_uri
            },
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
        
        # 生成登录链接
        github_auth_url = ""
        gmail_auth_url = ""
        
        if self.config.is_github_configured:
            github_auth_url = self.get_authorization_url(provider="github")
        
        if self.config.is_gmail_configured:
            gmail_auth_url = self.get_authorization_url(provider="gmail")
        
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
                    min-width: 300px;
                }}
                .login-btn {{
                    background: #333;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 4px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 0.5rem;
                    min-width: 200px;
                }}
                .login-btn:hover {{
                    background: #555;
                }}
                .github-btn {{
                    background: #333;
                }}
                .github-btn:hover {{
                    background: #24292e;
                }}
                .gmail-btn {{
                    background: #db4437;
                }}
                .gmail-btn:hover {{
                    background: #c23321;
                }}
                .login-options {{
                    margin: 1rem 0;
                }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>MarkEdit</h1>
                <p>请选择登录方式</p>
                <div class="login-options">
        """
        
        if github_auth_url:
            html_content += f'<a href="{github_auth_url}" class="login-btn github-btn">通过GitHub登录</a><br>'
        
        if gmail_auth_url:
            html_content += f'<a href="{gmail_auth_url}" class="login-btn gmail-btn">通过Gmail登录</a><br>'
        
        html_content += """
                </div>
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
        
        # 重定向到OAuth或管理员登录
        if self.is_configured():
            # 如果只配置了一种，直接重定向
            if self.config.is_github_configured and not self.config.is_gmail_configured:
                auth_url = self.get_authorization_url(provider="github")
                return RedirectResponse(url=auth_url)
            elif self.config.is_gmail_configured and not self.config.is_github_configured:
                auth_url = self.get_authorization_url(provider="gmail")
                return RedirectResponse(url=auth_url)
            else:
                # 两种都配置了，返回选择页面
                return RedirectResponse(url="/login")
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
                "/myaccount",  # 我的账户
                "/epub-viewer.html",  # EPUB查看器
            }
            # 注意：所有 /admin/* 路径都有自己的认证逻辑，不需要中间件保护
            
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