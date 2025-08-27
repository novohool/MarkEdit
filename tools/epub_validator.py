#!/usr/bin/env python3
"""
EPUB文件验证工具

此脚本用于验证EPUB文件的基本结构和完整性，
帮助诊断可能的文件格式问题。

用法:
    python epub_validator.py <epub文件路径>
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def validate_epub_file(epub_path):
    """验证EPUB文件的基本结构"""
    epub_file = Path(epub_path)
    
    print(f"验证EPUB文件: {epub_file.name}")
    print(f"文件路径: {epub_file.absolute()}")
    print(f"文件大小: {epub_file.stat().st_size:,} 字节")
    print("-" * 50)
    
    # 检查文件是否存在
    if not epub_file.exists():
        print("❌ 错误: 文件不存在")
        return False
    
    # 检查文件扩展名
    if epub_file.suffix.lower() != '.epub':
        print("⚠️ 警告: 文件扩展名不是.epub")
    
    try:
        # 尝试作为ZIP文件打开
        with zipfile.ZipFile(epub_file, 'r') as zip_file:
            print("✅ ZIP文件格式: 有效")
            
            # 获取文件列表
            file_list = zip_file.namelist()
            print(f"✅ 包含文件数量: {len(file_list)}")
            
            if len(file_list) == 0:
                print("❌ 错误: EPUB文件为空")
                return False
            
            # 检查ZIP文件完整性
            bad_file = zip_file.testzip()
            if bad_file:
                print(f"❌ 错误: ZIP文件包含损坏的文件: {bad_file}")
                return False
            print("✅ ZIP文件完整性: 通过")
            
            # 检查必需的EPUB结构
            has_mimetype = 'mimetype' in file_list
            has_meta_inf = any('META-INF/' in f for f in file_list)
            has_container_xml = 'META-INF/container.xml' in file_list
            
            print(f"{'✅' if has_mimetype else '❌'} mimetype文件: {'存在' if has_mimetype else '缺失'}")
            print(f"{'✅' if has_meta_inf else '❌'} META-INF目录: {'存在' if has_meta_inf else '缺失'}")
            print(f"{'✅' if has_container_xml else '❌'} container.xml: {'存在' if has_container_xml else '缺失'}")
            
            # 检查mimetype内容
            if has_mimetype:
                try:
                    mimetype_content = zip_file.read('mimetype').decode('utf-8').strip()
                    if mimetype_content == 'application/epub+zip':
                        print("✅ mimetype内容: 正确")
                    else:
                        print(f"⚠️ mimetype内容: 不正确 ('{mimetype_content}')")
                except Exception as e:
                    print(f"⚠️ mimetype读取错误: {e}")
            
            # 查找OPF文件
            opf_files = [f for f in file_list if f.endswith('.opf')]
            content_opf_files = [f for f in file_list if f.endswith('content.opf')]
            
            print(f"{'✅' if opf_files else '❌'} OPF文件: {len(opf_files)}个 {'(找到)' if opf_files else '(未找到)'}")
            if opf_files:
                print(f"   OPF文件列表: {', '.join(opf_files)}")
            
            # 尝试解析OPF文件
            if content_opf_files:
                try:
                    opf_content = zip_file.read(content_opf_files[0])
                    root = ET.fromstring(opf_content)
                    
                    # 检查基本的OPF结构
                    manifest = root.find('.//{http://www.idpf.org/2007/opf}manifest')
                    spine = root.find('.//{http://www.idpf.org/2007/opf}spine')
                    metadata = root.find('.//{http://www.idpf.org/2007/opf}metadata')
                    
                    print(f"✅ OPF结构分析:")
                    print(f"   - Manifest项目: {len(manifest) if manifest is not None else 0}")
                    print(f"   - Spine项目: {len(spine) if spine is not None else 0}")
                    print(f"   - Metadata: {'存在' if metadata is not None else '缺失'}")
                    
                    # 检查是否有HTML/XHTML文件
                    if manifest is not None:
                        html_items = [item for item in manifest if 'html' in item.get('media-type', '').lower()]
                        print(f"   - HTML/XHTML文件: {len(html_items)}个")
                        
                        # 检查图片文件
                        image_items = [item for item in manifest if 'image' in item.get('media-type', '').lower()]
                        print(f"   - 图片文件: {len(image_items)}个")
                    
                except ET.ParseError as e:
                    print(f"❌ OPF文件解析错误: {e}")
                except Exception as e:
                    print(f"⚠️ OPF文件分析警告: {e}")
            
            # 检查常见文件类型
            html_files = [f for f in file_list if any(f.lower().endswith(ext) for ext in ['.html', '.xhtml', '.htm'])]
            css_files = [f for f in file_list if f.lower().endswith('.css')]
            image_files = [f for f in file_list if any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg'])]
            
            print(f"\n📊 文件统计:")
            print(f"   - HTML/XHTML文件: {len(html_files)}")
            print(f"   - CSS样式文件: {len(css_files)}")
            print(f"   - 图片文件: {len(image_files)}")
            
            # 最终评估
            critical_errors = not has_mimetype or not has_meta_inf or not opf_files
            if critical_errors:
                print(f"\n❌ 验证结果: EPUB文件有严重结构问题，可能无法正常处理")
                return False
            else:
                print(f"\n✅ 验证结果: EPUB文件结构基本正确，应该可以正常处理")
                return True
            
    except zipfile.BadZipFile:
        print("❌ 错误: 文件不是有效的ZIP格式")
        return False
    except Exception as e:
        print(f"❌ 验证过程中出现错误: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python epub_validator.py <epub文件路径>")
        print("例如: python epub_validator.py my_book.epub")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    success = validate_epub_file(epub_path)
    
    print("\n" + "=" * 50)
    if success:
        print("✅ EPUB文件验证通过！")
        print("💡 建议: 此文件应该可以成功上传并转换")
    else:
        print("❌ EPUB文件验证失败！")
        print("💡 建议: 请检查文件是否完整，或尝试使用其他EPUB文件")
        print("💡 常见解决方案:")
        print("   1. 重新下载EPUB文件，确保下载完整")
        print("   2. 使用EPUB编辑器修复文件结构")
        print("   3. 转换文件格式为标准EPUB 2.0或3.0")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()