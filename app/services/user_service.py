"""
User service for MarkEdit application.

This module contains business logic for user management.
"""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException

from app.common import (
    get_session_service,
    database, admin_table, user_table,
    validate_json_and_parse, validate_theme_name
)

logger = logging.getLogger(__name__)

class UserService:
    """用户管理服务类"""
    
    async def update_user_theme(self, request: Request, theme: str) -> Dict[str, str]:
        """更新用户主题"""
        try:
            # 获取会话数据
            session_service = get_session_service()
            session = session_service.get_session(request)
            if not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            if not theme:
                raise HTTPException(status_code=400, detail="主题信息不能为空")
            
            if not validate_theme_name(theme):
                raise HTTPException(status_code=400, detail="无效的主题名称")
            
            # 更新数据库中的用户主题
            query = user_table.update().where(user_table.c.username == session.username).values(theme=theme)
            await database.execute(query)
            
            # 更新会话中的主题
            session.theme = theme
            
            return {"message": "主题更新成功", "theme": theme}
        except Exception as e:
            logger.error(f"更新用户主题失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"更新主题失败: {str(e)}")
    
    async def get_user_theme(self, request: Request) -> Dict[str, str]:
        """获取用户当前主题"""
        try:
            # 获取会话数据
            session_service = get_session_service()
            session = session_service.get_session(request)
            if not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            # 从会话中获取主题
            theme = session.theme or "default"
            
            return {"theme": theme}
        except Exception as e:
            logger.error(f"获取用户主题失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"获取主题失败: {str(e)}")
    
    async def get_user_info(self, request: Request) -> Dict[str, Any]:
        """获取用户信息（兼容超级管理员用户）"""
        try:
            # 获取会话数据
            session_service = get_session_service()
            session = session_service.get_session(request)
            if not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            # 首先检查是否为管理员用户
            query = admin_table.select().where(admin_table.c.username == session.username)
            admin_record = await database.fetch_one(query)
            
            if admin_record:
                # 如果是管理员，返回管理员信息
                return {
                    "username": admin_record["username"],
                    "created_at": admin_record["created_at"],
                    "login_time": None,  # 管理员表中没有login_time字段
                    "theme": "default",  # 管理员使用默认主题
                    "llm_config": "{}",  # 管理员没有LLM配置
                    "role": "admin"  # 添加角色信息
                }
            
            # 如果不是管理员，从用户表获取用户信息
            query = user_table.select().where(user_table.c.username == session.username)
            user_record = await database.fetch_one(query)
            
            if not user_record:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 返回用户信息
            return {
                "username": user_record["username"],
                "created_at": user_record["created_at"],
                "login_time": user_record["login_time"],
                "theme": user_record["theme"],
                "llm_config": user_record["llm_config"] or "{}",
                "role": "user"  # 添加角色信息
            }
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")
    
    async def update_user_llm_config(self, request: Request, llm_config: str) -> Dict[str, str]:
        """更新用户LLM配置"""
        try:
            # 获取会话数据
            session_service = get_session_service()
            session = session_service.get_session(request)
            if not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            if llm_config is None:
                raise HTTPException(status_code=400, detail="LLM配置信息不能为空")
            
            # 验证JSON格式
            validate_json_and_parse(llm_config)
            
            # 更新数据库中的用户LLM配置
            query = user_table.update().where(user_table.c.username == session.username).values(llm_config=llm_config)
            await database.execute(query)
            
            return {"message": "LLM配置更新成功"}
        except Exception as e:
            logger.error(f"更新用户LLM配置失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"更新LLM配置失败: {str(e)}")