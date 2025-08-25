"""
Utils package for MarkEdit application.

This package contains all utility functions and helper classes.
"""
from .file_utils import (
    TEXT_FILE_EXTENSIONS,
    IMAGE_FILE_EXTENSIONS,
    PREVIEWABLE_BINARY_EXTENSIONS,
    is_text_file,
    is_image_file,
    is_previewable_binary,
    scan_directory,
    read_text_file,
    read_image_file,
    save_text_file,
    delete_file_safely,
    create_file_safely,
    create_directory_safely
)
from .response_utils import (
    create_file_response,
    create_static_file_response
)
from .crypto_utils import (
    pwd_context,
    hash_password,
    verify_password,
    generate_random_password,
    generate_session_id
)
from .validation_utils import (
    validate_json_string,
    validate_json_and_parse,
    validate_theme_name,
    validate_password_strength,
    sanitize_file_path
)
from .permission_utils import (
    PermissionError,
    require_permissions,
    require_any_permission,
    check_user_has_permission,
    check_user_has_role,
    get_user_permission_summary,
    validate_permission_name,
    validate_role_name,
    PermissionConstants,
    RoleConstants
)
from .system_utils import (
    SystemMonitor,
    format_bytes,
    format_duration,
    get_quick_stats
)
from .auth_decorators import (
    get_session,
    require_auth_session,
    require_permission,
    require_role,
    require_admin,
    require_super_admin,
    optional_auth
)
from .directory_utils import (
    DirectoryManager,
    directory_manager
)
from .global_state import (
    GlobalStateManager,
    global_state_manager,
    set_startup_backup_filename,
    get_startup_backup_filename,
    set_config_value,
    get_config_value
)

__all__ = [
    # File utils
    'TEXT_FILE_EXTENSIONS',
    'IMAGE_FILE_EXTENSIONS', 
    'PREVIEWABLE_BINARY_EXTENSIONS',
    'is_text_file',
    'is_image_file',
    'is_previewable_binary',
    'scan_directory',
    'read_text_file',
    'read_image_file',
    'save_text_file',
    'delete_file_safely',
    'create_file_safely',
    'create_directory_safely',
    # Response utils
    'create_file_response',
    'create_static_file_response',
    # Crypto utils
    'pwd_context',
    'hash_password',
    'verify_password',
    'generate_random_password',
    'generate_session_id',
    # Validation utils
    'validate_json_string',
    'validate_json_and_parse',
    'validate_theme_name',
    'validate_password_strength',
    'sanitize_file_path',
    # Permission utils
    'PermissionError',
    'require_permissions',
    'require_any_permission',
    'check_user_has_permission',
    'check_user_has_role',
    'get_user_permission_summary',
    'validate_permission_name',
    'validate_role_name',
    'PermissionConstants',
    'RoleConstants',
    # System utils
    'SystemMonitor',
    'format_bytes',
    'format_duration',
    'get_quick_stats',
    # Auth decorators
    'get_session',
    'require_auth_session',
    'require_permission',
    'require_role',
    'require_admin',
    'require_super_admin',
    'optional_auth',
    # Directory utils
    'DirectoryManager',
    'directory_manager',
    # Global state
    'GlobalStateManager',
    'global_state_manager',
    'set_startup_backup_filename',
    'get_startup_backup_filename',
    'set_config_value',
    'get_config_value'
]