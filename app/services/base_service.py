"""
Base service class for MarkEdit application.

This module provides common functionality for all service classes,
including database operations, session management, and error handling.
"""
import logging
from typing import Dict, Any, Optional, Type, List
from fastapi import Request, HTTPException
from databases.core import Record

from app.common import (
    get_session_service,
    database, user_table, admin_table,
    validate_json_and_parse, validate_theme_name
)

logger = logging.getLogger(__name__)

class BaseService:
    """服务基类，提供通用的数据库操作和错误处理功能"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_authenticated_session(self, request: Request, allow_admin: bool = True):
        """获取已认证的会话，统一的会话验证逻辑"""
        try:
            session_service = get_session_service()
            session = session_service.get_session(request)
            
            if not session.username:
                raise HTTPException(status_code=401, detail="用户未登录")
            
            return session
        except Exception as e:
            self.logger.error(f"获取会话失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=401, detail="认证失败")
    
    async def get_user_info_by_username(self, username: str, include_admin: bool = True) -> Optional[Record]:
        """根据用户名获取用户信息，支持普通用户和管理员"""
        try:
            # 首先检查管理员表
            if include_admin:
                admin_query = admin_table.select().where(admin_table.c.username == username)
                admin_record = await database.fetch_one(admin_query)
                if admin_record:
                    return admin_record
            
            # 检查普通用户表
            user_query = user_table.select().where(user_table.c.username == username)
            user_record = await database.fetch_one(user_query)
            return user_record
            
        except Exception as e:
            self.logger.error(f"查询用户信息失败: {str(e)}", exc_info=True)
            return None
    
    async def validate_and_update_field(self, table, where_condition, field_name: str, 
                                      field_value: Any, validator_func=None) -> Dict[str, Any]:
        """通用的字段更新逻辑，包含验证和数据库更新"""
        try:
            # 验证字段值
            if validator_func:
                if not validator_func(field_value):
                    raise HTTPException(status_code=400, detail=f"无效的{field_name}值")
            
            # 执行数据库更新
            update_values = {field_name: field_value}
            query = table.update().where(where_condition).values(**update_values)
            await database.execute(query)
            
            return {"message": f"{field_name}更新成功", field_name: field_value}
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"更新{field_name}失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"更新{field_name}失败: {str(e)}")
    
    async def safe_json_operation(self, json_string: str, operation: str = "parse") -> Any:
        """安全的JSON操作，统一的JSON处理逻辑"""
        try:
            if operation == "parse":
                return validate_json_and_parse(json_string)
            elif operation == "validate":
                validate_json_and_parse(json_string)
                return True
        except Exception as e:
            self.logger.error(f"JSON{operation}操作失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"无效的JSON格式: {str(e)}")
    
    async def execute_query_with_error_handling(self, query, operation_name: str, 
                                               fetch_type: str = "execute") -> Any:
        """执行数据库查询并处理错误的通用方法"""
        try:
            if fetch_type == "execute":
                return await database.execute(query)
            elif fetch_type == "fetch_one":
                return await database.fetch_one(query)
            elif fetch_type == "fetch_all":
                return await database.fetch_all(query)
            else:
                raise ValueError(f"不支持的fetch类型: {fetch_type}")
                
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    def format_user_record(self, record: Record, is_admin: bool = False) -> Dict[str, Any]:
        """格式化用户记录，统一返回格式"""
        if is_admin:
            return {
                "username": record["username"],
                "created_at": record["created_at"],
                "login_time": None,  # 管理员表中没有login_time字段
                "theme": "default",  # 管理员使用默认主题
                "llm_config": "{}",  # 管理员没有LLM配置
                "role": "admin"
            }
        else:
            return {
                "username": record["username"],
                "created_at": record["created_at"],
                "login_time": record["login_time"],
                "theme": record["theme"] or "default",
                "llm_config": record["llm_config"] or "{}",
                "role": "user"
            }
    
    async def check_user_permissions(self, session, required_permission: str = None) -> bool:
        """检查用户权限的通用方法"""
        # 这里可以实现统一的权限检查逻辑
        # 目前简化处理，后续可以扩展
        return True
    
    def create_success_response(self, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建标准化的成功响应"""
        response = {"status": "success", "message": message}
        if data:
            response.update(data)
        return response
    
    def handle_service_error(self, error: Exception, operation: str, 
                           status_code: int = 500) -> HTTPException:
        """统一的错误处理方法"""
        error_message = f"{operation}失败: {str(error)}"
        self.logger.error(error_message, exc_info=True)
        return HTTPException(status_code=status_code, detail=error_message)

class DatabaseOperationMixin:
    """数据库操作混入类，提供常用的CRUD操作"""
    
    async def create_record(self, table, data: Dict[str, Any]) -> int:
        """创建记录的通用方法"""
        query = table.insert().values(**data)
        return await database.execute(query)
    
    async def get_record_by_id(self, table, record_id: int) -> Optional[Record]:
        """根据ID获取记录"""
        query = table.select().where(table.c.id == record_id)
        return await database.fetch_one(query)
    
    async def get_records_by_condition(self, table, condition) -> List[Record]:
        """根据条件获取多条记录"""
        query = table.select().where(condition)
        return await database.fetch_all(query)
    
    async def update_record(self, table, condition, data: Dict[str, Any]) -> int:
        """更新记录的通用方法"""
        query = table.update().where(condition).values(**data)
        return await database.execute(query)
    
    async def delete_record(self, table, condition) -> int:
        """删除记录的通用方法"""
        query = table.delete().where(condition)
        return await database.execute(query)
    
    async def count_records(self, table, condition=None) -> int:
        """统计记录数量"""
        if condition is not None:
            query = table.select().where(condition)
        else:
            query = table.select()
        records = await database.fetch_all(query)
        return len(records)