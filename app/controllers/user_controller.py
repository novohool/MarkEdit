"""
User controller for MarkEdit application.

This module contains HTTP route handlers for user management.
"""
from fastapi import APIRouter, Request

from app.common import get_user_service

# 创建路由器
user_router = APIRouter(prefix="/api/user", tags=["user"])

# 创建用户服务实例
user_service = get_user_service()

@user_router.post("/theme")
async def update_user_theme(request: Request):
    """更新用户主题"""
    # 获取请求体中的主题信息
    body = await request.json()
    theme = body.get("theme")
    
    return await user_service.update_user_theme(request, theme)

@user_router.get("/theme")
async def get_user_theme(request: Request):
    """获取用户当前主题"""
    return await user_service.get_user_theme(request)

@user_router.get("/info")
async def get_user_info(request: Request):
    """获取用户信息（兼容超级管理员用户）"""
    return await user_service.get_user_info(request)

@user_router.post("/llm-config")
async def update_user_llm_config(request: Request):
    """更新用户LLM配置"""
    # 获取请求体中的LLM配置信息
    body = await request.json()
    llm_config = body.get("llm_config")
    
    return await user_service.update_user_llm_config(request, llm_config)