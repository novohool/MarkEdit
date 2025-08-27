"""
User-related database models for MarkEdit application.
"""
from sqlalchemy import Table, Column, Integer, String, DateTime, Text, ForeignKey
import datetime
from .database import metadata

# 定义admin表（向后兼容）
admin_table = Table(
    "admin",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, index=True),
    Column("password", String),
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
)

# 定义user表（统一用户表）
user_table = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, index=True),
    Column("password", String),  # 新增密码字段，用于统一存储所有用户密码
    Column("user_type", String, default="user"),  # 用户类型: 'admin', 'user'
    Column("login_time", DateTime, default=datetime.datetime.utcnow),
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
    Column("theme", String, default="default"),
    Column("llm_config", String, default="{}"),  # 存储用户自定义LLM配置的JSON字符串
    Column("max_upload_size_mb", Integer, default=15),  # 最大上传文件大小（MB），默认15MB
    Column("max_build_books", Integer, default=10),  # build目录最大书籍数量，默认10本
)