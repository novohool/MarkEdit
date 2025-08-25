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