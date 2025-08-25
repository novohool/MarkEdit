"""
Build service for MarkEdit application.

This module contains business logic for building various formats:
- EPUB generation
- PDF generation  
- HTML generation
- File processing and optimization
"""
import os
import json
import subprocess
import shutil
import logging
import yaml
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import datetime

logger = logging.getLogger(__name__)

class BuildService:
    """构建服务类"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.src_dir = self.base_dir / "src"
        self.build_dir = self.base_dir / "build"
        
        # 确保构建目录存在
        self.build_dir.mkdir(parents=True, exist_ok=True)
    
    def load_metadata_config(self, src_dir: Path) -> Dict[str, Any]:
        """从metadata.yml文件加载元数据配置"""
        metadata_path = src_dir / "metadata.yml"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_chapter_config(self, src_dir: Path) -> Dict[str, Any]:
        """从统一配置文件加载章节顺序"""
        chapter_config_path = src_dir / "chapter-config.json"
        with open(chapter_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def copy_illustrations(self, src_illustrations_dir: Path, build_illustrations_dir: Path):
        """复制插图目录到构建目录"""
        if not build_illustrations_dir.exists():
            build_illustrations_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的图像格式
        supported_formats = {'.svg', '.jpg', '.jpeg', '.png', '.gif'}
        
        # 复制所有支持的图像文件到构建目录
        for file in src_illustrations_dir.iterdir():
            if file.suffix.lower() in supported_formats:
                dest_path = build_illustrations_dir / file.name
                shutil.copy2(file, dest_path)
                logger.info(f"已复制插图文件: {file.name}")
    
    def optimize_svg_for_epub(self, svg_content: str) -> str:
        """优化SVG文件以提高epub兼容性"""
        # 确保xmlns属性正确
        if 'xmlns="http://www.w3.org/2000/svg"' not in svg_content:
            svg_content = svg_content.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
        
        # 移除可能不被epub支持的特性
        import re
        svg_content = re.sub(r'<\?xml.*?\?>', '', svg_content)
        
        # 确保SVG有明确的宽度和高度
        if not ('width="' in svg_content and 'height="' in svg_content):
            # 如果没有明确的宽度和高度，添加默认值
            svg_content = re.sub(r'<svg([^>]*?)(?<!width="[^"]*")>', r'<svg\1 width="400" height="300">', svg_content)
        
        # 移除元素上的opacity属性，因为可能不被epub支持
        if 'opacity' in svg_content:
            # 使用正则表达式移除opacity属性
            import re
            svg_content = re.sub(r'\s+opacity\s*=\s*"[^"]*"', '', svg_content)
            svg_content = re.sub(r'opacity\s*=\s*"[^"]*"', '', svg_content)
        
        # 移除style标签中的opacity属性
        def remove_opacity_from_style(match):
            style_content = match.group(0)
            # 移除opacity样式
            import re
            return re.sub(r'opacity\s*:\s*[^;]+;?', '', style_content)
        
        import re
        svg_content = re.sub(r'<style[^>]*>[\s\S]*?</style>', remove_opacity_from_style, svg_content)
        
        return svg_content
    
    def optimize_svgs(self, build_illustrations_dir: Path):
        """优化所有SVG文件"""
        for file in build_illustrations_dir.iterdir():
            if file.suffix == '.svg':
                # 读取SVG内容
                with open(file, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # 优化SVG内容
                optimized_svg_content = self.optimize_svg_for_epub(svg_content)
                
                # 写入优化后的SVG内容
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(optimized_svg_content)
                
                logger.info(f"已优化SVG文件: {file.name}")
    
    def process_chapters_for_epub(self, chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
        """复制并修改章节文件，调整图片路径以适应EPUB"""
        if not temp_chapters_dir.exists():
            temp_chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制并修改章节文件，调整图片路径
        for file_name in chapter_files:
            src_path = chapters_dir / file_name
            dest_path = temp_chapters_dir / file_name
            
            # 读取原始章节文件
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修改图片路径，将 "../illustrations/" 和 "/user-illustrations/" 替换为 "illustrations/"
            content = content.replace('../illustrations/', 'illustrations/')
            content = content.replace('/user-illustrations/', 'illustrations/')
            
            # 写入修改后的章节文件到临时目录
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已处理章节文件: {file_name}")
    
    def process_chapters_for_pdf(self, chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
        """复制并修改章节文件，调整图片路径以适应PDF"""
        if not temp_chapters_dir.exists():
            temp_chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制并修改章节文件，调整图片路径
        for file_name in chapter_files:
            src_path = chapters_dir / file_name
            dest_path = temp_chapters_dir / file_name
            
            # 读取原始章节文件
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修改图片路径，将 "../illustrations/" 和 "/user-illustrations/" 替换为 "./illustrations/"
            content = content.replace('../illustrations/', './illustrations/')
            content = content.replace('/user-illustrations/', './illustrations/')
            
            # 写入修改后的章节文件到临时目录
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已处理章节文件: {file_name}")
    
    def process_chapters_for_html(self, chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
        """复制并修改章节文件，调整图片路径以适应HTML"""
        if not temp_chapters_dir.exists():
            temp_chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制并修改章节文件，调整图片路径
        for file_name in chapter_files:
            src_path = chapters_dir / file_name
            dest_path = temp_chapters_dir / file_name
            
            # 读取原始章节文件
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修改图片路径，将 "../illustrations/" 和 "/user-illustrations/" 替换为 "./illustrations/"
            content = content.replace('../illustrations/', './illustrations/')
            content = content.replace('/user-illustrations/', './illustrations/')
            
            # 写入修改后的章节文件到临时目录
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已处理章节文件: {file_name}")
    
    async def build_epub(self, src_dir: Path = None, build_dir: Path = None) -> Dict[str, Any]:
        """构建EPUB文件"""
        if src_dir is None:
            src_dir = self.src_dir
        if build_dir is None:
            build_dir = self.build_dir
            
        try:
            # 配置目录
            chapters_dir = src_dir / "chapters"
            illustrations_dir = src_dir / "illustrations"
            metadata_file = src_dir / "metadata.yml"
            book_file = src_dir / "book.md"
            css_file = src_dir / "css" / "epub-style.css"
            chapter_config_file = src_dir / "chapter-config.json"
            
            # 创建输出目录（如果不存在）
            build_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制插图目录到构建目录
            build_illustrations_dir = build_dir / "illustrations"
            self.copy_illustrations(illustrations_dir, build_illustrations_dir)
            
            # 优化SVG文件以提高EPUB兼容性
            self.optimize_svgs(build_illustrations_dir)
            
            # 从统一配置文件加载章节顺序
            chapter_config = self.load_chapter_config(src_dir)
            chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
            
            # 为EPUB创建临时章节目录
            temp_chapters_dir = build_dir / "temp-chapters-epub"
            self.process_chapters_for_epub(chapters_dir, temp_chapters_dir, chapter_files)
            
            # 构建pandoc命令参数
            input_files = [metadata_file, book_file]
            
            # 添加章节文件
            input_files.extend([temp_chapters_dir / file for file in chapter_files])
            
            epub_output_path = build_dir / "katakana-dictionary.epub"
            
            logger.info("开始生成EPUB文件...")
            
            # 使用pandoc生成EPUB文件
            pandoc_args = [
                "pandoc"
            ] + [str(f) for f in input_files] + [
                "-o", str(epub_output_path),
                "--from", "markdown",
                "--to", "epub",
                "--toc",
                "--toc-depth=2",
                "--split-level=2",
                f"--css={css_file}",
                f"--resource-path={build_dir}"
            ]
            
            # 构建完整的pandoc命令
            pandoc_command = " ".join(pandoc_args)
            logger.info(f"正在执行命令生成EPUB: {pandoc_command}")
            
            # 执行pandoc命令生成EPUB
            result = subprocess.run(
                pandoc_args,
                cwd=src_dir.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 检查返回码
            if result.returncode == 0:
                logger.info(f"EPUB文件生成成功: {epub_output_path}")
                # 清理临时目录
                if temp_chapters_dir.exists():
                    shutil.rmtree(temp_chapters_dir)
                    logger.info("已清理临时目录")
                
                return {
                    "status": "success",
                    "message": "EPUB文件生成成功",
                    "output_file": str(epub_output_path),
                    "file_size": epub_output_path.stat().st_size
                }
            else:
                error_msg = f"生成EPUB文件时出错: {result.stderr}"
                logger.error(error_msg)
                # 清理临时目录
                if temp_chapters_dir.exists():
                    shutil.rmtree(temp_chapters_dir)
                    logger.info("已清理临时目录")
                
                return {
                    "status": "error",
                    "message": error_msg,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired as e:
            error_msg = f"生成EPUB文件时超时: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"生成EPUB文件时出现未预期的错误: {str(e)}"
            logger.error(error_msg)
            # 记录堆栈跟踪信息
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": error_msg
            }
    
    async def build_pdf(self, src_dir: Path = None, build_dir: Path = None) -> Dict[str, Any]:
        """构建PDF文件"""
        if src_dir is None:
            src_dir = self.src_dir
        if build_dir is None:
            build_dir = self.build_dir
            
        try:
            # 配置目录
            chapters_dir = src_dir / "chapters"
            illustrations_dir = src_dir / "illustrations"
            metadata_file = src_dir / "metadata.yml"
            book_file = src_dir / "book.md"
            css_file = src_dir / "css" / "pdf-style.css"
            chapter_config_file = src_dir / "chapter-config.json"
            
            # 创建输出目录（如果不存在）
            build_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制插图目录到构建目录
            build_illustrations_dir = build_dir / "illustrations"
            self.copy_illustrations(illustrations_dir, build_illustrations_dir)
            
            # 从统一配置文件加载章节顺序
            chapter_config = self.load_chapter_config(src_dir)
            chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
            
            # 为PDF创建临时章节目录
            temp_chapters_dir = build_dir / "temp-chapters-pdf"
            self.process_chapters_for_pdf(chapters_dir, temp_chapters_dir, chapter_files)
            
            # 构建pandoc命令参数
            input_files = [metadata_file, book_file]
            
            # 添加章节文件
            input_files.extend([temp_chapters_dir / file for file in chapter_files])
            
            pdf_output_path = build_dir / "katakana-dictionary.pdf"
            
            logger.info("开始生成PDF文件...")
            
            # 使用pandoc生成PDF文件
            pandoc_args = [
                "pandoc"
            ] + [str(f) for f in input_files] + [
                "-o", str(pdf_output_path),
                "--from", "markdown",
                "--to", "pdf",
                "--toc",
                "--toc-depth=2",
                f"--css={css_file}",
                "--pdf-engine=xelatex",
                f"--resource-path={build_dir}"
            ]
            
            # 构建完整的pandoc命令
            pandoc_command = " ".join(pandoc_args)
            logger.info(f"正在执行命令生成PDF: {pandoc_command}")
            
            # 执行pandoc命令生成PDF
            result = subprocess.run(
                pandoc_args,
                cwd=src_dir.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=600  # 10分钟超时（PDF生成可能需要更长时间）
            )
            
            # 检查返回码
            if result.returncode == 0:
                logger.info(f"PDF文件生成成功: {pdf_output_path}")
                # 清理临时目录
                if temp_chapters_dir.exists():
                    shutil.rmtree(temp_chapters_dir)
                    logger.info("已清理临时目录")
                
                return {
                    "status": "success",
                    "message": "PDF文件生成成功",
                    "output_file": str(pdf_output_path),
                    "file_size": pdf_output_path.stat().st_size
                }
            else:
                error_msg = f"生成PDF文件时出错: {result.stderr}"
                logger.error(error_msg)
                # 清理临时目录
                if temp_chapters_dir.exists():
                    shutil.rmtree(temp_chapters_dir)
                    logger.info("已清理临时目录")
                
                return {
                    "status": "error",
                    "message": error_msg,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired as e:
            error_msg = f"生成PDF文件时超时: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"生成PDF文件时出现未预期的错误: {str(e)}"
            logger.error(error_msg)
            # 记录堆栈跟踪信息
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": error_msg
            }
    
    async def build_html(self, src_dir: Path = None, build_dir: Path = None) -> Dict[str, Any]:
        """构建HTML文件"""
        if src_dir is None:
            src_dir = self.src_dir
        if build_dir is None:
            build_dir = self.build_dir
            
        try:
            # 配置目录
            chapters_dir = src_dir / "chapters"
            illustrations_dir = src_dir / "illustrations"
            metadata_file = src_dir / "metadata.yml"
            book_file = src_dir / "book.md"
            css_file = src_dir / "css" / "common-style.css"
            chapter_config_file = src_dir / "chapter-config.json"
            
            # 创建输出目录（如果不存在）
            build_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制插图目录到构建目录
            build_illustrations_dir = build_dir / "illustrations"
            self.copy_illustrations(illustrations_dir, build_illustrations_dir)
            
            # 从metadata.yml加载封面信息
            cover_image_path = None
            try:
                metadata_config = self.load_metadata_config(src_dir)
                cover_md_file = metadata_config.get("cover")
                if cover_md_file:
                    # 读取cover.md文件内容，提取图片路径
                    cover_md_path = src_dir / cover_md_file
                    if cover_md_path.exists():
                        with open(cover_md_path, 'r', encoding='utf-8') as f:
                            cover_content = f.read()
                            # 简单解析Markdown图片语法 ![alt](path)
                            import re
                            match = re.search(r'!\[.*?\]\((.*?)\)', cover_content)
                            if match:
                                cover_image_relative_path = match.group(1)
                                # 检查图片文件是否存在
                                cover_image_path_obj = src_dir / cover_image_relative_path
                                if cover_image_path_obj.exists():
                                    cover_image_path = f"./{cover_image_relative_path}"
            except Exception as e:
                logger.warning(f"从metadata.yml加载封面信息失败: {e}")
            
            # 如果无法从metadata.yml获取封面信息，则使用原来的逻辑
            if not cover_image_path:
                possible_cover_files = ["cover.jpg", "cover.png", "cover_1.jpg", "cover_1.png"]
                for cover_file in possible_cover_files:
                    cover_path = illustrations_dir / cover_file
                    if cover_path.exists():
                        cover_image_path = f"./illustrations/{cover_file}"
                        break
            
            # 从统一配置文件加载章节顺序
            chapter_config = self.load_chapter_config(src_dir)
            chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
            
            # 为HTML创建临时章节目录
            temp_chapters_dir = build_dir / "temp-chapters-html"
            self.process_chapters_for_html(chapters_dir, temp_chapters_dir, chapter_files)
            
            # 构建pandoc命令参数
            input_files = [metadata_file, book_file]
            
            # 添加章节文件
            input_files.extend([temp_chapters_dir / file for file in chapter_files])
            
            html_output_path = build_dir / "katakana-dictionary.html"
            
            logger.info("开始生成HTML文件...")
            
            # 使用pandoc生成HTML文件
            pandoc_args = [
                "pandoc"
            ] + [str(f) for f in input_files] + [
                "-o", str(html_output_path),
                "--toc",
                "--toc-depth=2",
                "--split-level=2",
                f"--css={css_file}",
                "--standalone",
                "--embed-resources",
                "--from", "markdown",
                "--html-q-tags",
                f"--resource-path={build_dir}"
            ]
            
            # 构建完整的pandoc命令
            pandoc_command = " ".join(pandoc_args)
            logger.info(f"正在执行命令生成HTML: {pandoc_command}")
            
            # 执行pandoc命令生成HTML
            result = subprocess.run(
                pandoc_args,
                cwd=src_dir.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 检查返回码
            if result.returncode == 0:
                logger.info(f"HTML文件生成成功: {html_output_path}")
                # 清理临时目录
                if temp_chapters_dir.exists():
                    shutil.rmtree(temp_chapters_dir)
                    logger.info("已清理临时目录")
                
                return {
                    "status": "success",
                    "message": "HTML文件生成成功",
                    "output_file": str(html_output_path),
                    "file_size": html_output_path.stat().st_size
                }
            else:
                error_msg = f"生成HTML文件时出错: {result.stderr}"
                logger.error(error_msg)
                # 清理临时目录
                if temp_chapters_dir.exists():
                    shutil.rmtree(temp_chapters_dir)
                    logger.info("已清理临时目录")
                
                return {
                    "status": "error",
                    "message": error_msg,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired as e:
            error_msg = f"生成HTML文件时超时: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"生成HTML文件时出现未预期的错误: {str(e)}"
            logger.error(error_msg)
            # 记录堆栈跟踪信息
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": error_msg
            }
    
    async def get_build_info(self) -> Dict[str, Any]:
        """获取构建信息"""
        try:
            build_info = {
                "build_dir": str(self.build_dir),
                "src_dir": str(self.src_dir),
                "build_files": [],
                "last_build_time": None
            }
            
            # 检查构建目录中的文件
            if self.build_dir.exists():
                for file_path in self.build_dir.iterdir():
                    if file_path.is_file() and file_path.suffix in ['.epub', '.pdf', '.html']:
                        stat = file_path.stat()
                        build_info["build_files"].append({
                            "name": file_path.name,
                            "size": stat.st_size,
                            "created_at": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                
                # 按修改时间排序
                build_info["build_files"].sort(key=lambda x: x["modified_at"], reverse=True)
                
                # 获取最新构建时间
                if build_info["build_files"]:
                    build_info["last_build_time"] = build_info["build_files"][0]["modified_at"]
            
            return build_info
            
        except Exception as e:
            logger.error(f"获取构建信息失败: {str(e)}")
            return {
                "build_dir": str(self.build_dir),
                "src_dir": str(self.src_dir),
                "build_files": [],
                "last_build_time": None,
                "error": f"获取构建信息失败: {str(e)}"
            }