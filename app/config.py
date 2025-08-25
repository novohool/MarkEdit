import os

# GitHub OAuth 配置
GITHUB_CLIENT_ID = os.getenv('GITHUB_APP_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_APP_CLIENT_SECRET', '')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_APP_REDIRECT_URI', '')



# 数据库连接池配置
DB_POOL_MIN_SIZE = int(os.getenv('DB_POOL_MIN_SIZE', '5'))
DB_POOL_MAX_SIZE = int(os.getenv('DB_POOL_MAX_SIZE', '20'))

# 是否在启动时创建数据库和表
CREATE_DB_ON_STARTUP = os.getenv('CREATE_DB_ON_STARTUP', 'true').lower() == 'true'

# 数据库配置字典
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', '10.238.235.84'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '123456'),
    'database': os.getenv('DB_NAME', 'markedit')
}