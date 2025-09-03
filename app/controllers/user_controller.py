"""
User controller for MarkEdit application.

This module contains HTTP route handlers for user management.
"""
from fastapi import APIRouter, Request
from typing import Dict, Any

from app.controllers.base_controller import BaseController

class UserController(BaseController):
    """用户管理控制器"""
    
    def __init__(self):
        super().__init__("UserController")

# 创建用户控制器实例
user_controller = UserController()

# 创建路由器
user_router = APIRouter(prefix="/api/user", tags=["user"])

@user_router.post("/theme")
async def update_user_theme(request: Request):
    """更新用户主题"""
    # 解析请求体获取theme参数
    body_data = await request.json()
    theme = body_data.get("theme")
    
    return await user_controller.handle_api_operation(
        operation_type="update",
        service_name="user",
        method_name="update_user_theme",
        request=request,
        body_data={"theme": theme},
        required_permissions=[]  # 移除权限检查，只需要登录
    )

@user_router.get("/theme")
async def get_user_theme(request: Request):
    """获取用户当前主题"""
    return await user_controller.handle_api_operation(
        operation_type="get",
        service_name="user",
        method_name="get_user_theme",
        request=request,
        required_permissions=[]  # 移除权限检查，只需要登录
    )

@user_router.get("/info")
async def get_user_info(request: Request):
    """获取用户信息（兼容超级管理员用户）"""
    return await user_controller.handle_api_operation(
        operation_type="get",
        service_name="user",
        method_name="get_user_info",
        request=request,
        required_permissions=[]  # 移除权限检查，允许所有登录用户访问自己的信息
    )

@user_router.post("/llm-config")
async def update_user_llm_config(request: Request):
    """更新用户LLM配置"""
    return await user_controller.handle_api_operation(
        operation_type="update",
        service_name="user",
        method_name="update_user_llm_config",
        request=request,
        required_permissions=[]  # 移除权限检查，允许所有登录用户更新自己的配置
    )

@user_router.get("/profile")
async def get_user_profile(request: Request):
    """获取用户个人资料"""
    return await user_controller.handle_api_operation(
        operation_type="get",
        service_name="user",
        method_name="get_user_profile",
        request=request,
        required_permissions=[]  # 移除权限检查，允许所有登录用户访问自己的资料
    )

@user_router.get("/settings")
async def get_user_settings(request: Request):
    """获取用户设置"""
    return await user_controller.handle_api_operation(
        operation_type="get",
        service_name="user",
        method_name="get_user_settings",
        request=request,
        required_permissions=[]  # 移除权限检查，允许所有登录用户访问自己的设置
    )

@user_router.get("/activities")
async def get_user_activities(request: Request):
    """获取用户活动记录"""
    return await user_controller.handle_api_operation(
        operation_type="get",
        service_name="user",
        method_name="get_user_activities",
        request=request,
        required_permissions=[]  # 移除权限检查，允许所有登录用户访问自己的活动记录
    )