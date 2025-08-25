"""
Cryptography and security utilities for MarkEdit application.
"""
import secrets
import string
from passlib.context import CryptContext

# 创建密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def generate_random_password(length: int = 16) -> str:
    """生成随机密码"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in password) and
            any(c.islower() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in "!@#$%^&*()" for c in password)):
            return password

def generate_session_id() -> str:
    """生成会话ID"""
    return secrets.token_urlsafe(32)