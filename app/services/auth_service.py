"""
Authentication service for MarkEdit application.

This module contains business logic for authentication and authorization.
"""
import logging
from typing import Dict, List
from sqlalchemy import create_engine

from app.config import CREATE_DB_ON_STARTUP, DATABASE_CONFIG
from app.common import (
    database, metadata, DATABASE_URL,
    admin_table, user_table, role_table, user_role_table, 
    permission_table, role_permission_table,
    generate_random_password, hash_password
)

logger = logging.getLogger(__name__)

class AuthService:
    """认证服务类"""
    
    async def startup_initialization(self):
        """应用启动时的初始化逻辑"""
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
    
    # 注意：shutdown_cleanup 函数已迁移到 startup_service.py
    
    # 注意：_ensure_database_exists 函数已迁移到 startup_service.py
    
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
    
    # 注意：_create_default_permissions 函数已迁移到 startup_service.py
    
    # 注意：assign_default_role_permissions 函数已迁移到 startup_service.py
    
    def _get_role_permission_mapping(self) -> Dict[str, List[str]]:
        """获取角色权限映射关系"""
        return {
            "super_admin": [
                # 用户管理权限
                "user.create", "user.edit", "user.delete", "user.list",
                # 角色管理权限
                "role.create", "role.edit", "role.delete", "role.list",
                # 权限管理权限
                "permission.create", "permission.edit", "permission.delete", "permission.list",
                # 系统管理权限
                "system.backup", "system.config", "content.edit",
                # 特殊功能权限
                "epub_conversion", "manual_backup", "theme_access", "admin_access", "super_admin",
                # 用户自身管理权限
                "user.self_info", "user.self_edit",
                # 文件操作权限
                "file.read", "file.write",
                # 构建权限
                "build.epub", "build.pdf"
            ],
            "admin": [
                # 用户管理权限（除了删除用户）
                "user.create", "user.edit", "user.list",
                # 角色管理权限（查看和编辑角色）
                "role.list", "role.edit",
                # 权限管理权限（查看和编辑权限）
                "permission.list", "permission.edit",
                # 基础功能权限
                "content.edit", "theme_access", "epub_conversion", "manual_backup", "system.backup",
                # 用户自身管理权限
                "user.self_info", "user.self_edit",
                # 文件操作权限
                "file.read", "file.write",
                # 构建权限
                "build.epub", "build.pdf",
                # 管理员访问权限
                "admin_access"
            ],
            "user": [
                # 基础功能权限
                "content.edit", "theme_access", "epub_conversion", "manual_backup", "system.backup",
                "user.list",  # 普通用户可以查看用户列表但不能增删改
                # 用户自身管理权限
                "user.self_info", "user.self_edit",
                # 文件操作权限
                "file.read", "file.write",
                # 构建权限
                "build.epub", "build.pdf"
            ]
        }
    
    async def init_default_superadmin_user(self):
        """初始化默认超级管理员用户 markedit"""
        try:
            # 检查 markedit 用户是否已在 user_table 中存在
            query = user_table.select().where(user_table.c.username == "markedit")
            existing_user = await database.fetch_one(query)
            
            if not existing_user:
                # 在 user_table 中创建 markedit 用户
                query = user_table.insert().values(
                    username="markedit",
                    user_type="admin",
                    theme="default",
                    llm_config="{}"
                )
                user_id = await database.execute(query)
                logger.info(f"在统一用户表中创建 markedit 用户成功, ID: {user_id}")
                
                # 为 markedit 用户分配 super_admin 角色
                await self._assign_superadmin_role_to_markedit(user_id)
            else:
                logger.info("markedit 用户已在统一用户表中存在")
                # 检查是否已有 super_admin 角色
                await self._ensure_markedit_superadmin_role(existing_user["id"])
            
            # 继续检查和创建旧系统管理员表中的记录（向后兼容）
            await self._ensure_markedit_admin_record()
                
        except Exception as e:
            logger.error(f"初始化默认超级管理员用户时出错: {str(e)}")
            raise
    
    async def _assign_superadmin_role_to_markedit(self, user_id: int):
        """为 markedit 用户分配 super_admin 角色"""
        try:
            # 获取 super_admin 角色 ID
            query = role_table.select().where(role_table.c.name == "super_admin")
            super_admin_role = await database.fetch_one(query)
            
            if not super_admin_role:
                logger.error("super_admin 角色不存在，无法为 markedit 用户分配")
                return
                
            role_id = super_admin_role["id"]
            
            # 检查是否已有角色分配
            query = user_role_table.select().where(
                (user_role_table.c.user_id == user_id) &
                (user_role_table.c.role_id == role_id)
            )
            existing_role = await database.fetch_one(query)
            
            if not existing_role:
                # 分配 super_admin 角色
                query = user_role_table.insert().values(
                    user_id=user_id,
                    role_id=role_id
                )
                await database.execute(query)
                logger.info(f"为 markedit 用户分配 super_admin 角色成功")
            else:
                logger.info("markedit 用户已有 super_admin 角色")
                
        except Exception as e:
            logger.error(f"为 markedit 用户分配 super_admin 角色时出错: {str(e)}")
            raise
    
    async def _ensure_markedit_superadmin_role(self, user_id: int):
        """确保 markedit 用户拥有 super_admin 角色"""
        try:
            # 获取 super_admin 角色 ID
            query = role_table.select().where(role_table.c.name == "super_admin")
            super_admin_role = await database.fetch_one(query)
            
            if not super_admin_role:
                logger.error("super_admin 角色不存在")
                return
                
            role_id = super_admin_role["id"]
            
            # 检查是否已有角色分配
            query = user_role_table.select().where(
                (user_role_table.c.user_id == user_id) &
                (user_role_table.c.role_id == role_id)
            )
            existing_role = await database.fetch_one(query)
            
            if not existing_role:
                # 分配 super_admin 角色
                query = user_role_table.insert().values(
                    user_id=user_id,
                    role_id=role_id
                )
                await database.execute(query)
                logger.info(f"为已存在的 markedit 用户分配 super_admin 角色成功")
            else:
                logger.info("markedit 用户已有 super_admin 角色")
                
        except Exception as e:
            logger.error(f"确保 markedit 用户 super_admin 角色时出错: {str(e)}")
            raise
    
    async def _ensure_markedit_admin_record(self):
        """确保旧系统管理员表中存在markedit记录"""
        query = admin_table.select().where(admin_table.c.username == "markedit")
        existing_admin = await database.fetch_one(query)
        
        if not existing_admin:
            # 生成随机密码
            password = generate_random_password()
            
            # 对密码进行哈希处理
            hashed_password = hash_password(password)
            
            # 在 admin_table 中创建记录（向后兼容）
            query = admin_table.insert().values(
                username="markedit",
                password=hashed_password
            )
            await database.execute(query)
            logger.info(f"创建旧系统管理员记录成功，用户名: markedit，密码: {password}")
        else:
            logger.info("旧系统管理员记录已存在")