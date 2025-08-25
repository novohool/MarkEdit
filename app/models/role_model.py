"""
Role and permission related database models for MarkEdit application.
"""
from sqlalchemy import Table, Column, Integer, String, DateTime, Text, ForeignKey
import datetime
from .database import metadata

# 定义角色表
role_table = Table(
    "role",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, unique=True, index=True),  # 角色名称
    Column("description", Text),  # 角色描述
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
)

# 定义用户角色绑定表
user_role_table = Table(
    "user_role",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("role_id", Integer, ForeignKey("role.id")),
    Column("assigned_at", DateTime, default=datetime.datetime.utcnow),
)

# 定义权限表
permission_table = Table(
    "permission",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, unique=True, index=True),  # 权限名称
    Column("description", Text),  # 权限描述
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
)

# 定义角色权限绑定表
role_permission_table = Table(
    "role_permission",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("role_id", Integer, ForeignKey("role.id")),
    Column("permission_id", Integer, ForeignKey("permission.id")),
    Column("assigned_at", DateTime, default=datetime.datetime.utcnow),
)

# 定义审计日志表
audit_log_table = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", DateTime, default=datetime.datetime.utcnow, index=True),
    Column("operation", String(50), index=True),  # create, update, delete, assign, remove
    Column("operator", String(100), index=True),  # 操作者用户名
    Column("target_type", String(50), index=True),  # user, role, permission
    Column("target_id", Integer, index=True),  # 目标对象ID
    Column("target_name", String(100)),  # 目标对象名称
    Column("old_values", Text),  # 变更前的值（JSON格式）
    Column("new_values", Text),  # 变更后的值（JSON格式）
    Column("details", Text),  # 详细信息（JSON格式）
    Column("ip_address", String(45)),  # 操作者IP地址
    Column("user_agent", Text),  # 用户代理信息
)