import os
import zipfile
import xml.etree.ElementTree as ET
import json
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
    ncx_href = None  # 用于存储NCX文件的href
    manifest_element = root.find('opf:manifest', namespaces)
    if manifest_element is not None:
        for item in manifest_element.findall('opf:item', namespaces):
            item_id = item.get('id')
            href = item.get('href')
            media_type = item.get('media-type')
            properties = item.get('properties')
            
            # 检查是否为NCX文件
            if media_type == 'application/x-dtbncx+xml':
                ncx_href = href
            
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
            
        # 提取封面信息
        cover_meta = metadata_element.find(".//opf:meta[@name='cover']", namespaces)
        if cover_meta is not None:
            metadata['cover'] = cover_meta.get('content')
    
    # 提取guide中的封面引用
    guide_element = root.find('opf:guide', namespaces)
    if guide_element is not None:
        cover_reference = guide_element.find(".//opf:reference[@type='cover']", namespaces)
        if cover_reference is not None:
            metadata['cover_href'] = cover_reference.get('href')
    
    return {
        'manifest': manifest,
        'spine': spine,
        'metadata': metadata,
        'ncx_href': ncx_href
    }
    
def parse_ncx_file(ncx_path: Path) -> Dict:
    """
    解析EPUB的NCX文件，提取目录结构
    
    Args:
        ncx_path: NCX文件的路径
        
    Returns:
        包含目录结构信息的字典
    """
    # 注册NCX命名空间
    namespaces = {
        'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
    }
    
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    
    # 解析XML文件
    tree = ET.parse(ncx_path)
    root = tree.getroot()
    
    # 提取文档标题
    doc_title = ""
    doc_title_element = root.find('ncx:docTitle/ncx:text', namespaces)
    if doc_title_element is not None:
        doc_title = doc_title_element.text or ""
    
    # 提取导航地图
    nav_map = []
    nav_map_element = root.find('ncx:navMap', namespaces)
    if nav_map_element is not None:
        nav_map = _parse_nav_points(nav_map_element, namespaces)
    
    return {
        'title': doc_title,
        'nav_map': nav_map
    }

def _parse_nav_points(nav_point_element, namespaces: Dict, level: int = 0) -> List[Dict]:
    """
    递归解析导航点
    
    Args:
        nav_point_element: navPoint元素
        namespaces: 命名空间字典
        level: 当前层级
        
    Returns:
        导航点列表
    """
    nav_points = []
    
    # 查找所有navPoint子元素
    for nav_point in nav_point_element.findall('ncx:navPoint', namespaces):
        # 提取导航点信息
        nav_label_element = nav_point.find('ncx:navLabel/ncx:text', namespaces)
        nav_label = nav_label_element.text if nav_label_element is not None and nav_label_element.text else ""
        
        # 提取内容链接
        content_element = nav_point.find('ncx:content', namespaces)
        content_src = content_element.get('src') if content_element is not None else ""
        
        # 创建导航点对象
        nav_point_obj = {
            'label': nav_label,
            'content': content_src,
            'level': level
        }
        
        # 递归处理子导航点
        child_nav_points = nav_point.findall('ncx:navPoint', namespaces)
        if child_nav_points:
            nav_point_obj['children'] = _parse_nav_points(nav_point, namespaces, level + 1)
        
        nav_points.append(nav_point_obj)
    
    return nav_points

def _convert_nav_map_to_chapter_config(nav_map: List[Dict]) -> Dict:
    """
    将导航点映射转换为chapter-config.json格式
    
    Args:
        nav_map: 导航点列表
        
    Returns:
        chapter-config.json格式的字典
    """
    chapters = []
    counter = [0]  # 使用列表来保持计数器的引用
    
    def extract_chapters(nav_points, level=0):
        for nav_point in nav_points:
            # 提取内容链接中的文件名
            content = nav_point.get('content', '')
            # 提取导航点标签
            label = nav_point.get('label', '')
            
            if content and label:
                # 移除锚点部分，只保留文件名
                file_name = content.split('#')[0]
                # 移除目录结构，只保留文件名
                file_name = Path(file_name).name
                # 将.xhtml扩展名替换为.md
                if file_name.endswith('.xhtml'):
                    file_name = file_name[:-6] + '.md'
                elif file_name.endswith('.html'):
                    file_name = file_name[:-5] + '.md'
                
                # 生成章节标题，保留原始标签文本
                title = label
                
                # 生成文件名，基于章节标题
                # 移除非法字符并替换空格为连字符
                import re
                safe_label = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', label)
                safe_label = re.sub(r'\s+', '-', safe_label)
                # 限制文件名长度
                if len(safe_label) > 100:
                    safe_label = safe_label[:100]
                
                # 递增计数器并生成文件名，添加序号前缀
                counter[0] += 1
                file_name = f"{counter[0]:02d}-{safe_label}.md"
                
                # 添加章节信息
                chapters.append({
                    'file': file_name,
                    'title': title
                })
            
            # 递归处理子导航点
            if 'children' in nav_point:
                extract_chapters(nav_point['children'], level + 1)
    
    extract_chapters(nav_map)
    
    return {
        'chapters': chapters
    }

def _format_toc_structure(nav_map: List[Dict], indent: str = "") -> str:
    """
    格式化目录结构为字符串
    
    Args:
        nav_map: 导航点列表
        indent: 缩进字符串
        
    Returns:
        格式化后的目录结构字符串
    """
    result = ""
    for nav_point in nav_map:
        label = nav_point.get('label', '')
        content = nav_point.get('content', '')
        level = nav_point.get('level', 0)
        
        # 添加缩进和标签
        result += f"{indent}{label}"
        if content:
            result += f" ({content})"
        result += "\n"
        
        # 递归处理子导航点
        if 'children' in nav_point:
            result += _format_toc_structure(nav_point['children'], indent + "  ")
    
    return result


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
    ncx_href = epub_data.get('ncx_href')
    
    # 如果存在NCX文件，则解析它以获取目录结构
    toc_structure = None
    if ncx_href:
        ncx_path = epub_root_path / ncx_href
        if ncx_path.exists():
            try:
                toc_structure = parse_ncx_file(ncx_path)
                logger.info(f"已解析NCX目录文件: {ncx_href}")
            except Exception as e:
                logger.warning(f"解析NCX文件失败: {e}")
    
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
     
        # 如果解析了目录结构，将其也添加到ZIP文件中
        if toc_structure:
            # 创建一个包含目录结构信息的文本文件
            toc_info = f"EPUB目录结构信息\n"
            toc_info += f"标题: {toc_structure.get('title', 'N/A')}\n"
            toc_info += f"目录项数量: {len(toc_structure.get('nav_map', []))}\n\n"
            toc_info += "目录结构:\n"
            toc_info += _format_toc_structure(toc_structure.get('nav_map', []))
            
            # 将目录信息添加到ZIP文件
            zipf.writestr("toc_info.txt", toc_info)
            logger.info("已添加目录结构信息到ZIP文件")
            
            # 将目录结构转换为chapter-config.json格式并添加到ZIP文件中
            chapter_config = _convert_nav_map_to_chapter_config(toc_structure.get('nav_map', []))
            chapter_config_json = json.dumps(chapter_config, ensure_ascii=False, indent=2)
            zipf.writestr("chapter-config.json", chapter_config_json)
            logger.info("已添加chapter-config.json到ZIP文件")
            
            # 同时在EPUB根目录下生成chapter-config.json文件
            chapter_config_path = epub_root_path.parent / 'chapter-config.json'
            with open(chapter_config_path, 'w', encoding='utf-8') as f:
                f.write(chapter_config_json)
            logger.info(f"已生成chapter-config.json文件: {chapter_config_path}")

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