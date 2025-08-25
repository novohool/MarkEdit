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