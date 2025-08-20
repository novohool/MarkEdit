# 共享模块，用于存储全局变量和提供共享功能

# 全局变量存储启动备份文件名
startup_backup_filename = None

def set_startup_backup_filename(filename):
    """设置启动备份文件名"""
    global startup_backup_filename
    startup_backup_filename = filename

def get_startup_backup_filename():
    """获取启动备份文件名"""
    return startup_backup_filename