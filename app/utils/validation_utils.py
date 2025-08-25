"""
Validation utilities for MarkEdit application.
"""
import json
from typing import Any, Dict, Optional
from fastapi import HTTPException

def validate_json_string(json_str: str) -> bool:
    """验证JSON字符串格式"""
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def validate_json_and_parse(json_str: str) -> Dict[str, Any]:
    """验证并解析JSON字符串"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

def validate_theme_name(theme: str) -> bool:
    """验证主题名称"""
    # 主题名称应该只包含字母、数字、下划线和连字符
    return theme.replace('_', '').replace('-', '').isalnum()

def validate_password_strength(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()" for c in password)
    
    return has_upper and has_lower and has_digit and has_special

def sanitize_file_path(path: str) -> str:
    """清理文件路径，防止路径遍历攻击"""
    # 移除危险字符
    dangerous_chars = ['..', '~', '$', '&', '|', '>', '<', ';']
    cleaned_path = path
    for char in dangerous_chars:
        cleaned_path = cleaned_path.replace(char, '')
    
    # 移除开头的斜杠
    cleaned_path = cleaned_path.lstrip('/')
    
    return cleaned_path