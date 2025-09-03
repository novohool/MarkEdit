"""
Validation utilities for MarkEdit application.

This module provides unified validation functionality using the base_utils infrastructure.
"""
from typing import Any, Dict, List
from .base_utils import JSONUtils, ValidationUtils

# 直接使用base_utils中的统一实现
validate_json_string = JSONUtils.validate_json_string
validate_json_and_parse = JSONUtils.parse_json_string
validate_theme_name = ValidationUtils.validate_theme_name
sanitize_file_path = ValidationUtils.sanitize_file_path

# 使用增强的密码验证（支持更多配置）
def validate_password_strength(password: str, strict: bool = False) -> bool:
    """验证密码强度（兼容原接口）"""
    if strict:
        # 严格模式：要求特殊字符
        result = ValidationUtils.validate_password_strength(
            password, 
            min_length=8,
            require_special=True
        )
    else:
        # 标准模式：不要求特殊字符
        result = ValidationUtils.validate_password_strength(password, require_special=False)
    
    return result["valid"]

# 新增的增强功能
def validate_password_detailed(password: str) -> Dict[str, Any]:
    """获取详细的密码验证结果"""
    return ValidationUtils.validate_password_strength(password)

def validate_file_path_secure(path: str, allowed_extensions: List[str] = None) -> bool:
    """安全的文件路径验证"""
    return ValidationUtils.validate_file_path(path, allowed_extensions)