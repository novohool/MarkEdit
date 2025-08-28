"""
Startup service for MarkEdit application.

This module contains business logic for application startup including:
- Database initialization and connection
- Default roles and permissions setup
- Default admin user creation
- Application configuration
- Cleanup operations
"""
import asyncio
import asyncpg
import logging
import datetime
import zipfile
import os
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy import create_engine

from app.config import CREATE_DB_ON_STARTUP, DATABASE_CONFIG
from app.common import (
    database, metadata, DATABASE_URL,
    admin_table, user_table, role_table, user_role_table, 
    permission_table, role_permission_table,
    generate_random_password, hash_password,
    copy_default_files_to_user_directory
)

logger = logging.getLogger(__name__)

class StartupService:
    """应用启动服务类"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.src_dir = self.base_dir / "src"
    
    async def startup_initialization(self):
        """应用启动时的初始化逻辑"""
        logger.info("开始应用启动初始化...")
        
        # 如果配置要求创建数据库和表
        if CREATE_DB_ON_STARTUP:
            await self._ensure_database_exists()
        
        # 连接数据库（在确保数据库存在之后）
        try:
            await database.connect()
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            if CREATE_DB_ON_STARTUP:
                # 如果是自动创建模式，再次尝试创建数据库
                logger.info("尝试重新创建数据库...")
                await self._ensure_database_exists()
                await database.connect()
                logger.info("数据库连接成功")
            else:
                raise
        
        # 如果配置要求创建数据库和表
        if CREATE_DB_ON_STARTUP:
            # 创建表
            engine = create_engine(DATABASE_URL)
            metadata.create_all(engine)
            logger.info("数据库表创建完成")
            
            # 初始化默认角色和权限
            await self.init_roles_and_permissions()
            
            # 初始化默认超级管理员用户markedit
            await self.init_default_superadmin_user()
            
        logger.info("应用启动完成")
    
    async def shutdown_cleanup(self):
        """应用关闭时的清理逻辑"""
        # 断开数据库连接
        await database.disconnect()
        logger.info("数据库连接已断开")
    
    async def _ensure_database_exists(self):
        """确保数据库存在"""
        try:
            # 获取数据库配置
            db_config = DATABASE_CONFIG.copy()
            db_name = db_config.pop('database')  # 移除数据库名
            
            # 使用默认的postgres数据库
            postgres_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/postgres"
            
            # 连接到PostgreSQL服务器
            conn = await asyncpg.connect(postgres_url)
            
            # 检查数据库是否存在
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name
            )
            
            # 如果数据库不存在，则创建它
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"数据库 '{db_name}' 创建成功")
            else:
                logger.info(f"数据库 '{db_name}' 已存在")
            
            # 关闭连接
            await conn.close()
        except Exception as e:
            logger.error(f"数据库创建检查过程中出错: {str(e)}")
            raise
    

    
    async def init_roles_and_permissions(self):
        """初始化默认角色和权限"""
        # 检查是否已存在默认角色
        query = role_table.select()
        existing_roles = await database.fetch_all(query)
        
        # 如果没有角色，则创建默认角色
        if not existing_roles:
            roles = [
                {"name": "super_admin", "description": "超级管理员，拥有所有系统权限"},
                {"name": "admin", "description": "管理员"},
                {"name": "user", "description": "普通用户"}
            ]
            
            for role_data in roles:
                query = role_table.insert().values(**role_data)
                await database.execute(query)
            
            logger.info("默认角色创建完成")
        
        # 检查是否已存在权限
        query = permission_table.select()
        existing_permissions = await database.fetch_all(query)
        
        # 如果没有权限，则创建默认权限
        if not existing_permissions:
            await self._create_default_permissions()
            logger.info("默认权限创建完成")
            
            # 为默认角色分配权限
            await self.assign_default_role_permissions()
        else:
            # 即使权限已存在，也要确保默认角色权限分配正确
            await self.assign_default_role_permissions()
    
    async def _create_default_permissions(self):
        """创建默认权限"""
        permissions = [
            # 用户管理权限
            {"name": "user.create", "description": "创建用户"},
            {"name": "user.edit", "description": "编辑用户信息"},
            {"name": "user.delete", "description": "删除用户"},
            {"name": "user.list", "description": "查看用户列表"},
            {"name": "user.self_info", "description": "查看自己的信息"},
            {"name": "user.self_edit", "description": "编辑自己的信息"},
            
            # 角色管理权限
            {"name": "role.create", "description": "创建角色"},
            {"name": "role.edit", "description": "编辑角色"},
            {"name": "role.delete", "description": "删除角色"},
            {"name": "role.list", "description": "查看角色列表"},
            
            # 权限管理权限
            {"name": "permission.create", "description": "创建权限"},
            {"name": "permission.edit", "description": "编辑权限"},
            {"name": "permission.delete", "description": "删除权限"},
            {"name": "permission.list", "description": "查看权限列表"},
            
            # 系统管理权限
            {"name": "system.backup", "description": "系统备份"},
            {"name": "system.config", "description": "系统配置"},
            {"name": "content.edit", "description": "内容编辑"},
            
            # 特殊功能权限
            {"name": "epub_conversion", "description": "EPUB转换"},
            {"name": "manual_backup", "description": "手动备份"},
            {"name": "theme_access", "description": "主题访问"},
            {"name": "admin_access", "description": "管理员界面访问"},
            {"name": "super_admin", "description": "超级管理员权限"},
            
            # 文件操作权限
            {"name": "file.read", "description": "文件读取"},
            {"name": "file.write", "description": "文件写入"},
            
            # 构建权限
            {"name": "build.epub", "description": "EPUB构建"},
            {"name": "build.pdf", "description": "PDF构建"},
        ]
        
        for permission_data in permissions:
            query = permission_table.insert().values(**permission_data)
            await database.execute(query)
    
    async def assign_default_role_permissions(self):
        """为默认角色分配权限"""
        # 获取所有角色
        roles_query = role_table.select()
        roles = await database.fetch_all(roles_query)
        role_dict = {role["name"]: role["id"] for role in roles}
        
        # 获取所有权限
        permissions_query = permission_table.select()
        permissions = await database.fetch_all(permissions_query)
        permission_dict = {perm["name"]: perm["id"] for perm in permissions}
        
        # 定义角色权限映射
        role_permissions = {
            "super_admin": [
                # 超级管理员拥有所有权限
                "user.create", "user.edit", "user.delete", "user.list", "user.self_info", "user.self_edit",
                "role.create", "role.edit", "role.delete", "role.list",
                "permission.create", "permission.edit", "permission.delete", "permission.list",
                "system.backup", "system.config", "content.edit",
                "epub_conversion", "manual_backup", "theme_access", "admin_access", "super_admin",
                "file.read", "file.write", "build.epub", "build.pdf"
            ],
            "admin": [
                # 管理员权限
                "user.list", "user.self_info", "user.self_edit",
                "content.edit", "epub_conversion", "manual_backup", "theme_access", "admin_access",
                "file.read", "file.write", "build.epub", "build.pdf"
            ],
            "user": [
                # 普通用户权限
                "user.self_info", "user.self_edit", "user.list",
                "content.edit", "theme_access", "epub_conversion", "manual_backup", "system.backup",
                "file.read", "file.write", "build.epub", "build.pdf"
            ]
        }
        
        # 清理现有的角色权限关联（防止重复）
        for role_name in role_permissions:
            if role_name in role_dict:
                role_id = role_dict[role_name]
                delete_query = role_permission_table.delete().where(
                    role_permission_table.c.role_id == role_id
                )
                await database.execute(delete_query)
        
        # 分配权限
        for role_name, perms in role_permissions.items():
            if role_name in role_dict:
                role_id = role_dict[role_name]
                
                for perm_name in perms:
                    if perm_name in permission_dict:
                        permission_id = permission_dict[perm_name]
                        
                        # 插入角色权限关联
                        query = role_permission_table.insert().values(
                            role_id=role_id,
                            permission_id=permission_id
                        )
                        await database.execute(query)
                
                logger.info(f"为角色 {role_name} 分配了 {len(perms)} 个权限")
    
    async def init_default_superadmin_user(self):
        """初始化默认超级管理员用户"""
        original_username = "markedit"
        # 为超级管理员添加前缀
        username = f"super_admin_{original_username}"
        
        try:
            # 检查用户是否已存在
            query = user_table.select().where(user_table.c.username == username)
            existing_user = await database.fetch_one(query)
            
            if existing_user:
                logger.info(f"默认超级管理员用户 {username} 已存在")
                # 确保用户有正确的角色
                await self._ensure_user_has_super_admin_role(existing_user["id"])
                # 确保超管用户目录和默认文件存在
                logger.info(f"检查超管用户 {username} 的目录设置")
                copy_default_files_to_user_directory(username)
                return
                
            # 检查是否存在旧的不带前缀的用户，如果存在则迁移
            old_query = user_table.select().where(user_table.c.username == original_username)
            old_user = await database.fetch_one(old_query)
            
            if old_user:
                logger.info(f"发现旧的超管用户 {original_username}，开始迁移到新的前缀格式")
                await self._migrate_old_superadmin_user(old_user, username)
                return
            
            # 生成随机密码
            password = generate_random_password()
            hashed_password = hash_password(password)
            
            # 创建用户
            query = user_table.insert().values(
                username=username,
                password=hashed_password,
                user_type="admin",
                theme="default"
            )
            user_id = await database.execute(query)
            
            # 同时在admin表中创建记录（向后兼容）
            query = admin_table.insert().values(
                username=username,
                password=hashed_password
            )
            await database.execute(query)
            
            # 分配超级管理员角色
            await self._assign_super_admin_role(user_id)
            
            # 复制默认文件到超管用户目录
            logger.info(f"为超管用户 {username} 设置用户目录")
            copy_default_files_to_user_directory(username)
            
            logger.info(f"默认超级管理员用户创建成功: {username}")
            logger.info(f"显示用户名（不含前缀）: {original_username}")
            logger.info(f"数据库用户名（含前缀）: {username}")
            logger.info(f"默认密码: {password}")
            logger.warning("请及时修改默认密码！")
            
        except Exception as e:
            logger.error(f"创建默认超级管理员用户失败: {str(e)}")
            raise
    
    async def _ensure_user_has_super_admin_role(self, user_id: int):
        """确保用户拥有超级管理员角色"""
        # 获取super_admin角色ID
        query = role_table.select().where(role_table.c.name == "super_admin")
        role_info = await database.fetch_one(query)
        
        if not role_info:
            logger.error("super_admin角色不存在")
            return
        
        role_id = role_info["id"]
        
        # 检查用户是否已有该角色
        query = user_role_table.select().where(
            (user_role_table.c.user_id == user_id) &
            (user_role_table.c.role_id == role_id)
        )
        existing_role = await database.fetch_one(query)
        
        if not existing_role:
            # 分配角色
            query = user_role_table.insert().values(
                user_id=user_id,
                role_id=role_id
            )
            await database.execute(query)
            logger.info(f"为用户ID {user_id} 分配了super_admin角色")
    
    async def _assign_super_admin_role(self, user_id: int):
        """为用户分配超级管理员角色"""
        # 获取super_admin角色ID
        query = role_table.select().where(role_table.c.name == "super_admin")
        role_info = await database.fetch_one(query)
        
        if not role_info:
            logger.error("super_admin角色不存在")
            return
        
        role_id = role_info["id"]
        
        # 分配角色
        query = user_role_table.insert().values(
            user_id=user_id,
            role_id=role_id
        )
        await database.execute(query)
        
        logger.info(f"为用户ID {user_id} 分配了super_admin角色")
    
    async def _migrate_old_superadmin_user(self, old_user: dict, new_username: str):
        """迁移旧的超管用户到新的前缀格式"""
        old_username = old_user["username"]
        
        try:
            # 更新用户表中的用户名
            update_query = user_table.update().where(
                user_table.c.id == old_user["id"]
            ).values(username=new_username)
            await database.execute(update_query)
            
            # 更新admin表中的用户名（如果存在）
            admin_update_query = admin_table.update().where(
                admin_table.c.username == old_username
            ).values(username=new_username)
            await database.execute(admin_update_query)
            
            # 确保用户有超级管理员角色
            await self._ensure_user_has_super_admin_role(old_user["id"])
            
            # 迁移用户目录
            await self._migrate_user_directory(old_username, new_username)
            
            logger.info(f"成功迁移超管用户：{old_username} -> {new_username}")
            
        except Exception as e:
            logger.error(f"迁移超管用户失败: {str(e)}")
            raise
    
    async def _migrate_user_directory(self, old_username: str, new_username: str):
        """迁移用户目录并处理其中的超链接"""
        from app.common.services import get_directory_manager
        import shutil
        import re
        
        directory_manager = get_directory_manager()
        
        try:
            old_user_dir = directory_manager.get_user_directory(old_username)
            new_user_dir = directory_manager.get_user_directory(new_username)
            
            if old_user_dir.exists():
                # 如果新目录已存在，先备份
                if new_user_dir.exists():
                    backup_dir = new_user_dir.parent / f"{new_username}_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(str(new_user_dir), str(backup_dir))
                    logger.info(f"备份现有目录: {new_user_dir} -> {backup_dir}")
                
                # 移动目录
                shutil.move(str(old_user_dir), str(new_user_dir))
                logger.info(f"移动用户目录: {old_user_dir} -> {new_user_dir}")
                
                # 处理src目录中的超链接
                src_dir = new_user_dir / "src"
                if src_dir.exists():
                    await self._update_hyperlinks_in_directory(src_dir, old_username, new_username)
                    
            else:
                # 如果旧目录不存在，创建新目录并复制默认文件
                logger.info(f"旧用户目录不存在，为新用户创建目录: {new_username}")
                copy_default_files_to_user_directory(new_username)
                
        except Exception as e:
            logger.error(f"迁移用户目录失败: {str(e)}")
            raise
    
    async def _update_hyperlinks_in_directory(self, directory: Path, old_username: str, new_username: str):
        """更新目录中所有markdown文件的超链接"""
        try:
            for file_path in directory.rglob("*.md"):
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 替换超链接中的用户名
                    # 匹配 /user-illustrations/old_username/ 格式
                    old_pattern = f"/user-illustrations/{re.escape(old_username)}/"
                    new_replacement = f"/user-illustrations/{new_username}/"
                    updated_content = re.sub(old_pattern, new_replacement, content)
                    
                    # 如果内容有变化，写回文件
                    if updated_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(updated_content)
                        logger.info(f"更新文件中的超链接: {file_path}")
                        
                except Exception as e:
                    logger.warning(f"更新文件超链接失败 {file_path}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"更新目录超链接失败: {str(e)}")
    
    async def get_startup_info(self) -> Dict[str, Any]:
        """获取启动信息"""
        try:
            startup_info = {
                "database_connected": False,
                "database_config": {
                    "host": DATABASE_CONFIG['host'],
                    "port": DATABASE_CONFIG['port'],
                    "database": DATABASE_CONFIG['database'],
                    "user": DATABASE_CONFIG['user']
                },
                "create_db_on_startup": CREATE_DB_ON_STARTUP,
                "src_directory_exists": self.src_dir.exists(),
                "base_directory": str(self.base_dir),
                "src_directory": str(self.src_dir)
            }
            
            # 检查数据库连接状态
            try:
                # 简单查询测试连接
                query = "SELECT 1"
                await database.fetch_one(query)
                startup_info["database_connected"] = True
            except Exception as e:
                startup_info["database_error"] = str(e)
            
            # 统计角色和权限信息
            if startup_info["database_connected"]:
                try:
                    # 统计角色数量
                    query = role_table.select()
                    roles = await database.fetch_all(query)
                    startup_info["roles_count"] = len(roles)
                    
                    # 统计权限数量
                    query = permission_table.select()
                    permissions = await database.fetch_all(query)
                    startup_info["permissions_count"] = len(permissions)
                    
                    # 统计用户数量
                    query = user_table.select()
                    users = await database.fetch_all(query)
                    startup_info["users_count"] = len(users)
                    
                except Exception as e:
                    startup_info["stats_error"] = str(e)
            
            return startup_info
            
        except Exception as e:
            logger.error(f"获取启动信息失败: {str(e)}")
            return {
                "error": f"获取启动信息失败: {str(e)}",
                "database_connected": False,
                "create_db_on_startup": CREATE_DB_ON_STARTUP,
                "base_directory": str(self.base_dir),
                "src_directory": str(self.src_dir)
            }