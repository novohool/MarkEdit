"""
Admin controller base class for MarkEdit application.

This module provides specialized functionality for admin controllers.
"""
import logging
from typing import Any, Dict, List, Union, Callable
from functools import wraps

from fastapi import HTTPException, Request

from app.controllers.base_controller import BaseController, CRUDControllerMixin

logger = logging.getLogger(__name__)

class AdminBaseController(BaseController, CRUDControllerMixin):
    """管理员控制器基类，提供管理功能的通用方法"""
    
    def __init__(self, controller_name: str = "AdminController"):
        super().__init__(controller_name)
        CRUDControllerMixin.__init__(self)
        
        # 管理员常用的服务实例引用
        self._admin_service = None
        self._build_service = None
        self._epub_service = None
    
    @property
    def admin_service(self):
        """延迟加载admin_service以避免循环导入"""
        if self._admin_service is None:
            from app.common import get_admin_service
            self._admin_service = get_admin_service()
        return self._admin_service
    
    @property 
    def build_service(self):
        """延迟加载build_service以避免循环导入"""
        if self._build_service is None:
            from app.common import get_build_service
            self._build_service = get_build_service()
        return self._build_service
    
    @property
    def epub_service(self):
        """延迟加载epub_service以避免循环导入"""
        if self._epub_service is None:
            from app.common import get_epub_service
            self._epub_service = get_epub_service()
        return self._epub_service
    
    # === 用户管理相关方法 ===
    async def handle_user_list_operation(self, request: Request) -> Dict[str, Any]:
        """处理用户列表获取"""
        result = await self.admin_service.get_user_list()
        return {"users": result}
    
    async def handle_user_create_operation(self, request: Request) -> Dict[str, Any]:
        """处理用户创建操作"""
        body = await self.parse_request_json(request, required_fields=['username', 'password'])
        
        username = body.get('username')
        password = body.get('password')
        theme = body.get('theme', 'default')
        
        result = await self.admin_service.create_user(username, password, theme)
        return self.create_success_response(result, "用户创建成功")
    
    async def handle_user_update_operation(self, user_id: int, request: Request) -> Dict[str, Any]:
        """处理用户更新操作"""
        body = await self.parse_request_json(request)
        
        username = body.get('username')
        password = body.get('password')
        theme = body.get('theme')
        
        result = await self.admin_service.update_user(user_id, username, password, theme)
        return self.create_success_response(result, "用户更新成功")
    
    async def handle_user_delete_operation(self, user_id: int) -> Dict[str, Any]:
        """处理用户删除操作"""
        result = await self.admin_service.delete_user(user_id)
        return self.create_success_response(result, "用户删除成功")
    
    # === 角色管理相关方法 ===
    async def handle_role_list_operation(self, request: Request) -> Dict[str, Any]:
        """处理角色列表获取"""
        result = await self.admin_service.get_roles()
        return {"roles": result}
    
    async def handle_role_create_operation(self, request: Request) -> Dict[str, Any]:
        """处理角色创建操作"""
        body = await self.parse_request_json(request, required_fields=['name'])
        
        name = body.get('name')
        description = body.get('description', '')
        
        result = await self.admin_service.create_role(name, description)
        return self.create_success_response(result, "角色创建成功")
    
    async def handle_role_update_operation(self, role_id: int, request: Request) -> Dict[str, Any]:
        """处理角色更新操作"""
        body = await self.parse_request_json(request)
        
        name = body.get('name')
        description = body.get('description')
        
        result = await self.admin_service.update_role(role_id, name, description)
        return self.create_success_response(result, "角色更新成功")
    
    async def handle_role_delete_operation(self, role_id: int) -> Dict[str, Any]:
        """处理角色删除操作"""
        result = await self.admin_service.delete_role(role_id)
        return self.create_success_response(result, "角色删除成功")
    
    # === 权限管理相关方法 ===
    async def handle_permission_list_operation(self, request: Request) -> Dict[str, Any]:
        """处理权限列表获取"""
        result = await self.admin_service.get_permissions()
        return {"permissions": result}
    
    async def handle_permission_create_operation(self, request: Request) -> Dict[str, Any]:
        """处理权限创建操作"""
        body = await self.parse_request_json(request, required_fields=['name'])
        
        name = body.get('name')
        description = body.get('description', '')
        
        result = await self.admin_service.create_permission(name, description)
        return self.create_success_response(result, "权限创建成功")
    
    async def handle_permission_delete_operation(self, permission_id: int) -> Dict[str, Any]:
        """处理权限删除操作"""
        result = await self.admin_service.delete_permission(permission_id)
        return self.create_success_response(result, "权限删除成功")
    
    # === 用户角色分配相关方法 ===
    async def handle_user_roles_operation(self, user_id: int) -> Dict[str, Any]:
        """处理获取用户角色操作"""
        result = await self.admin_service.get_user_roles(user_id)
        return self.create_success_response(result)
    
    async def handle_assign_user_roles_operation(self, user_id: int, request: Request) -> Dict[str, Any]:
        """处理用户角色分配操作"""
        body = await self.parse_request_json(request, required_fields=['role_ids'])
        role_ids = body.get('role_ids', [])
        
        result = await self.admin_service.assign_user_roles(user_id, role_ids)
        return self.create_success_response(result, "用户角色分配成功")
    
    async def handle_remove_user_role_operation(self, user_id: int, role_name: str) -> Dict[str, Any]:
        """处理移除用户角色操作"""
        result = await self.admin_service.remove_user_role(user_id, role_name)
        return self.create_success_response(result, "用户角色移除成功")
    
    # === 角色权限分配相关方法 ===
    async def handle_role_permissions_operation(self, role_id: int) -> Dict[str, Any]:
        """处理获取角色权限操作"""
        result = await self.admin_service.get_role_permissions(role_id)
        return self.create_success_response(result)
    
    async def handle_assign_role_permissions_operation(self, role_id: int, request: Request) -> Dict[str, Any]:
        """处理角色权限分配操作"""
        body = await self.parse_request_json(request, required_fields=['permission_ids'])
        permission_ids = body.get('permission_ids', [])
        
        result = await self.admin_service.assign_role_permissions(role_id, permission_ids)
        return self.create_success_response(result, "角色权限分配成功")
    
    async def handle_remove_role_permission_operation(self, role_id: int, permission_name: str) -> Dict[str, Any]:
        """处理移除角色权限操作"""
        result = await self.admin_service.remove_role_permission(role_id, permission_name)
        return self.create_success_response(result, "角色权限移除成功")
    
    # === 批量操作相关方法 ===
    async def handle_batch_assign_role_operation(self, request: Request) -> Dict[str, Any]:
        """处理批量角色分配操作"""
        body = await self.parse_request_json(request, required_fields=['user_ids', 'role_id'])
        
        user_ids = body.get('user_ids', [])
        role_id = body.get('role_id')
        
        result = await self.admin_service.batch_assign_users_to_role(user_ids, role_id)
        return self.create_success_response(result, "批量角色分配成功")
    
    async def handle_batch_remove_role_operation(self, request: Request) -> Dict[str, Any]:
        """处理批量角色移除操作"""
        body = await self.parse_request_json(request, required_fields=['user_ids', 'role_id'])
        
        user_ids = body.get('user_ids', [])
        role_id = body.get('role_id')
        
        result = await self.admin_service.batch_remove_users_from_role(user_ids, role_id)
        return self.create_success_response(result, "批量角色移除成功")
    
    # === 文件管理相关方法 ===
    async def handle_admin_file_read_operation(self, file_name: str) -> Dict[str, Any]:
        """处理管理文件读取操作"""
        result = await self.admin_service.read_admin_file(file_name)
        return self.create_success_response(result)
    
    async def handle_admin_file_save_operation(self, file_name: str, request: Request) -> Dict[str, Any]:
        """处理管理文件保存操作"""
        # 获取请求体中的内容
        body = await request.body()
        content_type = request.headers.get('content-type', '')
        
        if 'application/json' in content_type:
            content = body.decode('utf-8')
        else:
            content = body.decode('utf-8')
        
        result = await self.admin_service.save_admin_file(file_name, content, content_type)
        return self.create_success_response(result, "文件保存成功")
    
    # === 系统信息相关方法 ===
    async def handle_system_info_operation(self) -> Dict[str, Any]:
        """处理系统信息获取操作"""
        result = await self.admin_service.get_system_info()
        return self.create_success_response(result)
    
    # === 登录相关方法 ===
    async def handle_admin_login_operation(self, request: Request) -> Any:
        """处理管理员登录操作"""
        body = await self.parse_request_json(request, required_fields=['username', 'password'])
        
        username = body.get('username')
        password = body.get('password')
        
        # 验证管理员用户
        from app.common import admin_table, database, verify_password, get_session_service
        
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
        
        self.logger.info(f"管理员 {username} 登录成功")
        return response
    
    # === 通用工具方法 ===
    def admin_exception_handler(self, operation_name: str):
        """管理员操作专用的异常处理装饰器"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    # 重新抛出HTTP异常
                    raise
                except ValueError as e:
                    # 业务逻辑错误（如用户不存在、角色不存在等）
                    if "不存在" in str(e):
                        raise HTTPException(status_code=404, detail=str(e))
                    else:
                        raise HTTPException(status_code=400, detail=str(e))
                except PermissionError as e:
                    # 权限错误
                    self.logger.warning(f"{operation_name}权限错误: {str(e)}")
                    raise HTTPException(status_code=403, detail=str(e))
                except Exception as e:
                    # 系统异常
                    self.logger.error(f"{operation_name}失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
            return wrapper
        return decorator