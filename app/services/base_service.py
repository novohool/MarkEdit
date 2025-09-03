"""
Base service class for MarkEdit application.

This module provides common functionality for all service classes,
including database operations, session management, and error handling.
"""
import logging
import json
import os
import datetime
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, Type, List, Union, Callable
from fastapi import Request, HTTPException
from databases.core import Record

from app.common import (
    get_session_service,
    database, user_table, admin_table, role_table, permission_table, 
    user_role_table, role_permission_table,
    validate_json_and_parse, validate_theme_name,
    generate_random_password, hash_password,
    get_user_backup_directory, ensure_user_backup_directory_exists,
    get_user_src_directory
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
            # 优先检查统一用户表（user表），因为它包含完整的用户信息
            user_query = user_table.select().where(user_table.c.username == username)
            user_record = await database.fetch_one(user_query)
            if user_record:
                return user_record
            
            # 如果user表中没有，再检查管理员表（向后兼容）
            if include_admin:
                admin_query = admin_table.select().where(admin_table.c.username == username)
                admin_record = await database.fetch_one(admin_query)
                if admin_record:
                    return admin_record
            
            return None
            
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
    
    # === 新增的通用业务逻辑方法 ===
    
    async def get_user_roles_and_permissions(self, username: str) -> Dict[str, List[str]]:
        """获取用户的角色和权限信息"""
        try:
            # 获取用户角色
            roles_query = (
                role_table.select()
                .select_from(
                    role_table.join(user_role_table, role_table.c.id == user_role_table.c.role_id)
                    .join(user_table, user_role_table.c.user_id == user_table.c.id)
                )
                .where(user_table.c.username == username)
            )
            role_records = await database.fetch_all(roles_query)
            roles = [role["name"] for role in role_records]
            
            # 获取用户权限
            permissions_query = (
                permission_table.select()
                .select_from(
                    permission_table.join(role_permission_table, permission_table.c.id == role_permission_table.c.permission_id)
                    .join(user_role_table, role_permission_table.c.role_id == user_role_table.c.role_id)
                    .join(user_table, user_role_table.c.user_id == user_table.c.id)
                )
                .where(user_table.c.username == username)
            )
            permission_records = await database.fetch_all(permissions_query)
            permissions = [perm["name"] for perm in permission_records]
            
            return {"roles": roles, "permissions": permissions}
            
        except Exception as e:
            self.logger.error(f"获取用户角色权限失败: {str(e)}", exc_info=True)
            return {"roles": [], "permissions": []}
    
    async def validate_user_permission(self, username: str, required_permission: str) -> bool:
        """验证用户是否具有特定权限"""
        try:
            permissions_info = await self.get_user_roles_and_permissions(username)
            return required_permission in permissions_info["permissions"]
        except Exception as e:
            self.logger.error(f"权限验证失败: {str(e)}", exc_info=True)
            return False
    
    async def create_backup_for_user(self, username: str, backup_type: str = "user") -> Dict[str, Any]:
        """为用户创建备份的通用方法"""
        try:
            # 获取用户的src目录和备份目录
            user_src_dir = get_user_src_directory(username)
            user_backup_dir = ensure_user_backup_directory_exists(username)
            
            if not user_src_dir.exists():
                raise FileNotFoundError(f"用户 {username} 的src目录不存在")
            
            # 获取当前时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{backup_type}_{username}_{timestamp}.zip"
            backup_path = user_backup_dir / backup_filename
            
            # 创建备份
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(user_src_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(user_src_dir)
                        zipf.write(file_path, arcname)
            
            self.logger.info(f"用户 {username} 创建备份成功: {backup_filename}")
            
            return {
                "status": "success",
                "message": "备份创建成功",
                "filename": backup_filename,
                "size": backup_path.stat().st_size,
                "created_at": timestamp,
                "backup_path": str(backup_path)
            }
            
        except Exception as e:
            self.logger.error(f"创建备份失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")
    
    async def list_user_backups(self, username: str) -> List[Dict[str, Any]]:
        """列出用户备份文件的通用方法"""
        backup_files = []
        
        try:
            user_backup_dir = get_user_backup_directory(username)
            
            if not user_backup_dir.exists():
                self.logger.info(f"用户 {username} 的备份目录不存在")
                return []
            
            # 搜索用户的备份文件
            for file_path in user_backup_dir.glob("backup_*.zip"):
                if file_path.is_file():
                    stat = file_path.stat()
                    
                    backup_files.append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "created_at": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                        "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "path": str(file_path)
                    })
            
            # 按创建时间倒序排列
            backup_files.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backup_files
            
        except Exception as e:
            self.logger.error(f"列出备份文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"列出备份文件失败: {str(e)}")
    
    async def validate_file_access(self, file_path: str, allowed_extensions: List[str] = None) -> bool:
        """验证文件访问权限的通用方法"""
        try:
            path_obj = Path(file_path)
            
            # 检查路径安全性
            if ".." in file_path or "//" in file_path:
                return False
            
            # 检查文件扩展名
            if allowed_extensions:
                if path_obj.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                    return False
            
            # 检查文件是否存在
            if not path_obj.exists():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"文件访问验证失败: {str(e)}")
            return False
    
    async def safe_file_operation(self, operation: str, file_path: str, content: str = None) -> Dict[str, Any]:
        """安全的文件操作通用方法"""
        try:
            path_obj = Path(file_path)
            
            # 验证文件路径安全性
            if not await self.validate_file_access(file_path):
                raise HTTPException(status_code=400, detail="文件路径不安全或文件不存在")
            
            if operation == "read":
                if path_obj.is_file():
                    try:
                        with open(path_obj, 'r', encoding='utf-8') as f:
                            content = f.read()
                        return {"content": content, "encoding": "utf-8"}
                    except UnicodeDecodeError:
                        try:
                            with open(path_obj, 'r', encoding='gbk') as f:
                                content = f.read()
                            return {"content": content, "encoding": "gbk"}
                        except UnicodeDecodeError:
                            raise HTTPException(status_code=400, detail="无法解码文件")
                else:
                    raise HTTPException(status_code=404, detail="文件不存在")
            
            elif operation == "write":
                if content is None:
                    raise HTTPException(status_code=400, detail="写入内容不能为空")
                
                # 创建目录（如果不存在）
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return {"status": "success", "message": "文件保存成功"}
            
            elif operation == "delete":
                if path_obj.exists():
                    path_obj.unlink()
                    return {"status": "success", "message": "文件删除成功"}
                else:
                    raise HTTPException(status_code=404, detail="文件不存在")
            
            else:
                raise HTTPException(status_code=400, detail=f"不支持的操作类型: {operation}")
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"文件操作失败 [{operation}]: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件操作失败: {str(e)}")

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
    
    # === 新增的数据库操作方法 ===
    
    async def bulk_insert(self, table, data_list: List[Dict[str, Any]]) -> List[int]:
        """批量插入记录"""
        if not data_list:
            return []
        
        result_ids = []
        for data in data_list:
            record_id = await self.create_record(table, data)
            result_ids.append(record_id)
        
        return result_ids
    
    async def bulk_update(self, table, updates: List[Dict[str, Any]]) -> List[int]:
        """批量更新记录
        updates 格式: [{"condition": condition, "data": data}, ...]
        """
        if not updates:
            return []
        
        result_ids = []
        for update_item in updates:
            condition = update_item.get("condition")
            data = update_item.get("data")
            if condition is not None and data:
                record_id = await self.update_record(table, condition, data)
                result_ids.append(record_id)
        
        return result_ids
    
    async def get_paginated_records(self, table, page: int = 1, page_size: int = 20, 
                                  condition=None, order_by=None) -> Dict[str, Any]:
        """分页获取记录"""
        offset = (page - 1) * page_size
        
        # 构建查询
        query = table.select()
        if condition is not None:
            query = query.where(condition)
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        # 获取总数
        total_count = await self.count_records(table, condition)
        
        # 分页查询
        query = query.limit(page_size).offset(offset)
        records = await database.fetch_all(query)
        
        return {
            "records": records,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    async def exists_record(self, table, condition) -> bool:
        """检查记录是否存在"""
        query = table.select().where(condition)
        record = await database.fetch_one(query)
        return record is not None
    
    async def get_or_create_record(self, table, condition, defaults: Dict[str, Any] = None) -> tuple[Record, bool]:
        """获取或创建记录，返回 (record, created)"""
        # 先尝试获取
        query = table.select().where(condition)
        record = await database.fetch_one(query)
        
        if record:
            return record, False
        
        # 如果不存在，则创建
        create_data = defaults or {}
        # 将条件中的等值条件添加到创建数据中
        # 这里只支持简单的等值条件，复杂条件需要手动处理
        if hasattr(condition, 'left') and hasattr(condition, 'right'):
            # 简单的 column == value 条件
            if hasattr(condition.left, 'name'):
                create_data[condition.left.name] = condition.right.value
        
        record_id = await self.create_record(table, create_data)
        new_record = await self.get_record_by_id(table, record_id)
        
        return new_record, True
    
    async def upsert_record(self, table, condition, data: Dict[str, Any]) -> Record:
        """更新或插入记录"""
        # 先尝试更新
        updated_count = await self.update_record(table, condition, data)
        
        if updated_count > 0:
            # 更新成功，获取更新后的记录
            query = table.select().where(condition)
            return await database.fetch_one(query)
        else:
            # 没有记录被更新，创建新记录
            record_id = await self.create_record(table, data)
            return await self.get_record_by_id(table, record_id)