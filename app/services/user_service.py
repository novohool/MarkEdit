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
    
    async def update_user_theme(self, request: Request, theme: str = None) -> Dict[str, str]:
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
    
    def _get_display_username(self, db_username: str) -> str:
        """获取用于显示的用户名"""
        if db_username == "super_admin_markedit":
            return "markedit"
        return db_username
    
    async def get_user_info(self, request: Request) -> Dict[str, Any]:
        """获取用户信息（兼容超级管理员用户）"""
        try:
            # 获取已认证的会话
            session = await self.get_authenticated_session(request)
            
            # 首先检查管理员表 - 尝试多种用户名格式
            admin_queries = [
                admin_table.select().where(admin_table.c.username == session.username),
                admin_table.select().where(admin_table.c.username == f"super_admin_{session.username}"),
                admin_table.select().where(admin_table.c.username == "super_admin_markedit")
            ]
            
            admin_record = None
            for query in admin_queries:
                admin_record = await self.execute_query_with_error_handling(
                    query,
                    "查询管理员信息",
                    "fetch_one"
                )
                if admin_record:
                    break
            
            if admin_record:
                # 管理员用户，获取角色信息
                display_username = self._get_display_username(admin_record["username"])
                roles = ["super_admin"] if display_username == "markedit" else ["admin"]
                
                return {
                    "username": display_username,
                    "created_at": admin_record["created_at"].isoformat() if admin_record["created_at"] else None,
                    "last_login": None,  # 管理员表中没有login_time字段
                    "theme": "default",  # 管理员使用默认主题
                    "roles": roles,
                    "primaryRole": roles[0],
                    "is_active": True,
                    "user_type": "admin"
                }
            
            # 检查普通用户表
            user_record = await self.execute_query_with_error_handling(
                user_table.select().where(user_table.c.username == session.username),
                "查询用户信息",
                "fetch_one"
            )
            
            if not user_record:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 获取用户角色
            roles_query = """
                SELECT r.name
                FROM role r
                INNER JOIN user_role ur ON r.id = ur.role_id
                INNER JOIN "user" u ON ur.user_id = u.id
                WHERE u.username = :username
                ORDER BY r.name
            """
            role_records = await database.fetch_all(roles_query, {"username": session.username})
            roles = [role["name"] for role in role_records] if role_records else ["user"]
            
            return {
                "username": user_record["username"],
                "created_at": user_record["created_at"].isoformat() if user_record["created_at"] else None,
                "last_login": user_record["login_time"].isoformat() if user_record["login_time"] else None,
                "theme": user_record["theme"] or "default",
                "roles": roles,
                "primaryRole": roles[0] if roles else "user",
                "is_active": getattr(user_record, 'is_active', True),
                "user_type": "user"
            }
            
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
    
    async def get_user_profile(self, request: Request) -> Dict[str, Any]:
        """获取用户个人资料"""
        try:
            # 获取已认证的会话
            session = await self.get_authenticated_session(request)
            
            # 首先检查管理员表 - 尝试多种用户名格式
            admin_queries = [
                admin_table.select().where(admin_table.c.username == session.username),
                admin_table.select().where(admin_table.c.username == f"super_admin_{session.username}"),
                admin_table.select().where(admin_table.c.username == "super_admin_markedit")
            ]
            
            admin_record = None
            for query in admin_queries:
                admin_record = await self.execute_query_with_error_handling(
                    query,
                    "查询管理员信息",
                    "fetch_one"
                )
                if admin_record:
                    break
            
            if admin_record:
                # 管理员用户
                display_username = self._get_display_username(admin_record["username"])
                roles = ["super_admin"] if display_username == "markedit" else ["admin"]
                return {
                    "username": display_username,
                    "email": "",  # 管理员表中没有email字段
                    "theme": "default",
                    "created_at": admin_record["created_at"].isoformat() if admin_record["created_at"] else "",
                    "last_login": "",  # 管理员表中没有login_time字段
                    "is_active": True,
                    "roles": roles
                }
            
            # 检查普通用户表
            user_record = await self.execute_query_with_error_handling(
                user_table.select().where(user_table.c.username == session.username),
                "查询用户信息",
                "fetch_one"
            )
            
            if not user_record:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 获取用户角色
            roles_query = """
                SELECT r.name
                FROM role r
                INNER JOIN user_role ur ON r.id = ur.role_id
                INNER JOIN "user" u ON ur.user_id = u.id
                WHERE u.username = :username
                ORDER BY r.name
            """
            role_records = await database.fetch_all(roles_query, {"username": session.username})
            roles = [role["name"] for role in role_records] if role_records else ["user"]
            
            # 返回个人资料信息
            return {
                "username": user_record["username"],
                "email": getattr(user_record, 'email', ''),
                "theme": user_record["theme"] or "default",
                "created_at": user_record["created_at"].isoformat() if user_record["created_at"] else "",
                "last_login": user_record["login_time"].isoformat() if user_record["login_time"] else "",
                "is_active": getattr(user_record, 'is_active', True),
                "roles": roles
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_service_error(e, "获取用户个人资料")
    
    async def get_user_settings(self, request: Request) -> Dict[str, Any]:
        """获取用户设置"""
        try:
            # 获取已认证的会话
            session = await self.get_authenticated_session(request)
            
            # 获取用户信息
            user_record = await self.get_user_info_by_username(session.username, include_admin=True)
            
            if not user_record:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 解析LLM配置
            llm_config = {}
            try:
                # 尝试从记录中获取llm_config字段
                user_llm_config = user_record.get('llm_config') if hasattr(user_record, 'get') else getattr(user_record, 'llm_config', None)
                if user_llm_config:
                    llm_config = json.loads(user_llm_config)
            except (json.JSONDecodeError, AttributeError, KeyError):
                llm_config = {}
            
            # 获取主题设置，确保兼容不同的记录类型
            theme = "default"
            try:
                if hasattr(user_record, 'get'):
                    # 如果是字典类型
                    theme = user_record.get('theme', 'default')
                elif 'theme' in user_record:
                    # 如果是Record类型且有theme字段
                    theme = user_record['theme'] or 'default'
                else:
                    # 如果没有theme字段，使用默认值
                    theme = 'default'
            except (KeyError, AttributeError):
                theme = 'default'
            
            # 返回用户设置
            return {
                "theme": theme,
                "llm_config": llm_config,
                "notifications": {
                    "email_notifications": True,
                    "system_notifications": True
                },
                "preferences": {
                    "language": "zh-CN",
                    "timezone": "Asia/Shanghai"
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_service_error(e, "获取用户设置")
    
    async def get_user_activities(self, request: Request) -> Dict[str, Any]:
        """获取用户活动记录"""
        try:
            # 获取已认证的会话
            session = await self.get_authenticated_session(request)
            
            # 这里可以从日志或活动表中获取用户活动记录
            # 目前返回模拟数据，后续可以扩展实际的活动记录功能
            activities = [
                {
                    "id": 1,
                    "type": "login",
                    "description": "用户登录",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "ip_address": "127.0.0.1"
                },
                {
                    "id": 2,
                    "type": "theme_change",
                    "description": "更改主题设置",
                    "timestamp": "2024-01-01T11:00:00Z",
                    "ip_address": "127.0.0.1"
                }
            ]
            
            return {
                "activities": activities,
                "total": len(activities),
                "page": 1,
                "per_page": 20
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_service_error(e, "获取用户活动记录")