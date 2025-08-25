"""
Database configuration and connection management for MarkEdit application.
"""
from databases import Database
from sqlalchemy import MetaData
from app.config import DATABASE_CONFIG

# 数据库配置
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
database = Database(DATABASE_URL)
metadata = MetaData()







