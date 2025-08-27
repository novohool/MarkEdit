"""
User service for MarkEdit application.

This module contains business logic for user management.
"""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException

from app.services.base_service import BaseService, DatabaseOperationMixin
from app.common import (
    database, admin_table, user_table,
    validate_theme_name
)

logger = logging.getLogger(__name__)

class UserService(BaseService, DatabaseOperationMixin):
    """用户管理服务类"""
    
    async def update_user_theme(self, request: Request, theme: str) -> Dict[str, str]:
        """更新用户主题"""
        # 获取已认证的会话
        session = await self.get_authenticated_session(request)
        
        if not theme:
            raise HTTPException(status_code=400, detail="主题信息不能为空")
        
        # 使用基类的字段更新方法
        return await self.validate_and_update_field(
            table=user_table,
            where_condition=user_table.c.username == session.username,
            field_name="theme",
            field_value=theme,
            validator_func=validate_theme_name
        )
    
    async def get_user_theme(self, request: Request) -> Dict[str, str]:
        """获取用户当前主题"""
        # 获取已认证的会话
        session = await self.get_authenticated_session(request)
        
        # 从会话中获取主题
        theme = session.theme or "default"
        
        return {"theme": theme}
    
    async def get_user_info(self, request: Request) -> Dict[str, Any]:
        """获取用户信息（兼容超级管理员用户）"""
        try:
            # 获取已认证的会话
            session = await self.get_authenticated_session(request)
            
            # 使用基类方法获取用户信息
            user_record = await self.get_user_info_by_username(session.username, include_admin=True)
            
            if not user_record:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 判断是否为管理员
            admin_record = await self.execute_query_with_error_handling(
                admin_table.select().where(admin_table.c.username == session.username),
                "查询管理员信息",
                "fetch_one"
            )
            
            is_admin = admin_record is not None
            
            # 使用基类方法格式化返回数据
            return self.format_user_record(user_record, is_admin=is_admin)
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_service_error(e, "获取用户信息")
    
    async def update_user_llm_config(self, request: Request, llm_config: str) -> Dict[str, str]:
        """更新用户LLM配置"""
        # 获取已认证的会话
        session = await self.get_authenticated_session(request)
        
        if llm_config is None:
            raise HTTPException(status_code=400, detail="LLM配置信息不能为空")
        
        # 验证JSON格式
        await self.safe_json_operation(llm_config, "validate")
        
        # 使用基类的字段更新方法
        return await self.validate_and_update_field(
            table=user_table,
            where_condition=user_table.c.username == session.username,
            field_name="llm_config",
            field_value=llm_config
        )