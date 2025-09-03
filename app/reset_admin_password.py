#!/usr/bin/env python3
"""
管理员密码重置工具

使用此工具可以重置管理员密码。
工具会自动检测正确的管理员账户或允许指定用户名。
运行后会生成一个新的强密码并更新数据库。

用法：
    python app/reset_admin_password.py                    # 自动检测管理员账户
    python app/reset_admin_password.py -u markedit       # 重置指定用户
    python app/reset_admin_password.py -y                # 跳过确认提示
    python app/reset_admin_password.py -u markedit -y    # 重置指定用户并跳过确认
    python app/reset_admin_password.py -l                # 列出所有管理员用户
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


async def list_admin_users():
    """列出所有管理员用户"""
    try:
        print("=" * 60)
        print("MarkEdit 管理员用户列表")
        print("=" * 60)
        print()
        
        # 连接数据库
        print("正在连接数据库...")
        await database.connect()
        print("数据库连接成功")
        print()
        
        # 获取所有管理员用户
        from app.common import admin_table
        query = admin_table.select()
        admin_users = await database.fetch_all(query)
        
        if admin_users:
            print(f"找到 {len(admin_users)} 个管理员用户:")
            print("-" * 50)
            
            for user in admin_users:
                username = user['username']
                display_name = username if username != "super_admin_markedit" else "markedit (系统用户名: super_admin_markedit)"
                print(f"ID: {user['id']}")
                print(f"用户名: {display_name}")
                print(f"密码哈希: {user['password'][:20]}...")
                print("-" * 50)
        else:
            print("❌ 未找到任何管理员用户")
            print("建议运行密码重置工具创建默认管理员账户")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取用户列表失败: {str(e)}")
        logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return False
    
    finally:
        # 断开数据库连接
        await database.disconnect()
        print("数据库连接已关闭")


async def reset_admin_password(specified_username=None):
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
        
        # 决定要重置的用户
        if specified_username:
            target_username = specified_username
            display_username = specified_username if specified_username != "super_admin_markedit" else "markedit"
            print(f"使用指定的用户名: {target_username}")
        else:
            # 检查哪个管理员用户存在
            from app.common import admin_table
            
            # 检查 super_admin_markedit 是否存在
            query = admin_table.select().where(admin_table.c.username == "super_admin_markedit")
            super_admin_user = await database.fetch_one(query)
            
            # 检查 markedit 是否存在
            query = admin_table.select().where(admin_table.c.username == "markedit")
            markedit_user = await database.fetch_one(query)
            
            # 决定重置哪个用户
            if super_admin_user:
                target_username = "super_admin_markedit"
                display_username = "markedit"
                print("找到系统管理员用户: super_admin_markedit")
            elif markedit_user:
                target_username = "markedit"
                display_username = "markedit"
                print("找到管理员用户: markedit")
            else:
                # 如果都不存在，创建 super_admin_markedit
                target_username = "super_admin_markedit"
                display_username = "markedit"
                print("未找到管理员用户，将创建: super_admin_markedit")
        
        # 执行密码重置
        print(f"正在重置管理员密码 ({target_username})...")
        result = await admin_service.reset_admin_password(target_username)
        
        if result.get("status") == "success":
            print("✅ 密码重置成功！")
            print()
            print("新的管理员登录信息：")
            print(f"登录用户名: {display_username}")
            print(f"系统用户名: {result.get('username')}")
            print(f"新密码: {result.get('new_password')}")
            print()
            print("⚠️  重要提示:")
            print("1. 请立即复制并保存新密码")
            print("2. 使用登录用户名和新密码登录管理员界面")
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
        
        # 检查命令行参数
        import argparse
        parser = argparse.ArgumentParser(description='重置管理员密码')
        parser.add_argument('--username', '-u', help='指定要重置的用户名 (默认自动检测)')
        parser.add_argument('--yes', '-y', action='store_true', help='跳过确认提示')
        parser.add_argument('--list', '-l', action='store_true', help='列出所有管理员用户')
        args = parser.parse_args()
        
        # 如果只是列出用户，执行列表功能
        if args.list:
            success = asyncio.run(list_admin_users())
            sys.exit(0 if success else 1)
        
        # 确认操作
        if not args.yes:
            print("此工具将重置默认超级管理员的密码")
            print("原密码将被覆盖且无法恢复")
            if args.username:
                print(f"指定重置用户: {args.username}")
            else:
                print("工具会自动检测并重置正确的管理员账户")
            print()
            
            confirm = input("确定要继续吗？(y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("操作已取消")
                sys.exit(0)
            
            print()
        
        # 执行密码重置
        success = asyncio.run(reset_admin_password(args.username))
        
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