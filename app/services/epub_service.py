"""
EPUB service for MarkEdit application.

This module contains business logic for EPUB operations including:
- EPUB parsing and analysis
- Content.opf file processing
- NCX file processing
- EPUB to ZIP conversion
- Chapter configuration generation
"""
import os
import zipfile
import xml.etree.ElementTree as ET
import json
import logging
import re
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EpubService:
    """EPUB服务类"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
    
    def parse_content_opf(self, content_opf_path: Path) -> Dict[str, Any]:
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
    
    def parse_ncx_file(self, ncx_path: Path) -> Dict[str, Any]:
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
            nav_map = self._parse_nav_points(nav_map_element, namespaces)
        
        return {
            'title': doc_title,
            'nav_map': nav_map
        }
    
    def _parse_nav_points(self, nav_point_element, namespaces: Dict[str, str], level: int = 0) -> List[Dict[str, Any]]:
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
                nav_point_obj['children'] = self._parse_nav_points(nav_point, namespaces, level + 1)
            
            nav_points.append(nav_point_obj)
        
        return nav_points
    
    def _process_images_with_cover_naming(self, all_images: List[Dict], illustrations_dir: Path) -> Dict[str, str]:
        """
        处理图片文件，包括封面命名和base64转换
        
        Args:
            all_images: 所有图片信息列表
            illustrations_dir: 插图目录路径
            
        Returns:
            原始路径到新文件名的映射字典
        """
        import shutil
        
        image_file_mappings = {}
        processed_files = []
        
        # 检测封面图片的逻辑：优先查找包含cover关键字的图片
        cover_index = -1
        backcover_index = -1
        
        # 查找明确的封面图片
        for i, img_info in enumerate(all_images):
            href_lower = img_info['href'].lower()
            if 'cover' in href_lower and 'back' not in href_lower:
                cover_index = i
            elif 'backcover' in href_lower or ('back' in href_lower and 'cover' in href_lower):
                backcover_index = i
        
        # 如果没有找到明确的封面，将第一张图片作为封面（但不强制重命名）
        for i, img_info in enumerate(all_images):
            img_source = img_info['source']
            original_name = Path(img_info['href']).name
            file_extension = Path(original_name).suffix.lower()
            original_href = img_info['href']
            
            # 确定目标文件名的策略
            if i == cover_index or (cover_index == -1 and i == 0 and len(all_images) > 1 and 'cover' not in original_name.lower()):
                # 如果是明确的封面，或者是第一张且没有cover关键字的图片
                if 'cover' in original_name.lower():
                    target_name = original_name  # 保持原名
                else:
                    target_name = f"cover{file_extension or '.jpg'}"
            elif i == backcover_index or (backcover_index == -1 and i == len(all_images) - 1 and len(all_images) > 2 and 'backcover' not in original_name.lower()):
                # 如果是明确的背面封面，或者是最后一张且没有backcover关键字
                if 'backcover' in original_name.lower() or ('back' in original_name.lower() and 'cover' in original_name.lower()):
                    target_name = original_name  # 保持原名
                else:
                    target_name = f"backcover{file_extension or '.jpg'}"
            else:
                # 其他图片保持原名
                target_name = original_name
            
            img_target = illustrations_dir / target_name
            
            try:
                shutil.copy2(img_source, img_target)
                processed_files.append(target_name)
                image_file_mappings[original_href] = target_name
                logger.info(f"复制图片文件: {original_href} -> {target_name}")
            except Exception as e:
                logger.warning(f"复制图片文件失败 {original_href}: {str(e)}")
                # 如果复制失败，仍然记录映射关系，使用原始文件名
                image_file_mappings[original_href] = original_name
        
        logger.info(f"图片处理完成，共处理 {len(processed_files)} 个文件: {processed_files}")
        return image_file_mappings
    
    def _extract_base64_images_from_content(self, content: str, illustrations_dir: Path) -> Dict[str, str]:
        """
        从内容中提取base64图片并保存为文件
        
        Args:
            content: HTML或Markdown内容
            illustrations_dir: 插图目录路径
            
        Returns:
            base64链接到文件名的映射
        """
        base64_to_file = {}
        
        # 查找base64图片，支持多种格式和换行情况
        base64_pattern = r'data:image/([^;,\s]+);base64,([A-Za-z0-9+/=\s\n\r]+)'
        matches = re.finditer(base64_pattern, content, re.MULTILINE | re.DOTALL)
        
        image_counter = 1
        existing_files = set()
        
        # 首先检查已存在的文件
        if illustrations_dir.exists():
            for existing_file in illustrations_dir.glob('*'):
                if existing_file.is_file():
                    existing_files.add(existing_file.name)
        
        for match in matches:
            image_format = match.group(1).strip().lower()
            base64_data = match.group(2).strip()
            # 清理base64数据，移除所有空白字符
            clean_base64 = re.sub(r'\s', '', base64_data)
            full_data_url = match.group(0)
            
            try:
                # 解码base64数据
                image_data = base64.b64decode(clean_base64)
                
                # 确定文件扩展名
                if image_format in ['svg+xml', 'svg']:
                    # SVG转换为PNG
                    file_extension = '.png'
                    image_data = self._convert_svg_to_png(image_data)
                elif image_format in ['jpeg', 'jpg']:
                    file_extension = '.jpg'
                elif image_format == 'png':
                    file_extension = '.png'
                elif image_format == 'gif':
                    file_extension = '.gif'
                elif image_format == 'webp':
                    file_extension = '.webp'
                else:
                    file_extension = '.png'  # 默认为PNG
                
                # 生成文件名，避免重复
                if image_counter == 1 and f'cover{file_extension}' not in existing_files:
                    filename = f"cover{file_extension}"
                    existing_files.add(filename)
                else:
                    filename = f"image_{image_counter:03d}{file_extension}"
                    while filename in existing_files:
                        image_counter += 1
                        filename = f"image_{image_counter:03d}{file_extension}"
                    existing_files.add(filename)
                
                # 保存文件
                file_path = illustrations_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
                # 记录多种映射关系，确保能够匹配各种格式的base64
                clean_data_url = f"data:image/{image_format};base64,{clean_base64}"
                base64_to_file[clean_data_url] = filename
                base64_to_file[full_data_url] = filename  # 保存原始版本
                
                # 也记录不带空格的版本
                compact_data_url = f"data:image/{image_format};base64,{base64_data.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')}"
                base64_to_file[compact_data_url] = filename
                
                logger.info(f"提取base64图片: {filename} (格式: {image_format}, 大小: {len(image_data)} bytes)")
                
                image_counter += 1
                
            except Exception as e:
                logger.warning(f"处理base64图片失败: {str(e)}")
                logger.debug(f"Base64数据前100字符: {clean_base64[:100]}...")
        
        logger.info(f"共提取 {len(base64_to_file)//3} 个base64图片")
        return base64_to_file
    
    def _convert_svg_to_png(self, svg_data: bytes) -> bytes:
        """
        将SVG数据转换为PNG
        
        Args:
            svg_data: SVG数据
            
        Returns:
            PNG数据
        """
        try:
            # 尝试使用cairosvg转换
            try:
                import cairosvg
                return cairosvg.svg2png(bytestring=svg_data)
            except ImportError:
                logger.warning("cairosvg未安装，无法转换SVG为PNG，保持原格式")
                return svg_data
        except Exception as e:
            logger.warning(f"SVG转换PNG失败: {str(e)}，保持原格式")
            return svg_data
    
    def _convert_image_links_in_markdown(self, markdown_content: str, base64_to_file: Dict[str, str], 
                                       image_file_mappings: Dict[str, str] = None) -> str:
        """
        转换Markdown中的图片链接
        
        Args:
            markdown_content: Markdown内容
            base64_to_file: base64到文件名的映射
            image_file_mappings: 原始图片路径到新文件名的映射
            
        Returns:
            转换后的Markdown内容
        """
        if image_file_mappings is None:
            image_file_mappings = {}
        
        logger.debug(f"开始转换图片链接，base64映射数量: {len(base64_to_file)}, 文件映射数量: {len(image_file_mappings)}")
        
        original_content = markdown_content
        replacement_count = 0
        
        # 替换base64图片链接 - 使用直接字符串替换而不是正则
        for base64_url, filename in base64_to_file.items():
            if base64_url in markdown_content:
                markdown_content = markdown_content.replace(base64_url, f"illustrations/{filename}")
                replacement_count += 1
                logger.debug(f"替换base64图片: {filename}")
        
        # 处理样式块中的图片引用
        def replace_style_block_image(match):
            style_content = match.group(1)
            image_part = match.group(2)
            modified = False
            
            # 在图片部分中替换base64链接
            for base64_url, filename in base64_to_file.items():
                if base64_url in image_part:
                    image_part = image_part.replace(base64_url, f"illustrations/{filename}")
                    modified = True
            
            # 替换普通图片链接
            for original_path, new_filename in image_file_mappings.items():
                if original_path in image_part:
                    image_part = image_part.replace(original_path, f"illustrations/{new_filename}")
                    modified = True
            
            return f":::{style_content}\n{image_part}\n:::"
        
        # 替换样式块中的图片
        style_block_pattern = r':::([^\n]*?)\n([^:]*?)\n:::'
        markdown_content = re.sub(style_block_pattern, replace_style_block_image, markdown_content, flags=re.MULTILINE | re.DOTALL)
        
        # 替换标准图片链接格式 ![alt](path)
        def replace_image_link(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # 如果已经是illustrations/格式，则不处理
            if image_path.startswith('illustrations/'):
                return match.group(0)
            
            # 如果是base64数据，应该已经在上面处理过了，但以防万一
            if image_path.startswith('data:image/'):
                # 查找对应的文件名
                for base64_url, filename in base64_to_file.items():
                    # 尝试匹配部分base64字符串
                    if base64_url == image_path or image_path in base64_url:
                        logger.debug(f"在图片链接中发现未处理的base64: {filename}")
                        return f"![{alt_text}](illustrations/{filename})"
                # 如果没有找到匹配，尝试用正则匹配
                for base64_url, filename in base64_to_file.items():
                    if 'base64,' in image_path and 'base64,' in base64_url:
                        # 提取base64数据部分进行部分匹配
                        try:
                            img_b64_part = image_path.split('base64,')[1][:50]  # 取前50个字符
                            url_b64_part = base64_url.split('base64,')[1][:50]
                            if img_b64_part == url_b64_part:
                                logger.debug(f"通过部分匹配找到base64图片: {filename}")
                                return f"![{alt_text}](illustrations/{filename})"
                        except:
                            pass
                return match.group(0)
            
            # 检查是否在图片文件映射中（完全匹配）
            if image_path in image_file_mappings:
                new_filename = image_file_mappings[image_path]
                logger.debug(f"替换图片链接: {image_path} -> {new_filename}")
                return f"![{alt_text}](illustrations/{new_filename})"
            
            # 尝试匹配相对路径或文件名
            image_name = Path(image_path).name
            for original_path, new_filename in image_file_mappings.items():
                if Path(original_path).name == image_name:
                    logger.debug(f"按文件名匹配替换: {image_path} -> {new_filename}")
                    return f"![{alt_text}](illustrations/{new_filename})"
            
            # 如果没有找到映射，使用原文件名但改为illustrations路径
            filename = Path(image_path).name
            logger.debug(f"未找到映射，使用原文件名: {image_path} -> {filename}")
            return f"![{alt_text}](illustrations/{filename})"
        
        # 替换图片链接
        markdown_content = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', replace_image_link, markdown_content)
        
        if original_content != markdown_content:
            logger.debug(f"图片链接转换完成，共替换 {replacement_count} 个base64图片")
        
        return markdown_content
    
    def _convert_nav_map_to_chapter_config(self, nav_map: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                content_src = nav_point.get('content', '')
                if content_src:
                    # 移除锚点（#）部分，只保留文件名
                    file_name = content_src.split('#')[0]
                    
                    # 如果文件名以.xhtml结尾，替换为.md
                    if file_name.endswith('.xhtml'):
                        file_name = file_name.replace('.xhtml', '.md')
                    
                    # 创建章节对象
                    counter[0] += 1
                    chapter = {
                        "id": counter[0],
                        "title": nav_point.get('label', ''),
                        "file": file_name,
                        "level": level
                    }
                    
                    chapters.append(chapter)
                
                # 递归处理子章节
                if 'children' in nav_point:
                    extract_chapters(nav_point['children'], level + 1)
        
        extract_chapters(nav_map)
        
        return {
            "chapters": chapters,
            "generated_from": "epub_ncx",
            "generated_at": ""
        }
    
    async def convert_epub_dir_to_zip(self, epub_dir_path: str, output_zip_path: str, 
                                    generate_chapter_config: bool = False) -> Dict[str, Any]:
        """
        将解压后的EPUB目录转换为ZIP文件，并可选择生成chapter-config.json
        
        Args:
            epub_dir_path: 解压后的EPUB目录路径
            output_zip_path: 输出ZIP文件路径
            generate_chapter_config: 是否生成chapter-config.json文件
            
        Returns:
            操作结果字典
        """
        try:
            epub_dir = Path(epub_dir_path)
            
            if not epub_dir.exists() or not epub_dir.is_dir():
                raise ValueError(f"EPUB目录不存在或不是目录: {epub_dir_path}")
            
            # 查找content.opf文件
            content_opf_files = list(epub_dir.rglob("content.opf"))
            if not content_opf_files:
                # 如果没有找到content.opf，查找*.opf文件
                opf_files = list(epub_dir.rglob("*.opf"))
                if not opf_files:
                    raise ValueError("在EPUB目录中未找到.opf文件")
                content_opf_path = opf_files[0]
            else:
                content_opf_path = content_opf_files[0]
            
            logger.info(f"找到OPF文件: {content_opf_path}")
            
            # 解析content.opf文件
            opf_data = self.parse_content_opf(content_opf_path)
            
            # 可选：生成chapter-config.json
            chapter_config_data = None
            if generate_chapter_config:
                # 查找NCX文件
                ncx_href = opf_data.get('ncx_href')
                if ncx_href:
                    ncx_path = content_opf_path.parent / ncx_href
                    if ncx_path.exists():
                        logger.info(f"找到NCX文件: {ncx_path}")
                        ncx_data = self.parse_ncx_file(ncx_path)
                        chapter_config_data = self._convert_nav_map_to_chapter_config(ncx_data['nav_map'])
                        
                        # 添加生成时间
                        import datetime
                        chapter_config_data['generated_at'] = datetime.datetime.now().isoformat()
                        
                        # 保存chapter-config.json到EPUB目录
                        chapter_config_path = epub_dir / "chapter-config.json"
                        with open(chapter_config_path, 'w', encoding='utf-8') as f:
                            json.dump(chapter_config_data, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"已生成chapter-config.json: {chapter_config_path}")
                    else:
                        logger.warning(f"NCX文件不存在: {ncx_path}")
                else:
                    logger.warning("在OPF文件中未找到NCX文件引用")
            
            # 创建ZIP文件
            output_zip = Path(output_zip_path)
            output_zip.parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加所有文件到ZIP
                for file_path in epub_dir.rglob('*'):
                    if file_path.is_file():
                        # 计算相对路径
                        arc_name = file_path.relative_to(epub_dir)
                        zipf.write(file_path, arc_name)
                        logger.debug(f"添加文件到ZIP: {arc_name}")
            
            logger.info(f"ZIP文件创建成功: {output_zip}")
            
            # 收集统计信息
            zip_size = output_zip.stat().st_size
            file_count = len(list(epub_dir.rglob('*')))
            
            result = {
                "status": "success",
                "message": "EPUB目录转换为ZIP文件成功",
                "output_file": str(output_zip),
                "zip_size": zip_size,
                "file_count": file_count,
                "opf_data": opf_data
            }
            
            if chapter_config_data:
                result["chapter_config"] = chapter_config_data
                result["chapter_config_generated"] = True
            else:
                result["chapter_config_generated"] = False
            
            return result
            
        except Exception as e:
            logger.error(f"转换EPUB目录到ZIP失败: {str(e)}")
            return {
                "status": "error",
                "message": f"转换EPUB目录到ZIP失败: {str(e)}"
            }
    
    async def extract_epub_info(self, epub_file_path: str) -> Dict[str, Any]:
        """
        从EPUB文件中提取信息
        
        Args:
            epub_file_path: EPUB文件路径
            
        Returns:
            EPUB信息字典
        """
        try:
            epub_path = Path(epub_file_path)
            
            if not epub_path.exists():
                raise FileNotFoundError(f"EPUB文件不存在: {epub_file_path}")
            
            # 创建临时目录解压EPUB
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 解压EPUB文件
                with zipfile.ZipFile(epub_path, 'r') as zipf:
                    zipf.extractall(temp_path)
                
                # 查找content.opf文件
                content_opf_files = list(temp_path.rglob("content.opf"))
                if not content_opf_files:
                    opf_files = list(temp_path.rglob("*.opf"))
                    if not opf_files:
                        raise ValueError("在EPUB文件中未找到.opf文件")
                    content_opf_path = opf_files[0]
                else:
                    content_opf_path = content_opf_files[0]
                
                # 解析OPF文件
                opf_data = self.parse_content_opf(content_opf_path)
                
                # 解析NCX文件（如果存在）
                ncx_data = None
                ncx_href = opf_data.get('ncx_href')
                if ncx_href:
                    ncx_path = content_opf_path.parent / ncx_href
                    if ncx_path.exists():
                        ncx_data = self.parse_ncx_file(ncx_path)
                
                # 收集文件统计信息
                file_stats = {
                    "total_files": 0,
                    "html_files": 0,
                    "image_files": 0,
                    "css_files": 0,
                    "other_files": 0
                }
                
                for file_path in temp_path.rglob('*'):
                    if file_path.is_file():
                        file_stats["total_files"] += 1
                        suffix = file_path.suffix.lower()
                        if suffix in ['.html', '.xhtml', '.htm']:
                            file_stats["html_files"] += 1
                        elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
                            file_stats["image_files"] += 1
                        elif suffix == '.css':
                            file_stats["css_files"] += 1
                        else:
                            file_stats["other_files"] += 1
                
                result = {
                    "status": "success",
                    "file_path": str(epub_path),
                    "file_size": epub_path.stat().st_size,
                    "opf_data": opf_data,
                    "file_stats": file_stats
                }
                
                if ncx_data:
                    result["ncx_data"] = ncx_data
                
                return result
                
        except Exception as e:
            logger.error(f"提取EPUB信息失败: {str(e)}")
            return {
                "status": "error",
                "message": f"提取EPUB信息失败: {str(e)}"
            }
    
    async def validate_epub_structure(self, epub_file_path: str) -> Dict[str, Any]:
        """
        验证EPUB文件结构
        
        Args:
            epub_file_path: EPUB文件路径
            
        Returns:
            验证结果字典
        """
        try:
            epub_path = Path(epub_file_path)
            
            if not epub_path.exists():
                raise FileNotFoundError(f"EPUB文件不存在: {epub_file_path}")
            
            validation_results = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "structure_info": {}
            }
            
            # 创建临时目录解压EPUB
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 解压EPUB文件
                try:
                    with zipfile.ZipFile(epub_path, 'r') as zipf:
                        zipf.extractall(temp_path)
                except zipfile.BadZipFile:
                    validation_results["is_valid"] = False
                    validation_results["errors"].append("文件不是有效的ZIP/EPUB文件")
                    return validation_results
                
                # 检查必需文件
                mimetype_path = temp_path / "mimetype"
                if not mimetype_path.exists():
                    validation_results["errors"].append("缺少mimetype文件")
                    validation_results["is_valid"] = False
                else:
                    # 检查mimetype内容
                    try:
                        with open(mimetype_path, 'r', encoding='utf-8') as f:
                            mimetype_content = f.read().strip()
                        if mimetype_content != "application/epub+zip":
                            validation_results["warnings"].append(f"mimetype内容不正确: {mimetype_content}")
                    except Exception as e:
                        validation_results["warnings"].append(f"读取mimetype文件失败: {str(e)}")
                
                # 检查META-INF/container.xml
                container_path = temp_path / "META-INF" / "container.xml"
                if not container_path.exists():
                    validation_results["errors"].append("缺少META-INF/container.xml文件")
                    validation_results["is_valid"] = False
                
                # 查找OPF文件
                content_opf_files = list(temp_path.rglob("content.opf"))
                opf_files = list(temp_path.rglob("*.opf"))
                
                if not content_opf_files and not opf_files:
                    validation_results["errors"].append("未找到OPF文件")
                    validation_results["is_valid"] = False
                else:
                    opf_path = content_opf_files[0] if content_opf_files else opf_files[0]
                    validation_results["structure_info"]["opf_file"] = str(opf_path.relative_to(temp_path))
                    
                    # 尝试解析OPF文件
                    try:
                        opf_data = self.parse_content_opf(opf_path)
                        validation_results["structure_info"]["manifest_items"] = len(opf_data.get("manifest", {}))
                        validation_results["structure_info"]["spine_items"] = len(opf_data.get("spine", []))
                        validation_results["structure_info"]["has_ncx"] = bool(opf_data.get("ncx_href"))
                    except Exception as e:
                        validation_results["errors"].append(f"解析OPF文件失败: {str(e)}")
                        validation_results["is_valid"] = False
                
                # 统计文件信息
                validation_results["structure_info"]["total_files"] = len(list(temp_path.rglob('*')))
            
            return validation_results
            
        except Exception as e:
            logger.error(f"验证EPUB结构失败: {str(e)}")
            return {
                "status": "error",
                "message": f"验证EPUB结构失败: {str(e)}",
                "is_valid": False,
                "errors": [str(e)],
                "warnings": [],
                "structure_info": {}
            }
    
    async def convert_epub_to_markdown(self, epub_file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """
        将EPUB文件转换为Markdown格式
        
        Args:
            epub_file_path: EPUB文件路径
            output_dir: 输出目录，如果为None则使用临时目录
            
        Returns:
            转换结果字典
        """
        try:
            import tempfile
            import shutil
            from app.common import get_user_directory
            
            epub_path = Path(epub_file_path)
            
            if not epub_path.exists():
                raise FileNotFoundError(f"EPUB文件不存在: {epub_file_path}")
            
            # 创建临时目录解压EPUB
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                extract_path = temp_path / "extracted"
                
                # 解压EPUB文件
                logger.info(f"开始解压EPUB文件: {epub_path}")
                with zipfile.ZipFile(epub_path, 'r') as zipf:
                    zipf.extractall(extract_path)
                
                # 查找并解析content.opf文件
                content_opf_files = list(extract_path.rglob("content.opf"))
                if not content_opf_files:
                    opf_files = list(extract_path.rglob("*.opf"))
                    if not opf_files:
                        raise ValueError("在EPUB文件中未找到.opf文件")
                    content_opf_path = opf_files[0]
                else:
                    content_opf_path = content_opf_files[0]
                
                logger.info(f"找到OPF文件: {content_opf_path}")
                opf_data = self.parse_content_opf(content_opf_path)
                
                # 解析NCX文件获取章节信息
                chapter_config_data = None
                ncx_href = opf_data.get('ncx_href')
                if ncx_href:
                    ncx_path = content_opf_path.parent / ncx_href
                    if ncx_path.exists():
                        logger.info(f"找到NCX文件: {ncx_path}")
                        ncx_data = self.parse_ncx_file(ncx_path)
                        chapter_config_data = self._convert_nav_map_to_chapter_config(ncx_data['nav_map'])
                
                # 确定输出目录
                if output_dir:
                    final_output_dir = Path(output_dir)
                else:
                    final_output_dir = temp_path / "converted"
                
                final_output_dir.mkdir(parents=True, exist_ok=True)
                
                # 创建markdown文件的输出目录
                chapters_dir = final_output_dir / "chapters"
                chapters_dir.mkdir(exist_ok=True)
                
                # 创建css目录并复制CSS文件
                css_dir = final_output_dir / "css"
                css_dir.mkdir(exist_ok=True)
                
                # 创建插图目录
                illustrations_dir = final_output_dir / "illustrations"
                illustrations_dir.mkdir(exist_ok=True)
                
                # 处理manifest中的文件
                manifest = opf_data.get('manifest', {})
                spine = opf_data.get('spine', [])
                
                # 首先复制和处理图片文件
                image_files = []
                all_images = []  # 用于封面识别
                image_file_mappings = {}  # 原始路径到新文件名的映射
                
                # 首先收集所有图片信息
                logger.info("开始收集EPUB中的图片文件...")
                for item_id, item in manifest.items():
                    media_type = item.get('media_type', '')
                    if 'image' in media_type:
                        img_source = content_opf_path.parent / item['href']
                        logger.debug(f"找到图片文件: {item['href']} (类型: {media_type})")
                        if img_source.exists():
                            all_images.append({
                                'source': img_source,
                                'href': item['href'],
                                'item_id': item_id
                            })
                            # 记录原始路径到新文件名的映射
                            original_href = item['href']
                            image_file_mappings[original_href] = Path(original_href).name
                            logger.debug(f"添加图片映射: {original_href} -> {Path(original_href).name}")
                        else:
                            logger.warning(f"图片文件不存在: {img_source}")
                
                logger.info(f"共找到 {len(all_images)} 个图片文件")
                
                # 处理封面图片命名
                logger.info("开始处理图片文件命名和复制...")
                updated_image_mappings = self._process_images_with_cover_naming(all_images, illustrations_dir)
                # 合并映射
                image_file_mappings.update(updated_image_mappings)
                # 获取处理后的文件列表
                image_files = list(updated_image_mappings.values())
                
                logger.info(f"图片处理结果: 处理了 {len(image_files)} 个文件")
                for original, new in updated_image_mappings.items():
                    logger.debug(f"图片映射: {original} -> {new}")
                
                # 获取spine中的XHTML文件顺序
                xhtml_files = []
                for spine_item in spine:
                    idref = spine_item.get('idref')
                    if idref in manifest:
                        item = manifest[idref]
                        href = item.get('href')
                        media_type = item.get('media_type')
                        if media_type and 'html' in media_type and href:
                            xhtml_file_path = content_opf_path.parent / href
                            if xhtml_file_path.exists():
                                xhtml_files.append({
                                    'id': idref,
                                    'path': xhtml_file_path,
                                    'href': href,
                                    'title': f'Chapter {len(xhtml_files) + 1}'
                                })
                
                # 转换XHTML文件为Markdown
                converted_files = []
                logger.info(f"开始转换 {len(xhtml_files)} 个XHTML文件为Markdown...")
                for i, xhtml_file in enumerate(xhtml_files):
                    logger.debug(f"正在处理文件 {i+1}/{len(xhtml_files)}: {xhtml_file['href']}")
                    try:
                        # 首先读取XHTML内容，提取base64图片
                        with open(xhtml_file['path'], 'r', encoding='utf-8') as f:
                            xhtml_content = f.read()
                        
                        logger.debug(f"XHTML文件大小: {len(xhtml_content)} 字符")
                        
                        # 尝试从 XHTML 内容中提取标题
                        title = xhtml_file['title']
                        try:
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(xhtml_content, 'html.parser')
                                # 尝试从 h1, h2, title 标签中提取标题
                                for tag in ['h1', 'h2', 'title']:
                                    element = soup.find(tag)
                                    if element and element.get_text(strip=True):
                                        title = element.get_text(strip=True)
                                        logger.debug(f"从{tag}标签提取标题: {title}")
                                        break
                            except ImportError:
                                # 如果 BeautifulSoup 不可用，使用简单的正则提取
                                import re
                                for pattern in [r'<h1[^>]*>([^<]+)</h1>', r'<h2[^>]*>([^<]+)</h2>', r'<title[^>]*>([^<]+)</title>']:
                                    match = re.search(pattern, xhtml_content, re.IGNORECASE)
                                    if match:
                                        title = match.group(1).strip()
                                        logger.debug(f"通过正则提取标题: {title}")
                                        break
                        except Exception as e:
                            logger.debug(f"无法从 XHTML 中提取标题: {str(e)}")
                        
                        # 提取并转换base64图片
                        logger.debug("开始提取base64图片...")
                        base64_to_file = self._extract_base64_images_from_content(xhtml_content, illustrations_dir)
                        
                        # 使用pandoc转换XHTML到Markdown
                        input_path = xhtml_file['path']
                        output_filename = f"{i+1:02d}-{xhtml_file['id']}.md"
                        output_path = chapters_dir / output_filename
                        
                        logger.debug(f"开始使用Pandoc转换: {input_path} -> {output_path}")
                        
                        # 调用pandoc进行转换
                        import subprocess
                        pandoc_cmd = [
                            'pandoc',
                            str(input_path),
                            '-f', 'html',
                            '-t', 'markdown',
                            '-o', str(output_path),
                            '--wrap=none'
                        ]
                        
                        logger.debug(f"Pandoc命令: {' '.join(pandoc_cmd)}")
                        
                        result = subprocess.run(pandoc_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                        if result.returncode == 0:
                            logger.debug(f"Pandoc转换成功: {output_filename}")
                            
                            # 读取转换后的Markdown文件
                            with open(output_path, 'r', encoding='utf-8') as f:
                                markdown_content = f.read()
                            
                            logger.debug(f"转换后Markdown大小: {len(markdown_content)} 字符")
                            logger.debug(f"开始转换图片链接，base64数量: {len(base64_to_file)}, 文件映射数量: {len(image_file_mappings)}")
                            
                            # 转换图片链接
                            markdown_content = self._convert_image_links_in_markdown(markdown_content, base64_to_file, image_file_mappings)
                            
                            # 写回转换后的内容
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(markdown_content)
                            
                            converted_files.append({
                                'original': xhtml_file['href'],
                                'converted': output_filename,
                                'title': title,
                                'id': xhtml_file['id']
                            })
                            logger.info(f"成功转换: {xhtml_file['href']} -> {output_filename} (标题: {title})")
                        else:
                            logger.warning(f"转换失败: {xhtml_file['href']}, 错误: {result.stderr}")
                            
                    except Exception as e:
                        logger.warning(f"转换文件失败 {xhtml_file['href']}: {str(e)}")
                
                # 复制CSS文件
                css_files = []
                for item_id, item in manifest.items():
                    if item.get('media_type') == 'text/css':
                        css_source = content_opf_path.parent / item['href']
                        if css_source.exists():
                            css_target = css_dir / Path(item['href']).name
                            shutil.copy2(css_source, css_target)
                            css_files.append(Path(item['href']).name)
                            logger.info(f"复制CSS文件: {item['href']}")
                

                
                # 生成元数据文件
                metadata = opf_data.get('metadata', {})
                metadata_content = f"""---
title: "{metadata.get('title', 'Converted EPUB')}"
author: "{metadata.get('creator', 'Unknown')}"
language: "{metadata.get('language', 'en')}"
---

# {metadata.get('title', 'Converted EPUB')}

> 作者: {metadata.get('creator', 'Unknown')}
> 语言: {metadata.get('language', 'en')}
> 转换日期: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

本文档由EPUB文件转换而来。
"""
                
                # 写入metadata.yml文件
                with open(final_output_dir / "metadata.yml", 'w', encoding='utf-8') as f:
                    f.write(metadata_content)
                
                # 生成chapter-config.json文件
                if chapter_config_data:
                    # 更新章节文件名为实际转换的文件名
                    chapters = chapter_config_data.get('chapters', [])
                    for i, chapter in enumerate(chapters):
                        if i < len(converted_files):
                            # 使用实际转换的文件名
                            converted_file = converted_files[i]
                            chapter['file'] = f"chapters/{converted_file['converted']}"
                            # 保持原有的标题或使用转换文件的标题
                            if not chapter.get('title') or chapter['title'].startswith('Chapter'):
                                chapter['title'] = converted_file.get('title', chapter.get('title', f'Chapter {i+1}'))
                        else:
                            # 如果转换文件不够，就保持原有文件名但加上路径
                            if not chapter['file'].startswith('chapters/'):
                                chapter['file'] = f"chapters/{chapter['file']}"
                    
                    # 确保添加生成时间
                    import datetime
                    chapter_config_data['generated_at'] = datetime.datetime.now().isoformat()
                    
                    # 写入chapter-config.json文件
                    with open(final_output_dir / "chapter-config.json", 'w', encoding='utf-8') as f:
                        json.dump(chapter_config_data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"已生成chapter-config.json，包含 {len(chapters)} 个章节")
                else:
                    # 如果没有NCX数据，则根据转换的文件生成基本的chapter-config.json
                    import datetime
                    basic_chapters = []
                    for i, converted_file in enumerate(converted_files):
                        basic_chapters.append({
                            "id": i + 1,
                            "title": converted_file.get('title', f'Chapter {i+1}'),
                            "file": f"chapters/{converted_file['converted']}",
                            "level": 0
                        })
                    
                    basic_config = {
                        "chapters": basic_chapters,
                        "generated_from": "converted_files",
                        "generated_at": datetime.datetime.now().isoformat()
                    }
                    
                    with open(final_output_dir / "chapter-config.json", 'w', encoding='utf-8') as f:
                        json.dump(basic_config, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"已生成基本的chapter-config.json，包含 {len(basic_chapters)} 个章节")
                
                # 如果是临时目录，需要创建ZIP文件
                if not output_dir:
                    zip_path = temp_path / "converted.zip"
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # 将转换后的文件打包在src目录下
                        for file_path in final_output_dir.rglob('*'):
                            if file_path.is_file():
                                # 计算相对路径，并在前面加上src/
                                arc_name = "src" / file_path.relative_to(final_output_dir)
                                zipf.write(file_path, arc_name)
                    
                    # 将ZIP文件移动到用户目录
                    from app.common import get_user_directory
                    # 这里需要获取当前用户，但为了简化，我们将ZIP文件保存在临时目录
                    # 实际使用时会在controller中处理用户目录
                    final_zip_path = zip_path
                else:
                    final_zip_path = None
                
                result = {
                    "status": "success",
                    "message": "EPUB转换为Markdown成功",
                    "output_dir": str(final_output_dir),
                    "converted_files": converted_files,
                    "css_files": css_files,
                    "image_files": image_files,
                    "total_chapters": len(converted_files),
                    "metadata": metadata,
                    "illustrations_count": len(image_files)
                }
                
                if final_zip_path:
                    result["zip_file"] = str(final_zip_path)
                    result["zip_size"] = final_zip_path.stat().st_size
                
                if chapter_config_data:
                    result["chapter_config"] = chapter_config_data
                
                return result
                
        except Exception as e:
            logger.error(f"EPUB转换为Markdown失败: {str(e)}")
            return {
                "status": "error",
                "message": f"EPUB转换为Markdown失败: {str(e)}"
            }