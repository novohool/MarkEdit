import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List
import logging

# 创建logger
logger = logging.getLogger(__name__)

def parse_content_opf(content_opf_path: Path) -> Dict:
    """
    解析EPUB的content.opf文件，提取文件清单和元数据
    
    Args:
        content_opf_path: content.opf文件的路径
        
    Returns:
        包含manifest, spine和其他元数据的字典
    """
    # 注册命名空间以保持XML格式
    namespaces = {
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    
    # 解析XML文件
    tree = ET.parse(content_opf_path)
    root = tree.getroot()
    
    # 提取manifest信息
    manifest = {}
    manifest_element = root.find('opf:manifest', namespaces)
    if manifest_element is not None:
        for item in manifest_element.findall('opf:item', namespaces):
            item_id = item.get('id')
            href = item.get('href')
            media_type = item.get('media-type')
            properties = item.get('properties')
            
            manifest[item_id] = {
                'href': href,
                'media_type': media_type,
                'properties': properties
            }
    
    # 提取spine信息（阅读顺序）
    spine = []
    spine_element = root.find('opf:spine', namespaces)
    if spine_element is not None:
        for itemref in spine_element.findall('opf:itemref', namespaces):
            idref = itemref.get('idref')
            linear = itemref.get('linear', 'yes')  # 默认为yes
            spine.append({
                'idref': idref,
                'linear': linear
            })
    
    # 提取metadata信息
    metadata = {}
    metadata_element = root.find('opf:metadata', namespaces)
    if metadata_element is not None:
        # 提取标题
        title_element = metadata_element.find('dc:title', namespaces)
        if title_element is not None:
            metadata['title'] = title_element.text
        
        # 提取作者
        creator_element = metadata_element.find('dc:creator', namespaces)
        if creator_element is not None:
            metadata['creator'] = creator_element.text
            
        # 提取语言
        language_element = metadata_element.find('dc:language', namespaces)
        if language_element is not None:
            metadata['language'] = language_element.text
    
    return {
        'manifest': manifest,
        'spine': spine,
        'metadata': metadata
    }

def convert_epub_to_zip(epub_root_path: Path, output_zip_path: Path):
    """
    将EPUB目录结构转换为ZIP文件，严格遵循content.opf定义
    
    Args:
        epub_root_path: EPUB根目录路径（包含content.opf文件的目录）
        output_zip_path: 输出ZIP文件路径
    """
    # 确保输出目录存在
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 解析content.opf文件
    content_opf_path = epub_root_path / 'content.opf'
    if not content_opf_path.exists():
        raise FileNotFoundError(f"content.opf文件不存在: {content_opf_path}")
    
    epub_data = parse_content_opf(content_opf_path)
    manifest = epub_data['manifest']
    
    # 创建ZIP文件
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 遍历manifest中的所有文件
        for item_id, item_info in manifest.items():
            href = item_info['href']
            source_path = epub_root_path / href
            
            # 检查文件是否存在
            if not source_path.exists():
                logger.warning(f"文件不存在，跳过: {source_path}")
                continue
            
            # 处理文件路径，特别处理图片路径
            if item_info['media_type'] and item_info['media_type'].startswith('image/'):
                # 将图片文件统一放到illustrations/目录下
                filename = Path(href).name
                target_path = Path('illustrations') / filename
            else:
                target_path = Path(href)
            
            # 对于XHTML文件，需要处理其中的图片引用
            if item_info['media_type'] == 'application/xhtml+xml':
                # 读取XHTML文件内容
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 处理图片路径替换
                # 查找所有img标签的src属性
                import re
                def replace_img_src(match):
                    src = match.group(1)
                    # 解析原始图片路径
                    src_path = Path(src)
                    src_name = src_path.name
                    
                    # 查找manifest中是否有对应的图片文件
                    for manifest_item in manifest.values():
                        if (manifest_item['media_type'] and
                            manifest_item['media_type'].startswith('image/') and
                            Path(manifest_item['href']).name == src_name):
                            # 如果找到对应的图片文件，使用新的路径
                            return f'src="../illustrations/{src_name}"'
                    
                    # 如果没有找到对应的图片文件，保持原路径
                    return match.group(0)
                
                # 替换img标签的src属性
                content = re.sub(r'src="([^"]*)"', replace_img_src, content)
                
                # 处理其他可能的图片引用（如background-image等CSS属性）
                def replace_css_image(match):
                    url = match.group(1)
                    url_path = Path(url)
                    url_name = url_path.name
                    
                    # 查找manifest中是否有对应的图片文件
                    for manifest_item in manifest.values():
                        if (manifest_item['media_type'] and
                            manifest_item['media_type'].startswith('image/') and
                            Path(manifest_item['href']).name == url_name):
                            # 如果找到对应的图片文件，使用新的路径
                            return f'url(../illustrations/{url_name})'
                    
                    # 如果没有找到对应的图片文件，保持原路径
                    return match.group(0)
                
                # 替换CSS中的图片引用
                content = re.sub(r'url\(([^)]+)\)', replace_css_image, content)
                
                # 将修改后的内容写入ZIP
                zipf.writestr(str(target_path), content)
            else:
                # 直接复制其他文件
                zipf.write(source_path, target_path)
            
            logger.info(f"已添加文件到ZIP: {target_path}")

def convert_epub_dir_to_zip(epub_dir: Path, output_dir: Path = None) -> Path:
    """
    将EPUB目录转换为ZIP文件的便捷函数
    
    Args:
        epub_dir: EPUB目录路径（包含mimetype, META-INF, EPUB等子目录）
        output_dir: 输出目录路径，默认为EPUB目录同级的build目录
        
    Returns:
        生成的ZIP文件路径
    """
    # 默认输出目录为build目录
    if output_dir is None:
        output_dir = epub_dir.parent / 'build'
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # EPUB内容目录
    epub_root_path = epub_dir / 'EPUB'
    
    # 获取EPUB标题作为ZIP文件名
    content_opf_path = epub_root_path / 'content.opf'
    epub_data = parse_content_opf(content_opf_path)
    title = epub_data['metadata'].get('title', 'epub_book')
    
    # 清理文件名中的非法字符
    import re
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    
    # 生成输出ZIP文件路径
    output_zip_path = output_dir / f"{safe_title}.zip"
    
    # 执行转换
    convert_epub_to_zip(epub_root_path, output_zip_path)
    
    logger.info(f"EPUB到ZIP转换完成: {output_zip_path}")
    return output_zip_path

if __name__ == "__main__":
    # 示例用法
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python epub_to_zip.py <epub目录路径> [输出目录路径]")
        sys.exit(1)
    
    epub_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        zip_path = convert_epub_dir_to_zip(epub_dir, output_dir)
        print(f"转换成功: {zip_path}")
    except Exception as e:
        print(f"转换失败: {e}")
        sys.exit(1)