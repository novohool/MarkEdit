"""
Admin service for MarkEdit application.

This module contains business logic for admin operations including:
- File management
- User management 
- System configuration
- Backup operations
- Build operations
"""
import os
import json
import shutil
import zipfile
import logging
import asyncio
import datetime
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from databases import Database
from passlib.context import CryptContext
import secrets
import string

from app.config import DATABASE_CONFIG
from app.utils.file_utils import is_text_file
from app.common import (
    database, admin_table, user_table, role_table, user_role_table, 
    permission_table, role_permission_table,
    generate_random_password, hash_password,
    get_user_backup_directory, ensure_user_backup_directory_exists,
    get_user_src_directory, copy_default_files_to_user_directory
)
from app.models.role_model import audit_log_table

logger = logging.getLogger(__name__)

class AdminService:
    """管理员服务类"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.src_dir = self.base_dir / "src"
        
        # 定义允许管理的文件
        self.allowed_files = {
            "package.json": self.base_dir / "package.json",
            "build-pdf.js": self.base_dir / "src" / "build-pdf.js",
            "build-epub.js": self.base_dir / "src" / "build-epub.js"
        }
        
        # 注意：is_text_file函数已移至app.utils.file_utils中统一管理
    
    async def read_admin_file(self, file_name: str) -> Dict[str, Any]:
        """读取管理文件的内容"""
        # 检查文件是否在允许列表中
        if file_name not in self.allowed_files:
            raise ValueError("File access not allowed")
        
        file_path = self.allowed_files[file_name]
        
        if not file_path.exists():
            raise FileNotFoundError("File not found")
        
        if file_path.is_file():
            # 检查是否为文本文件
            if is_text_file(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {"content": content, "type": "text", "encoding": "utf-8"}
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试其他编码
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            content = f.read()
                        return {"content": content, "type": "text", "encoding": "gbk"}
                    except UnicodeDecodeError:
                        return {"content": "无法解码此文本文件", "type": "text", "encoding": "unknown"}
            else:
                # 其他二进制文件
                return {"content": "Binary file", "type": "binary"}
        else:
            raise ValueError("Path is not a file")
    
    async def save_admin_file(self, file_name: str, content: str, content_type: str = None) -> Dict[str, str]:
        """保存管理文件的内容"""
        # 检查文件是否在允许列表中
        if file_name not in self.allowed_files:
            raise ValueError("File access not allowed")
        
        file_path = self.allowed_files[file_name]
        
        # 读取原始文件内容（如果文件存在）
        original_content = None
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except Exception:
                # 如果无法读取原始内容，继续执行但不保存原始内容
                pass
        
        # 如果是JSON内容类型，格式化JSON
        if content_type and 'application/json' in content_type:
            try:
                json_data = json.loads(content)
                content = json.dumps(json_data, indent=2, ensure_ascii=False)
                
                # 验证生成的JSON是否有效
                json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {str(e)}")
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {"status": "success", "message": f"文件 {file_name} 保存成功"}
    
    async def create_backup(self, username: str) -> Dict[str, Any]:
        """创建用户备份"""
        try:
            # 获取用户的src目录和备份目录
            user_src_dir = get_user_src_directory(username)
            user_backup_dir = ensure_user_backup_directory_exists(username)
            
            if not user_src_dir.exists():
                raise FileNotFoundError(f"用户 {username} 的src目录不存在")
            
            # 获取当前时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{username}_{timestamp}.zip"
            backup_path = user_backup_dir / backup_filename
            
            # 创建备份
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 备份用户的src目录
                for root, dirs, files in os.walk(user_src_dir):
                    for file in files:
                        file_path = Path(root) / file
                        # 相对于用户src目录的路径
                        arcname = file_path.relative_to(user_src_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"用户 {username} 创建备份成功: {backup_filename}")
            
            return {
                "status": "success",
                "message": "备份创建成功",
                "filename": backup_filename,
                "size": backup_path.stat().st_size,
                "created_at": timestamp,
                "backup_path": str(backup_path)
            }
            
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            raise Exception(f"创建备份失败: {str(e)}")
    
    async def list_backups(self, username: str) -> List[Dict[str, Any]]:
        """列出用户的备份文件"""
        backup_files = []
        
        try:
            # 获取用户的备份目录
            user_backup_dir = get_user_backup_directory(username)
            
            if not user_backup_dir.exists():
                logger.info(f"用户 {username} 的备份目录不存在")
                return []
            
            # 搜索用户的备份文件
            for file_path in user_backup_dir.glob("backup_*.zip"):
                if file_path.is_file():
                    stat = file_path.stat()
                    
                    backup_files.append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "created_at": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                        "backup_path": str(file_path),
                        "username": username
                    })
            
            # 按创建时间排序（最新的在前）
            backup_files.sort(key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"列出用户备份失败: {str(e)}")
        
        return backup_files
    
    async def restore_backup(self, filename: str, username: str) -> Dict[str, str]:
        """恢复用户备份"""
        try:
            # 获取用户的备份目录和src目录
            user_backup_dir = get_user_backup_directory(username)
            user_src_dir = get_user_src_directory(username)
            backup_path = user_backup_dir / filename
            
            if not backup_path.exists():
                raise FileNotFoundError("备份文件不存在")
            
            # 创建恢复前的备份
            pre_restore_backup = await self.create_backup(f"{username}_pre_restore")
            
            # 清空用户的src目录
            if user_src_dir.exists():
                shutil.rmtree(user_src_dir)
            user_src_dir.mkdir(parents=True, exist_ok=True)
            
            # 解压备份文件
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # 解压所有文件到用户的src目录
                zipf.extractall(user_src_dir)
            
            logger.info(f"用户 {username} 恢复备份成功: {filename}")
            
            return {
                "status": "success",
                "message": f"备份恢复成功，恢复前备份已保存为: {pre_restore_backup['filename']}"
            }
            
        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}")
            raise Exception(f"恢复备份失败: {str(e)}")
    
    async def delete_backup(self, filename: str, username: str) -> Dict[str, str]:
        """删除用户备份文件"""
        try:
            # 获取用户的备份目录
            user_backup_dir = get_user_backup_directory(username)
            backup_path = user_backup_dir / filename
            
            if not backup_path.exists():
                raise FileNotFoundError("备份文件不存在")
            
            # 删除备份文件
            backup_path.unlink()
            
            logger.info(f"用户 {username} 删除备份成功: {filename}")
            
            return {
                "status": "success",
                "message": f"备份文件 {filename} 删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除备份失败: {str(e)}")
            raise Exception(f"删除备份失败: {str(e)}")
    
    def generate_strong_password(self, length: int = 16) -> str:
        """生成强密码"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.isupper() for c in password) and
                any(c.islower() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in "!@#$%^&*()" for c in password)):
                return password
    
    async def reset_admin_password(self, username: str = "markedit") -> Dict[str, str]:
        """重置管理员密码"""
        try:
            # 生成新密码
            new_password = self.generate_strong_password()
            hashed_password = self.pwd_context.hash(new_password)
            
            # 更新admin表中的密码
            query = admin_table.update().where(admin_table.c.username == username).values(
                password=hashed_password
            )
            result = await database.execute(query)
            
            if result == 0:
                # 如果admin表中没有找到用户，创建新用户
                query = admin_table.insert().values(
                    username=username,
                    password=hashed_password
                )
                await database.execute(query)
                logger.info(f"创建新管理员用户: {username}")
            else:
                logger.info(f"重置管理员密码成功: {username}")
            
            # 同时更新user表中的密码（如果存在）
            user_query = user_table.update().where(user_table.c.username == username).values(
                password=hashed_password
            )
            await database.execute(user_query)
            
            return {
                "status": "success",
                "message": "管理员密码重置成功",
                "username": username,
                "new_password": new_password
            }
            
        except Exception as e:
            logger.error(f"重置管理员密码失败: {str(e)}")
            raise Exception(f"重置管理员密码失败: {str(e)}")
    
    async def reset_user_password(self, user_id: int) -> Dict[str, str]:
        """重置用户密码"""
        try:
            # 首先检查用户是否存在
            user_query = user_table.select().where(user_table.c.id == user_id)
            user_info = await database.fetch_one(user_query)
            
            if not user_info:
                raise ValueError("用户不存在")
            
            username = user_info["username"]
            
            # 生成新密码
            new_password = self.generate_strong_password()
            hashed_password = self.pwd_context.hash(new_password)
            
            # 更新user表中的密码
            update_query = user_table.update().where(user_table.c.id == user_id).values(
                password=hashed_password
            )
            await database.execute(update_query)
            
            # 同时更新admin表中的密码（如果存在）
            admin_query = admin_table.update().where(admin_table.c.username == username).values(
                password=hashed_password
            )
            await database.execute(admin_query)
            
            logger.info(f"重置用户密码成功: {username} (ID: {user_id})")
            
            return {
                "status": "success",
                "message": "用户密码重置成功",
                "username": username,
                "new_password": new_password
            }
            
        except Exception as e:
            logger.error(f"重置用户密码失败: {str(e)}")
            raise Exception(f"重置用户密码失败: {str(e)}")
    
    async def get_user_list(self) -> List[Dict[str, Any]]:
        """获取用户列表"""
        try:
            # 查询所有用户及其角色信息
            query = """
                SELECT 
                    u.id, u.username, u.user_type, u.login_time, u.created_at, u.theme,
                    COALESCE(string_agg(r.name, ','), '') as roles
                FROM "user" u
                LEFT JOIN user_role ur ON u.id = ur.user_id
                LEFT JOIN role r ON ur.role_id = r.id
                GROUP BY u.id, u.username, u.user_type, u.login_time, u.created_at, u.theme
                ORDER BY u.created_at DESC
            """
            
            results = await database.fetch_all(query)
            
            users = []
            for row in results:
                user_data = {
                    "id": row["id"],
                    "username": row["username"],
                    "user_type": row["user_type"] or "user",
                    "login_time": row["login_time"].isoformat() if row["login_time"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "theme": row["theme"] or "default",
                    "roles": row["roles"].split(',') if row["roles"] else []
                }
                users.append(user_data)
            
            return users
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            raise Exception(f"获取用户列表失败: {str(e)}")
    
    async def create_user(self, username: str, password: str, theme: str = "default") -> Dict[str, Any]:
        """创建新用户"""
        try:
            # 检查用户名是否已存在
            query = user_table.select().where(user_table.c.username == username)
            existing_user = await database.fetch_one(query)
            
            if existing_user:
                raise ValueError("用户名已存在")
            
            # 密码加密
            hashed_password = hash_password(password)
            
            # 创建用户
            query = user_table.insert().values(
                username=username,
                password=hashed_password,
                user_type="user",
                theme=theme
            )
            user_id = await database.execute(query)
            
            # 同时在admin表中创建记录（向后兼容）
            try:
                query = admin_table.insert().values(
                    username=username,
                    password=hashed_password
                )
                await database.execute(query)
            except Exception as e:
                # admin表插入失败不影响主流程
                logger.warning(f"在admin表中创建用户记录失败: {str(e)}")
            
            # 分配默认用户角色
            await self._assign_default_user_role(user_id)
            
            # 复制默认文件到用户目录
            logger.info(f"为新用户 {username} 设置用户目录")
            copy_default_files_to_user_directory(username)
            
            logger.info(f"创建新用户成功: {username} (ID: {user_id})")
            
            # 记录审计日志
            await self.log_role_permission_change(
                operation="create",
                operator="system",  # 系统创建，实际应该传入操作者
                target_type="user",
                target_id=user_id,
                target_name=username,
                new_values={"username": username, "theme": theme, "user_type": "user"},
                details={"action": "user_created", "default_role_assigned": True}
            )
            
            return {
                "status": "success",
                "message": "用户创建成功",
                "user_id": user_id,
                "username": username
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            raise Exception(f"创建用户失败: {str(e)}")
    
    async def _assign_default_user_role(self, user_id: int):
        """为用户分配默认用户角色"""
        try:
            # 获取user角色ID
            query = role_table.select().where(role_table.c.name == "user")
            role_info = await database.fetch_one(query)
            
            if role_info:
                # 分配用户角色
                query = user_role_table.insert().values(
                    user_id=user_id,
                    role_id=role_info["id"]
                )
                await database.execute(query)
                logger.info(f"为用户ID {user_id} 分配了user角色")
            else:
                logger.warning("user角色不存在，无法分配默认角色")
                
        except Exception as e:
            logger.error(f"分配默认用户角色失败: {str(e)}")
    
    async def update_user(self, user_id: int, username: str = None, password: str = None, theme: str = None) -> Dict[str, Any]:
        """更新用户信息"""
        try:
            # 检查用户是否存在
            query = user_table.select().where(user_table.c.id == user_id)
            existing_user = await database.fetch_one(query)
            
            if not existing_user:
                raise ValueError("用户不存在")
            
            update_data = {}
            
            # 更新用户名（检查是否重复）
            if username and username != existing_user["username"]:
                username_query = user_table.select().where(
                    (user_table.c.username == username) & 
                    (user_table.c.id != user_id)
                )
                duplicate_user = await database.fetch_one(username_query)
                if duplicate_user:
                    raise ValueError("用户名已存在")
                update_data["username"] = username
            
            # 更新密码
            if password:
                hashed_password = hash_password(password)
                update_data["password"] = hashed_password
                
                # 同时更新admin表中的密码（向后兼容）
                try:
                    admin_update = admin_table.update().where(
                        admin_table.c.username == existing_user["username"]
                    ).values(password=hashed_password)
                    await database.execute(admin_update)
                except Exception as e:
                    logger.warning(f"更新admin表密码失败: {str(e)}")
            
            # 更新主题
            if theme:
                update_data["theme"] = theme
            
            # 执行更新
            if update_data:
                query = user_table.update().where(user_table.c.id == user_id).values(**update_data)
                await database.execute(query)
                
                # 如果用户名发生变化，同时更新admin表
                if "username" in update_data:
                    try:
                        admin_update = admin_table.update().where(
                            admin_table.c.username == existing_user["username"]
                        ).values(username=update_data["username"])
                        await database.execute(admin_update)
                    except Exception as e:
                        logger.warning(f"更新admin表用户名失败: {str(e)}")
            
            logger.info(f"更新用户成功: {existing_user['username']} (ID: {user_id})")
            
            return {
                "status": "success",
                "message": "用户更新成功",
                "user_id": user_id
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新用户失败: {str(e)}")
            raise Exception(f"更新用户失败: {str(e)}")
    
    async def delete_user(self, user_id: int) -> Dict[str, str]:
        """删除用户"""
        try:
            # 首先检查用户是否存在
            query = user_table.select().where(user_table.c.id == user_id)
            user_info = await database.fetch_one(query)
            
            if not user_info:
                raise ValueError("用户不存在")
            
            username = user_info["username"]
            
            # 删除用户角色关联
            query = user_role_table.delete().where(user_role_table.c.user_id == user_id)
            await database.execute(query)
            
            # 删除用户
            query = user_table.delete().where(user_table.c.id == user_id)
            await database.execute(query)
            
            # 同时删除admin表中的记录（如果存在）
            query = admin_table.delete().where(admin_table.c.username == username)
            await database.execute(query)
            
            logger.info(f"删除用户成功: {username} (ID: {user_id})")
            
            return {"status": "success", "message": f"用户 {username} 删除成功"}
            
        except Exception as e:
            logger.error(f"删除用户失败: {str(e)}")
            raise Exception(f"删除用户失败: {str(e)}")
    
    async def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        import platform
        import psutil
        
        try:
            # 获取系统基本信息
            system_info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node(),
            }
            
            # 获取内存信息
            memory = psutil.virtual_memory()
            system_info["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            }
            
            # 获取磁盘信息
            disk = psutil.disk_usage('/')
            system_info["disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            }
            
            # 获取数据库信息
            system_info["database"] = {
                "host": DATABASE_CONFIG['host'],
                "port": DATABASE_CONFIG['port'],
                "database": DATABASE_CONFIG['database'],
                "user": DATABASE_CONFIG['user']
            }
            
            return system_info
            
        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            # 返回基本信息，即使某些信息获取失败
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "error": f"部分信息获取失败: {str(e)}"
            }
    
    # ==========================================
    # 用户角色管理方法
    # ==========================================
    
    async def get_user_roles(self, user_id: int) -> Dict[str, Any]:
        """获取用户的角色列表"""
        try:
            # 首先检查用户是否存在
            user_query = user_table.select().where(user_table.c.id == user_id)
            user_info = await database.fetch_one(user_query)
            
            if not user_info:
                raise ValueError("用户不存在")
            
            # 获取用户的角色
            query = """
                SELECT r.id, r.name, r.description
                FROM role r
                INNER JOIN user_role ur ON r.id = ur.role_id
                WHERE ur.user_id = :user_id
                ORDER BY r.name
            """
            
            roles = await database.fetch_all(query, {"user_id": user_id})
            
            role_list = []
            for role in roles:
                role_list.append({
                    "id": role["id"],
                    "name": role["name"],
                    "description": role["description"]
                })
            
            return {
                "user_id": user_id,
                "username": user_info["username"],
                "roles": role_list
            }
            
        except Exception as e:
            logger.error(f"获取用户角色失败: {str(e)}")
            raise Exception(f"获取用户角色失败: {str(e)}")
    
    async def assign_user_roles(self, user_id: int, role_ids: List[int]) -> Dict[str, str]:
        """为用户分配角色"""
        try:
            # 首先检查用户是否存在
            user_query = user_table.select().where(user_table.c.id == user_id)
            user_info = await database.fetch_one(user_query)
            
            if not user_info:
                raise ValueError("用户不存在")
            
            # 删除用户现有的所有角色
            delete_query = user_role_table.delete().where(user_role_table.c.user_id == user_id)
            await database.execute(delete_query)
            
            # 为用户分配新角色
            for role_id in role_ids:
                # 检查角色是否存在
                role_query = role_table.select().where(role_table.c.id == role_id)
                role_info = await database.fetch_one(role_query)
                
                if role_info:
                    insert_query = user_role_table.insert().values(
                        user_id=user_id,
                        role_id=role_id
                    )
                    await database.execute(insert_query)
            
            logger.info(f"为用户 {user_info['username']} 分配角色成功")
            
            return {
                "status": "success",
                "message": f"用户角色分配成功"
            }
            
        except Exception as e:
            logger.error(f"分配用户角色失败: {str(e)}")
            raise Exception(f"分配用户角色失败: {str(e)}")
    
    async def remove_user_role(self, user_id: int, role_name: str) -> Dict[str, str]:
        """移除用户的特定角色"""
        try:
            # 首先获取角色ID
            role_query = role_table.select().where(role_table.c.name == role_name)
            role_info = await database.fetch_one(role_query)
            
            if not role_info:
                raise ValueError("角色不存在")
            
            # 删除用户角色关联
            delete_query = user_role_table.delete().where(
                (user_role_table.c.user_id == user_id) &
                (user_role_table.c.role_id == role_info["id"])
            )
            result = await database.execute(delete_query)
            
            if result == 0:
                raise ValueError("用户没有此角色")
            
            logger.info(f"移除用户角色成功: user_id={user_id}, role={role_name}")
            
            return {
                "status": "success",
                "message": f"用户角色 {role_name} 移除成功"
            }
            
        except Exception as e:
            logger.error(f"移除用户角色失败: {str(e)}")
            raise Exception(f"移除用户角色失败: {str(e)}")
    
    # ==========================================
    # 角色管理方法
    # ==========================================
    
    async def get_roles(self) -> List[Dict[str, Any]]:
        """获取所有角色列表"""
        try:
            query = role_table.select().order_by(role_table.c.name)
            roles = await database.fetch_all(query)
            
            role_list = []
            for role in roles:
                role_list.append({
                    "id": role["id"],
                    "name": role["name"],
                    "description": role["description"]
                })
            
            return role_list
            
        except Exception as e:
            logger.error(f"获取角色列表失败: {str(e)}")
            raise Exception(f"获取角色列表失败: {str(e)}")
    
    async def create_role(self, name: str, description: str = "") -> Dict[str, Any]:
        """创建新角色"""
        try:
            # 检查角色名是否已存在
            query = role_table.select().where(role_table.c.name == name)
            existing_role = await database.fetch_one(query)
            
            if existing_role:
                raise ValueError("角色名已存在")
            
            # 创建新角色
            insert_query = role_table.insert().values(
                name=name,
                description=description
            )
            role_id = await database.execute(insert_query)
            
            logger.info(f"创建角色成功: {name}")
            
            return {
                "status": "success",
                "message": "角色创建成功",
                "role": {
                    "id": role_id,
                    "name": name,
                    "description": description
                }
            }
            
        except Exception as e:
            logger.error(f"创建角色失败: {str(e)}")
            raise Exception(f"创建角色失败: {str(e)}")
    
    async def update_role(self, role_id: int, name: str = None, description: str = None) -> Dict[str, str]:
        """更新角色信息"""
        try:
            # 检查角色是否存在
            query = role_table.select().where(role_table.c.id == role_id)
            role_info = await database.fetch_one(query)
            
            if not role_info:
                raise ValueError("角色不存在")
            
            # 构建更新数据
            update_data = {}
            if name is not None:
                # 检查新名称是否与其他角色冲突
                name_query = role_table.select().where(
                    (role_table.c.name == name) & 
                    (role_table.c.id != role_id)
                )
                existing_role = await database.fetch_one(name_query)
                if existing_role:
                    raise ValueError("角色名已存在")
                update_data["name"] = name
            
            if description is not None:
                update_data["description"] = description
            
            if update_data:
                update_query = role_table.update().where(
                    role_table.c.id == role_id
                ).values(**update_data)
                await database.execute(update_query)
            
            logger.info(f"更新角色成功: role_id={role_id}")
            
            return {
                "status": "success",
                "message": "角色更新成功"
            }
            
        except Exception as e:
            logger.error(f"更新角色失败: {str(e)}")
            raise Exception(f"更新角色失败: {str(e)}")
    
    async def delete_role(self, role_id: int) -> Dict[str, str]:
        """删除角色"""
        try:
            # 检查角色是否存在
            query = role_table.select().where(role_table.c.id == role_id)
            role_info = await database.fetch_one(query)
            
            if not role_info:
                raise ValueError("角色不存在")
            
            # 检查是否有用户关联此角色
            user_role_query = user_role_table.select().where(user_role_table.c.role_id == role_id)
            user_roles = await database.fetch_all(user_role_query)
            
            if user_roles:
                raise ValueError("无法删除角色，仍有用户关联此角色")
            
            # 删除角色权限关联
            delete_role_perm_query = role_permission_table.delete().where(
                role_permission_table.c.role_id == role_id
            )
            await database.execute(delete_role_perm_query)
            
            # 删除角色
            delete_query = role_table.delete().where(role_table.c.id == role_id)
            await database.execute(delete_query)
            
            logger.info(f"删除角色成功: {role_info['name']}")
            
            return {
                "status": "success",
                "message": f"角色 {role_info['name']} 删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除角色失败: {str(e)}")
            raise Exception(f"删除角色失败: {str(e)}")
    
    # ==========================================
    # 权限管理方法
    # ==========================================
    
    async def get_permissions(self) -> List[Dict[str, Any]]:
        """获取所有权限列表"""
        try:
            query = permission_table.select().order_by(permission_table.c.name)
            permissions = await database.fetch_all(query)
            
            permission_list = []
            for permission in permissions:
                permission_list.append({
                    "id": permission["id"],
                    "name": permission["name"],
                    "description": permission["description"]
                })
            
            return permission_list
            
        except Exception as e:
            logger.error(f"获取权限列表失败: {str(e)}")
            raise Exception(f"获取权限列表失败: {str(e)}")
    
    async def create_permission(self, name: str, description: str = "") -> Dict[str, Any]:
        """创建新权限"""
        try:
            # 检查权限名是否已存在
            query = permission_table.select().where(permission_table.c.name == name)
            existing_permission = await database.fetch_one(query)
            
            if existing_permission:
                raise ValueError("权限名已存在")
            
            # 创建新权限
            insert_query = permission_table.insert().values(
                name=name,
                description=description
            )
            permission_id = await database.execute(insert_query)
            
            logger.info(f"创建权限成功: {name}")
            
            return {
                "status": "success",
                "message": "权限创建成功",
                "permission": {
                    "id": permission_id,
                    "name": name,
                    "description": description
                }
            }
            
        except Exception as e:
            logger.error(f"创建权限失败: {str(e)}")
            raise Exception(f"创建权限失败: {str(e)}")
    
    async def update_permission(self, permission_id: int, name: str = None, description: str = None) -> Dict[str, str]:
        """更新权限信息"""
        try:
            # 检查权限是否存在
            query = permission_table.select().where(permission_table.c.id == permission_id)
            permission_info = await database.fetch_one(query)
            
            if not permission_info:
                raise ValueError("权限不存在")
            
            # 构建更新数据
            update_data = {}
            if name is not None:
                # 检查新名称是否与其他权限冲突
                name_query = permission_table.select().where(
                    (permission_table.c.name == name) & 
                    (permission_table.c.id != permission_id)
                )
                existing_permission = await database.fetch_one(name_query)
                if existing_permission:
                    raise ValueError("权限名已存在")
                update_data["name"] = name
            
            if description is not None:
                update_data["description"] = description
            
            if update_data:
                update_query = permission_table.update().where(
                    permission_table.c.id == permission_id
                ).values(**update_data)
                await database.execute(update_query)
            
            logger.info(f"更新权限成功: permission_id={permission_id}")
            
            return {
                "status": "success",
                "message": "权限更新成功"
            }
            
        except Exception as e:
            logger.error(f"更新权限失败: {str(e)}")
            raise Exception(f"更新权限失败: {str(e)}")
    
    async def delete_permission(self, permission_id: int) -> Dict[str, str]:
        """删除权限"""
        try:
            # 检查权限是否存在
            query = permission_table.select().where(permission_table.c.id == permission_id)
            permission_info = await database.fetch_one(query)
            
            if not permission_info:
                raise ValueError("权限不存在")
            
            # 删除角色权限关联
            delete_role_perm_query = role_permission_table.delete().where(
                role_permission_table.c.permission_id == permission_id
            )
            await database.execute(delete_role_perm_query)
            
            # 删除权限
            delete_query = permission_table.delete().where(permission_table.c.id == permission_id)
            await database.execute(delete_query)
            
            logger.info(f"删除权限成功: {permission_info['name']}")
            
            return {
                "status": "success",
                "message": f"权限 {permission_info['name']} 删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除权限失败: {str(e)}")
            raise Exception(f"删除权限失败: {str(e)}")
    
    # ==========================================
    # 角色权限管理方法
    # ==========================================
    
    async def get_role_permissions(self, role_id: int) -> Dict[str, Any]:
        """获取角色的权限列表"""
        try:
            # 首先检查角色是否存在
            role_query = role_table.select().where(role_table.c.id == role_id)
            role_info = await database.fetch_one(role_query)
            
            if not role_info:
                raise ValueError("角色不存在")
            
            # 获取角色的权限
            query = """
                SELECT p.id, p.name, p.description
                FROM permission p
                INNER JOIN role_permission rp ON p.id = rp.permission_id
                WHERE rp.role_id = :role_id
                ORDER BY p.name
            """
            
            permissions = await database.fetch_all(query, {"role_id": role_id})
            
            permission_list = []
            for permission in permissions:
                permission_list.append({
                    "id": permission["id"],
                    "name": permission["name"],
                    "description": permission["description"]
                })
            
            return {
                "role_id": role_id,
                "role_name": role_info["name"],
                "permissions": permission_list
            }
            
        except Exception as e:
            logger.error(f"获取角色权限失败: {str(e)}")
            raise Exception(f"获取角色权限失败: {str(e)}")
    
    async def assign_role_permissions(self, role_id: int, permission_ids: List[int]) -> Dict[str, str]:
        """为角色分配权限"""
        try:
            # 首先检查角色是否存在
            role_query = role_table.select().where(role_table.c.id == role_id)
            role_info = await database.fetch_one(role_query)
            
            if not role_info:
                raise ValueError("角色不存在")
            
            # 删除角色现有的所有权限
            delete_query = role_permission_table.delete().where(role_permission_table.c.role_id == role_id)
            await database.execute(delete_query)
            
            # 为角色分配新权限
            for permission_id in permission_ids:
                # 检查权限是否存在
                permission_query = permission_table.select().where(permission_table.c.id == permission_id)
                permission_info = await database.fetch_one(permission_query)
                
                if permission_info:
                    insert_query = role_permission_table.insert().values(
                        role_id=role_id,
                        permission_id=permission_id
                    )
                    await database.execute(insert_query)
            
            logger.info(f"为角色 {role_info['name']} 分配权限成功")
            
            return {
                "status": "success",
                "message": f"角色权限分配成功"
            }
            
        except Exception as e:
            logger.error(f"分配角色权限失败: {str(e)}")
            raise Exception(f"分配角色权限失败: {str(e)}")
    
    async def remove_role_permission(self, role_id: int, permission_id: int) -> Dict[str, str]:
        """移除角色的特定权限"""
        try:
            # 删除角色权限关联
            delete_query = role_permission_table.delete().where(
                (role_permission_table.c.role_id == role_id) &
                (role_permission_table.c.permission_id == permission_id)
            )
            result = await database.execute(delete_query)
            
            if result == 0:
                raise ValueError("角色没有此权限")
            
            logger.info(f"移除角色权限成功: role_id={role_id}, permission_id={permission_id}")
            
            return {
                "status": "success",
                "message": "角色权限移除成功"
            }
            
        except Exception as e:
            logger.error(f"移除角色权限失败: {str(e)}")
            raise Exception(f"移除角色权限失败: {str(e)}")
    
    # ==========================================
    # 权限分组和层级管理方法
    # ==========================================
    
    async def get_permission_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取权限分组"""
        try:
            # 获取所有权限
            permissions = await self.get_permissions()
            
            # 按权限名称的前缀进行分组
            groups = {
                "系统管理": [],
                "用户管理": [],
                "角色管理": [],
                "权限管理": [],
                "内容管理": [],
                "构建管理": [],
                "其他": []
            }
            
            for permission in permissions:
                name = permission["name"]
                
                if name.startswith("super_admin") or name.startswith("admin_access") or name.startswith("system."):
                    groups["系统管理"].append(permission)
                elif name.startswith("user."):
                    groups["用户管理"].append(permission)
                elif name.startswith("role."):
                    groups["角色管理"].append(permission)
                elif name.startswith("permission."):
                    groups["权限管理"].append(permission)
                elif name.startswith("content.") or name.startswith("file."):
                    groups["内容管理"].append(permission)
                elif name.startswith("build.") or name.startswith("epub_conversion") or name.startswith("manual_backup"):
                    groups["构建管理"].append(permission)
                else:
                    groups["其他"].append(permission)
            
            return groups
            
        except Exception as e:
            logger.error(f"获取权限分组失败: {str(e)}")
            raise Exception(f"获取权限分组失败: {str(e)}")
    
    async def get_role_hierarchy(self) -> List[Dict[str, Any]]:
        """获取角色层级结构"""
        try:
            roles = await self.get_roles()
            
            # 定义角色层级顺序
            hierarchy_order = {
                "super_admin": 1,
                "admin": 2,
                "editor": 3,
                "user": 4,
                "guest": 5
            }
            
            # 为每个角色添加层级信息
            for role in roles:
                role_name = role["name"]
                role["level"] = hierarchy_order.get(role_name, 999)  # 默认级别为999
                role["level_name"] = self._get_role_level_name(role["level"])
            
            # 按层级排序
            roles.sort(key=lambda x: x["level"])
            
            return roles
            
        except Exception as e:
            logger.error(f"获取角色层级失败: {str(e)}")
            raise Exception(f"获取角色层级失败: {str(e)}")
    
    def _get_role_level_name(self, level: int) -> str:
        """获取角色层级名称"""
        level_names = {
            1: "超级管理员",
            2: "管理员",
            3: "编辑者",
            4: "普通用户",
            5: "访客"
        }
        return level_names.get(level, "自定义角色")
    
    # ==========================================
    # 默认角色和权限初始化方法
    # ==========================================
    
    async def initialize_default_roles_and_permissions(self) -> Dict[str, Any]:
        """初始化默认角色和权限"""
        try:
            # 定义默认权限
            default_permissions = [
                {"name": "super_admin", "description": "超级管理员权限"},
                {"name": "admin_access", "description": "管理员访问权限"},
                {"name": "user.list", "description": "查看用户列表"},
                {"name": "user.create", "description": "创建用户"},
                {"name": "user.edit", "description": "编辑用户"},
                {"name": "user.delete", "description": "删除用户"},
                {"name": "role.list", "description": "查看角色列表"},
                {"name": "role.create", "description": "创建角色"},
                {"name": "role.edit", "description": "编辑角色"},
                {"name": "role.delete", "description": "删除角色"},
                {"name": "permission.list", "description": "查看权限列表"},
                {"name": "permission.create", "description": "创建权限"},
                {"name": "permission.edit", "description": "编辑权限"},
                {"name": "permission.delete", "description": "删除权限"},
                {"name": "content.edit", "description": "编辑内容"},
                {"name": "file.manage", "description": "文件管理"},
                {"name": "build.epub", "description": "EPUB构建权限"},
                {"name": "build.pdf", "description": "PDF构建权限"},
                {"name": "build.html", "description": "HTML构建权限"},
                {"name": "epub_conversion", "description": "EPUB转换权限"},
                {"name": "manual_backup", "description": "手动备份权限"},
                {"name": "system.config", "description": "系统配置权限"},
                {"name": "theme_access", "description": "主题访问权限"}
            ]
            
            # 创建默认权限
            created_permissions = []
            for perm in default_permissions:
                try:
                    result = await self.create_permission(perm["name"], perm["description"])
                    created_permissions.append(perm["name"])
                except ValueError:
                    # 权限已存在，跳过
                    pass
            
            # 定义默认角色
            default_roles = [
                {"name": "super_admin", "description": "超级管理员，拥有所有权限"},
                {"name": "admin", "description": "管理员，拥有用户和内容管理权限"},
                {"name": "editor", "description": "编辑者，拥有内容编辑权限"},
                {"name": "user", "description": "普通用户，拥有基本访问权限"}
            ]
            
            # 创建默认角色
            created_roles = []
            for role in default_roles:
                try:
                    result = await self.create_role(role["name"], role["description"])
                    created_roles.append(role["name"])
                except ValueError:
                    # 角色已存在，跳过
                    pass
            
            # 为角色分配权限
            await self._assign_default_role_permissions()
            
            return {
                "status": "success",
                "message": "默认角色和权限初始化完成",
                "created_permissions": created_permissions,
                "created_roles": created_roles
            }
            
        except Exception as e:
            logger.error(f"初始化默认角色和权限失败: {str(e)}")
            raise Exception(f"初始化默认角色和权限失败: {str(e)}")
    
    async def _assign_default_role_permissions(self):
        """为默认角色分配权限"""
        try:
            # 获取所有权限
            permissions = await self.get_permissions()
            permission_map = {p["name"]: p["id"] for p in permissions}
            
            # 获取所有角色
            roles = await self.get_roles()
            role_map = {r["name"]: r["id"] for r in roles}
            
            # 为super_admin分配所有权限
            if "super_admin" in role_map:
                all_permission_ids = list(permission_map.values())
                await self.assign_role_permissions(role_map["super_admin"], all_permission_ids)
            
            # 为admin分配管理权限
            if "admin" in role_map:
                admin_permissions = [
                    "admin_access", "user.list", "user.create", "user.edit", "user.delete",
                    "role.list", "content.edit", "file.manage", "build.epub", "build.pdf",
                    "build.html", "epub_conversion", "manual_backup", "system.config"
                ]
                admin_permission_ids = [permission_map[p] for p in admin_permissions if p in permission_map]
                await self.assign_role_permissions(role_map["admin"], admin_permission_ids)
            
            # 为editor分配编辑权限
            if "editor" in role_map:
                editor_permissions = [
                    "content.edit", "file.manage", "build.epub", "build.html", "theme_access"
                ]
                editor_permission_ids = [permission_map[p] for p in editor_permissions if p in permission_map]
                await self.assign_role_permissions(role_map["editor"], editor_permission_ids)
            
            # 为user分配基本权限
            if "user" in role_map:
                user_permissions = ["theme_access", "content.edit"]
                user_permission_ids = [permission_map[p] for p in user_permissions if p in permission_map]
                await self.assign_role_permissions(role_map["user"], user_permission_ids)
            
            logger.info("默认角色权限分配完成")
            
        except Exception as e:
            logger.error(f"分配默认角色权限失败: {str(e)}")
            raise
    
    # ==========================================
    # 审计和日志功能
    # ==========================================
    
    async def log_role_permission_change(self, operation: str, operator: str, target_type: str, 
                                       target_id: int, target_name: str = None, old_values: Dict[str, Any] = None,
                                       new_values: Dict[str, Any] = None, details: Dict[str, Any] = None,
                                       ip_address: str = None, user_agent: str = None) -> None:
        """记录角色权限变更日志"""
        try:
            log_entry = {
                "operation": operation,  # create, update, delete, assign, remove
                "operator": operator,
                "target_type": target_type,  # user, role, permission
                "target_id": target_id,
                "target_name": target_name,
                "old_values": json.dumps(old_values, ensure_ascii=False) if old_values else None,
                "new_values": json.dumps(new_values, ensure_ascii=False) if new_values else None,
                "details": json.dumps(details, ensure_ascii=False) if details else None,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            # 将日志写入数据库
            query = audit_log_table.insert().values(**log_entry)
            await database.execute(query)
            
            # 同时写入日志文件
            logger.info(f"角色权限变更: {json.dumps(log_entry, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"记录角色权限变更日志失败: {str(e)}")
    
    async def get_permission_audit_log(self, days: int = 30, operation: str = None, 
                                     operator: str = None, target_type: str = None,
                                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取权限审计日志"""
        try:
            # 构建查询条件
            conditions = []
            
            # 时间范围过滤
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            conditions.append(audit_log_table.c.timestamp >= cutoff_date)
            
            # 可选过滤条件
            if operation:
                conditions.append(audit_log_table.c.operation == operation)
            if operator:
                conditions.append(audit_log_table.c.operator == operator)
            if target_type:
                conditions.append(audit_log_table.c.target_type == target_type)
            
            # 构建查询
            query = audit_log_table.select()
            if conditions:
                from sqlalchemy import and_
                query = query.where(and_(*conditions))
            
            query = query.order_by(audit_log_table.c.timestamp.desc()).limit(limit).offset(offset)
            
            # 执行查询
            results = await database.fetch_all(query)
            
            # 转换结果
            logs = []
            for row in results:
                log_entry = {
                    "id": row["id"],
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    "operation": row["operation"],
                    "operator": row["operator"],
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "target_name": row["target_name"],
                    "old_values": json.loads(row["old_values"]) if row["old_values"] else None,
                    "new_values": json.loads(row["new_values"]) if row["new_values"] else None,
                    "details": json.loads(row["details"]) if row["details"] else None,
                    "ip_address": row["ip_address"],
                    "user_agent": row["user_agent"]
                }
                logs.append(log_entry)
            
            return logs
            
        except Exception as e:
            logger.error(f"获取审计日志失败: {str(e)}")
            return []
    
    async def get_audit_log_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取审计日志统计信息"""
        try:
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            # 统计总数
            count_query = f"""
                SELECT COUNT(*) as total_count
                FROM audit_log
                WHERE timestamp >= '{cutoff_date.isoformat()}'
            """
            total_result = await database.fetch_one(count_query)
            total_count = total_result["total_count"] if total_result else 0
            
            # 按操作类型统计
            operation_query = f"""
                SELECT operation, COUNT(*) as count
                FROM audit_log
                WHERE timestamp >= '{cutoff_date.isoformat()}'
                GROUP BY operation
                ORDER BY count DESC
            """
            operation_stats = await database.fetch_all(operation_query)
            
            # 按操作者统计
            operator_query = f"""
                SELECT operator, COUNT(*) as count
                FROM audit_log
                WHERE timestamp >= '{cutoff_date.isoformat()}'
                GROUP BY operator
                ORDER BY count DESC
                LIMIT 10
            """
            operator_stats = await database.fetch_all(operator_query)
            
            # 按目标类型统计
            target_type_query = f"""
                SELECT target_type, COUNT(*) as count
                FROM audit_log
                WHERE timestamp >= '{cutoff_date.isoformat()}'
                GROUP BY target_type
                ORDER BY count DESC
            """
            target_type_stats = await database.fetch_all(target_type_query)
            
            return {
                "total_count": total_count,
                "days": days,
                "period_start": cutoff_date.isoformat(),
                "period_end": datetime.datetime.utcnow().isoformat(),
                "operation_statistics": [dict(row) for row in operation_stats],
                "operator_statistics": [dict(row) for row in operator_stats],
                "target_type_statistics": [dict(row) for row in target_type_stats]
            }
            
        except Exception as e:
            logger.error(f"获取审计日志统计失败: {str(e)}")
            return {"error": str(e)}
    
    # ==========================================
    # 批量操作方法
    # ==========================================
    
    async def batch_assign_users_to_role(self, user_ids: List[int], role_id: int) -> Dict[str, Any]:
        """批量为用户分配角色"""
        try:
            success_count = 0
            failed_users = []
            
            for user_id in user_ids:
                try:
                    # 检查用户是否存在
                    user_query = user_table.select().where(user_table.c.id == user_id)
                    user_info = await database.fetch_one(user_query)
                    
                    if user_info:
                        # 检查是否已有此角色
                        existing_role = await database.fetch_one(
                            user_role_table.select().where(
                                (user_role_table.c.user_id == user_id) &
                                (user_role_table.c.role_id == role_id)
                            )
                        )
                        
                        if not existing_role:
                            # 分配角色
                            insert_query = user_role_table.insert().values(
                                user_id=user_id,
                                role_id=role_id
                            )
                            await database.execute(insert_query)
                            success_count += 1
                        else:
                            success_count += 1  # 已有角色也算成功
                    else:
                        failed_users.append({"user_id": user_id, "reason": "用户不存在"})
                        
                except Exception as e:
                    failed_users.append({"user_id": user_id, "reason": str(e)})
            
            return {
                "status": "success" if len(failed_users) == 0 else "partial",
                "message": f"批量分配角色完成，成功: {success_count}, 失败: {len(failed_users)}",
                "success_count": success_count,
                "failed_users": failed_users
            }
            
        except Exception as e:
            logger.error(f"批量分配角色失败: {str(e)}")
            raise Exception(f"批量分配角色失败: {str(e)}")
    
    async def batch_remove_users_from_role(self, user_ids: List[int], role_id: int) -> Dict[str, Any]:
        """批量移除用户角色"""
        try:
            success_count = 0
            failed_users = []
            
            for user_id in user_ids:
                try:
                    # 删除用户角色关联
                    delete_query = user_role_table.delete().where(
                        (user_role_table.c.user_id == user_id) &
                        (user_role_table.c.role_id == role_id)
                    )
                    result = await database.execute(delete_query)
                    
                    if result > 0:
                        success_count += 1
                    else:
                        failed_users.append({"user_id": user_id, "reason": "用户没有此角色"})
                        
                except Exception as e:
                    failed_users.append({"user_id": user_id, "reason": str(e)})
            
            return {
                "status": "success" if len(failed_users) == 0 else "partial",
                "message": f"批量移除角色完成，成功: {success_count}, 失败: {len(failed_users)}",
                "success_count": success_count,
                "failed_users": failed_users
            }
            
        except Exception as e:
            logger.error(f"批量移除角色失败: {str(e)}")
            raise Exception(f"批量移除角色失败: {str(e)}")
    
    async def reset_user_src_directory(self, username: str) -> Dict[str, Any]:
        """重置用户的Src目录
        
        这个方法将：
        1. 创建用户对应的备份（自动备份当前目录）
        2. 删除用户当前的src目录
        3. 重新创建用户的src目录
        4. 从公共src目录复制所有文件到用户的src目录
        
        Args:
            username: 用户名
            
        Returns:
            包含操作结果的字典
        """
        try:
            # 验证用户名格式
            if not username or not username.strip():
                raise ValueError("用户名不能为空")
            
            # 获取用户的src目录路径
            user_src_dir = get_user_src_directory(username)
            
            # 检查用户目录是否存在
            if not user_src_dir.exists():
                logger.info(f"用户 {username} 的src目录不存在，将创建新目录")
            else:
                # 如果目录存在，先创建备份
                try:
                    backup_result = await self.create_backup(username)
                    logger.info(f"为用户 {username} 创建重置前备份: {backup_result.get('filename', 'unknown')}")
                except Exception as backup_error:
                    logger.warning(f"创建备份失败，但继续重置操作: {str(backup_error)}")
                
                # 删除现有的src目录
                shutil.rmtree(user_src_dir)
                logger.info(f"删除用户 {username} 的现有src目录: {user_src_dir}")
            
            # 重新创建并复制默认文件
            copy_default_files_to_user_directory(username)
            logger.info(f"为用户 {username} 重新创建src目录并复制默认文件")
            
            # 获取复制后的文件统计信息
            file_count = 0
            dir_count = 0
            total_size = 0
            
            for item in user_src_dir.rglob('*'):
                if item.is_file():
                    file_count += 1
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        pass
                elif item.is_dir():
                    dir_count += 1
            
            return {
                "status": "success",
                "message": f"用户 {username} 的src目录重置成功",
                "username": username,
                "src_directory": str(user_src_dir),
                "statistics": {
                    "files_copied": file_count,
                    "directories_created": dir_count,
                    "total_size_bytes": total_size
                },
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"重置用户src目录失败: {str(e)}")
            raise Exception(f"重置用户src目录失败: {str(e)}")