#!/usr/bin/env python3
"""
管理员密码重置工具

使用此工具可以重置默认超级管理员(markedit)的密码。
运行后会生成一个新的强密码并更新数据库。

用法：
    python app/reset_admin_password.py
"""

import sys
import asyncio
import os
from pathlib import Path

# 添加app目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import database
from app.services.admin_service import AdminService
from app.common.services import get_admin_service
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reset_admin_password():
    """重置管理员密码"""
    try:
        print("=" * 60)
        print("MarkEdit 管理员密码重置工具")
        print("=" * 60)
        print()
        
        # 连接数据库
        print("正在连接数据库...")
        await database.connect()
        print("数据库连接成功")
        
        # 获取管理员服务
        admin_service = get_admin_service()
        
        # 执行密码重置
        print("正在重置默认管理员密码...")
        result = await admin_service.reset_admin_password()
        
        if result.get("status") == "success":
            print("✅ 密码重置成功！")
            print()
            print("新的管理员登录信息：")
            print(f"用户名: {result.get('username', 'markedit')}")
            print(f"新密码: {result.get('new_password')}")
            print()
            print("⚠️  重要提示:")
            print("1. 请立即复制并保存新密码")
            print("2. 使用新密码登录管理员界面")
            print("3. 登录后建议修改为自定义密码")
            print("4. 删除此工具的命令行历史记录")
            print()
            print("管理员界面地址: http://localhost:8080/admin/login")
        else:
            print("❌ 密码重置失败")
            if result.get("message"):
                print(f"错误信息: {result.get('message')}")
    
    except Exception as e:
        print(f"❌ 重置过程中发生错误: {str(e)}")
        logger.error(f"密码重置失败: {str(e)}", exc_info=True)
        return False
    
    finally:
        # 断开数据库连接
        await database.disconnect()
        print("数据库连接已关闭")
    
    return True


def main():
    """主函数"""
    try:
        # 检查是否在正确的目录
        if not Path("app/main.py").exists():
            print("❌ 错误: 请在 MarkEdit 项目根目录下运行此工具")
            print("正确用法: python app/reset_admin_password.py")
            sys.exit(1)
        
        # 确认操作
        print("此工具将重置默认超级管理员(markedit)的密码")
        print("原密码将被覆盖且无法恢复")
        print()
        
        confirm = input("确定要继续吗？(y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("操作已取消")
            sys.exit(0)
        
        print()
        
        # 执行密码重置
        success = asyncio.run(reset_admin_password())
        
        if success:
            print("=" * 60)
            print("密码重置完成")
            print("=" * 60)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()