"""
User controller for MarkEdit application.

This module contains HTTP route handlers for user management.
"""
from fastapi import APIRouter, Request

from app.common import get_user_service
from app.controllers.base_controller import BaseController, controller_exception_handler

# 创建用户控制器实例
user_controller = BaseController("UserController")

# 创建路由器
user_router = APIRouter(prefix="/api/user", tags=["user"])

# 创建用户服务实例
user_service = get_user_service()

@user_router.post("/theme")
@controller_exception_handler("更新用户主题")
async def update_user_theme(request: Request):
    """更新用户主题"""
    # 解析请求体并验证必需字段
    body = await user_controller.parse_request_json(request, required_fields=["theme"])
    theme = body.get("theme")
    
    result = await user_service.update_user_theme(request, theme)
    return user_controller.create_success_response(result, "主题更新成功")

@user_router.get("/theme")
@controller_exception_handler("获取用户主题")
async def get_user_theme(request: Request):
    """获取用户当前主题"""
    result = await user_service.get_user_theme(request)
    return user_controller.create_success_response(result)

@user_router.get("/info")
@controller_exception_handler("获取用户信息")
async def get_user_info(request: Request):
    """获取用户信息（兼容超级管理员用户）"""
    result = await user_service.get_user_info(request)
    return user_controller.create_success_response(result)

@user_router.post("/llm-config")
@controller_exception_handler("更新用户LLM配置")
async def update_user_llm_config(request: Request):
    """更新用户LLM配置"""
    # 解析请求体并验证必需字段
    body = await user_controller.parse_request_json(request, required_fields=["llm_config"])
    llm_config = body.get("llm_config")
    
    result = await user_service.update_user_llm_config(request, llm_config)
    return user_controller.create_success_response(result, "LLM配置更新成功")