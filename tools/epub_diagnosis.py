#!/usr/bin/env python3
"""
EPUB转换诊断工具

用于检查EPUB转换功能所需的所有依赖项和环境配置。
"""
import sys
import subprocess
import importlib
import logging
from pathlib import Path

def check_python_dependencies():
    """检查Python依赖库"""
    print("=== 检查Python依赖库 ===")
    
    required_packages = [
        'fastapi',
        'uvicorn', 
        'zipfile',  # 内置模块
        'xml.etree.ElementTree',  # 内置模块
        'json',  # 内置模块
        'pathlib',  # 内置模块
        'tempfile',  # 内置模块
        'shutil',  # 内置模块
    ]
    
    optional_packages = [
        'beautifulsoup4',
        'lxml'
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            if '.' in package:
                # 处理子模块
                main_module = package.split('.')[0]
                importlib.import_module(main_module)
            else:
                importlib.import_module(package)
            print(f"✓ {package} - 已安装")
        except ImportError:
            print(f"✗ {package} - 缺失")
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package} - 已安装 (可选)")
        except ImportError:
            print(f"- {package} - 未安装 (可选，建议安装)")
            missing_optional.append(package)
    
    return missing_required, missing_optional

def check_pandoc():
    """检查Pandoc安装状态"""
    print("\n=== 检查Pandoc安装 ===")
    
    try:
        # 检查pandoc命令是否可用
        result = subprocess.run(['pandoc', '--version'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            version_info = result.stdout.split('\n')[0]
            print(f"✓ Pandoc已安装: {version_info}")
            
            # 检查支持的格式
            formats_result = subprocess.run(['pandoc', '--list-input-formats'], 
                                          capture_output=True, text=True, timeout=10)
            if 'html' in formats_result.stdout:
                print("✓ Pandoc支持HTML输入格式")
            else:
                print("✗ Pandoc不支持HTML输入格式")
                
            formats_result = subprocess.run(['pandoc', '--list-output-formats'], 
                                          capture_output=True, text=True, timeout=10)
            if 'markdown' in formats_result.stdout:
                print("✓ Pandoc支持Markdown输出格式")
            else:
                print("✗ Pandoc不支持Markdown输出格式")
                
            return True
        else:
            print(f"✗ Pandoc命令执行失败: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("✗ Pandoc未安装或不在系统PATH中")
        print("\n安装Pandoc的方法:")
        print("1. 访问 https://pandoc.org/installing.html")
        print("2. Windows用户可以使用:")
        print("   - 下载MSI安装包")
        print("   - 或使用 winget install pandoc")
        print("   - 或使用 choco install pandoc")
        print("3. 安装后重启应用程序")
        return False
        
    except subprocess.TimeoutExpired:
        print("✗ Pandoc命令执行超时")
        return False
        
    except Exception as e:
        print(f"✗ 检查Pandoc时发生错误: {str(e)}")
        return False

def check_file_system():
    """检查文件系统权限和空间"""
    print("\n=== 检查文件系统 ===")
    
    project_root = Path(__file__).resolve().parent.parent
    
    # 检查项目目录
    print(f"项目根目录: {project_root}")
    if project_root.exists():
        print("✓ 项目根目录存在")
    else:
        print("✗ 项目根目录不存在")
        return False
    
    # 检查src目录
    src_dir = project_root / "src"
    if src_dir.exists():
        print("✓ src目录存在")
    else:
        print("- src目录不存在，将在需要时创建")
    
    # 检查users目录
    users_dir = project_root / "users"
    if users_dir.exists():
        print("✓ users目录存在")
    else:
        print("- users目录不存在，将在需要时创建")
    
    # 检查写入权限
    try:
        test_file = project_root / "test_write_permission.tmp"
        test_file.write_text("test", encoding='utf-8')
        test_file.unlink()
        print("✓ 项目目录写入权限正常")
    except Exception as e:
        print(f"✗ 项目目录写入权限异常: {str(e)}")
        return False
    
    # 检查磁盘空间
    try:
        import shutil
        total, used, free = shutil.disk_usage(project_root)
        free_gb = free // (1024**3)
        print(f"✓ 可用磁盘空间: {free_gb} GB")
        if free_gb < 1:
            print("⚠ 警告: 可用磁盘空间不足1GB")
    except Exception as e:
        print(f"- 无法检查磁盘空间: {str(e)}")
    
    return True

def test_epub_conversion():
    """测试EPUB转换功能"""
    print("\n=== 测试EPUB转换功能 ===")
    
    try:
        # 创建测试HTML文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>测试文档</title>
</head>
<body>
    <h1>测试标题</h1>
    <p>这是一个测试段落。</p>
</body>
</html>""")
            html_file = f.name
        
        # 创建输出文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            md_file = f.name
        
        # 测试pandoc转换
        cmd = ['pandoc', html_file, '-f', 'html', '-t', 'markdown', '-o', md_file, '--wrap=none']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # 检查输出文件
            output_path = Path(md_file)
            if output_path.exists() and output_path.stat().st_size > 0:
                content = output_path.read_text(encoding='utf-8')
                if '测试标题' in content and '测试段落' in content:
                    print("✓ EPUB转换功能正常")
                    success = True
                else:
                    print("✗ EPUB转换输出内容异常")
                    print(f"输出内容: {content}")
                    success = False
            else:
                print("✗ EPUB转换未产生输出文件")
                success = False
        else:
            print(f"✗ EPUB转换失败: {result.stderr}")
            success = False
        
        # 清理临时文件
        try:
            Path(html_file).unlink()
            Path(md_file).unlink()
        except:
            pass
            
        return success
        
    except Exception as e:
        print(f"✗ 测试EPUB转换时发生错误: {str(e)}")
        return False

def main():
    """主函数"""
    print("MarkEdit EPUB转换功能诊断工具")
    print("=" * 50)
    
    # 检查Python依赖
    missing_required, missing_optional = check_python_dependencies()
    
    # 检查Pandoc
    pandoc_ok = check_pandoc()
    
    # 检查文件系统
    filesystem_ok = check_file_system()
    
    # 测试转换功能
    if pandoc_ok:
        conversion_ok = test_epub_conversion()
    else:
        conversion_ok = False
    
    # 总结
    print("\n=== 诊断总结 ===")
    
    if missing_required:
        print(f"✗ 缺少必需的Python依赖: {', '.join(missing_required)}")
        print("  解决方法: pip install -r requirements.txt")
    
    if missing_optional:
        print(f"⚠ 缺少可选的Python依赖: {', '.join(missing_optional)}")
        print("  建议安装: pip install beautifulsoup4 lxml")
    
    if not pandoc_ok:
        print("✗ Pandoc未正确安装")
        print("  解决方法: 从 https://pandoc.org/installing.html 安装Pandoc")
    
    if not filesystem_ok:
        print("✗ 文件系统权限或配置异常")
    
    if not conversion_ok:
        print("✗ EPUB转换功能测试失败")
    
    if not missing_required and pandoc_ok and filesystem_ok and conversion_ok:
        print("✓ 所有检查通过，EPUB转换功能应该可以正常工作")
        return 0
    else:
        print("✗ 存在问题，请根据上述建议解决后重试")
        return 1

if __name__ == "__main__":
    sys.exit(main())