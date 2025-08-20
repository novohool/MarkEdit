import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging
import yaml

# 创建logger
logger = logging.getLogger(__name__)

def load_metadata_config(src_dir: Path) -> Dict[str, Any]:
    """从metadata.yml文件加载元数据配置"""
    metadata_path = src_dir / "metadata.yml"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_chapter_config(src_dir: Path) -> Dict[str, Any]:
    """从统一配置文件加载章节顺序"""
    chapter_config_path = src_dir / "chapter-config.json"
    with open(chapter_config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def copy_illustrations(src_illustrations_dir: Path, build_illustrations_dir: Path):
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

def optimize_svg_for_epub(svg_content: str) -> str:
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


def optimize_svgs(build_illustrations_dir: Path):
    """优化所有SVG文件"""
    for file in build_illustrations_dir.iterdir():
        if file.suffix == '.svg':
            # 读取SVG内容
            with open(file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # 优化SVG内容
            optimized_svg_content = optimize_svg_for_epub(svg_content)
            
            # 写入优化后的SVG内容
            with open(file, 'w', encoding='utf-8') as f:
                f.write(optimized_svg_content)
            
            logger.info(f"已优化SVG文件: {file.name}")

def process_chapters_for_epub(chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
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
        
        # 修改图片路径，将 "../illustrations/" 替换为 "illustrations/"
        content = content.replace('../illustrations/', 'illustrations/')
        
        # 写入修改后的章节文件到临时目录
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"已处理章节文件: {file_name}")

def process_chapters_for_pdf(chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
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
        
        # 修改图片路径，将 "../illustrations/" 替换为 "./illustrations/"
        content = content.replace('../illustrations/', './illustrations/')
        
        # 写入修改后的章节文件到临时目录
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"已处理章节文件: {file_name}")

def process_chapters_for_html(chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
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
        
        # 修改图片路径，将 "../illustrations/" 替换为 "./illustrations/"
        content = content.replace('../illustrations/', './illustrations/')
        
        # 写入修改后的章节文件到临时目录
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"已处理章节文件: {file_name}")

def build_html(src_dir: Path, build_dir: Path) -> Dict[str, Any]:
    """构建HTML文件"""
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
        copy_illustrations(illustrations_dir, build_illustrations_dir)
        
        # 从metadata.yml加载封面信息
        cover_image_path = None
        try:
            metadata_config = load_metadata_config(src_dir)
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
        chapter_config = load_chapter_config(src_dir)
        chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
        
        # 为HTML创建临时章节目录
        temp_chapters_dir = build_dir / "temp-chapters-html"
        process_chapters_for_html(chapters_dir, temp_chapters_dir, chapter_files)
        
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
                "output_file": str(html_output_path)
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

def build_epub(src_dir: Path, build_dir: Path) -> Dict[str, Any]:
    """构建EPUB文件"""
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
        copy_illustrations(illustrations_dir, build_illustrations_dir)
        
        # 优化所有SVG文件
        optimize_svgs(build_illustrations_dir)
        
        # 自动检测封面图片文件
        cover_image_path = None
        cover_image_file = illustrations_dir / "cover.jpg"
        if cover_image_file.exists():
            cover_image_path = "illustrations/cover.jpg"
            logger.info(f"检测到封面图片文件: {cover_image_path}")
        else:
            # 检查其他可能的封面文件名
            possible_cover_files = ["cover.png", "cover_1.jpg", "cover_1.png"]
            for cover_file in possible_cover_files:
                cover_path = illustrations_dir / cover_file
                if cover_path.exists():
                    cover_image_path = f"illustrations/{cover_file}"
                    logger.info(f"检测到封面图片文件: {cover_image_path}")
                    break
            
            if not cover_image_path:
                logger.info("未找到封面图片文件")
        
        # 从统一配置文件加载章节顺序
        chapter_config = load_chapter_config(src_dir)
        chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
        
        # 检查第一章是否是封面章节
        first_chapter_is_cover = False
        if chapter_files:
            first_chapter_file = chapter_files[0]
            # 检查第一章文件名是否包含"cover"
            if "cover" in first_chapter_file.lower():
                first_chapter_is_cover = True
                logger.info(f"检测到第一章是封面章节: {first_chapter_file}")
        
        # 为EPUB创建临时章节目录
        temp_chapters_dir = build_dir / "temp-chapters"
        process_chapters_for_epub(chapters_dir, temp_chapters_dir, chapter_files)
        
        # 构建pandoc命令参数
        input_files = [metadata_file, book_file]
        
        
        # 添加章节文件
        input_files.extend([temp_chapters_dir / file for file in chapter_files])
        
        output_file_path = build_dir / "katakana-dictionary.epub"
        
        pandoc_args = [
            "pandoc"
        ] + [str(f) for f in input_files] + [
            "-o", str(output_file_path),
            "--toc",
            "--toc-depth=2",
            "--split-level=2",
            f"--css={css_file}",
            "--from", "markdown",
            "--html-q-tags",
            "--embed-resources",
            f"--resource-path={build_dir}"
        ]
        
        # 如果有封面图片文件，添加--epub-cover-image参数
        if cover_image_path:
            # 确保封面图片在构建目录中存在
            cover_image_filename = cover_image_path.split('/')[-1]
            cover_image_build_path = build_illustrations_dir / cover_image_filename
            if cover_image_build_path.exists():
                # 使用相对于pandoc执行目录的路径
                # pandoc在src_dir.parent目录中执行，所以需要使用build_dir.relative_to(src_dir.parent)
                relative_build_path = build_dir.relative_to(src_dir.parent)
                pandoc_args.extend(["--epub-cover-image", f"{relative_build_path}/illustrations/{cover_image_filename}"])
                logger.info(f"已添加EPUB封面图片参数: {relative_build_path}/illustrations/{cover_image_filename}")
            else:
                logger.warning(f"封面图片文件不存在于构建目录中: {cover_image_build_path}")
        
        # 构建完整的pandoc命令
        command = " ".join(pandoc_args)
        logger.info(f"正在执行命令: {command}")
        
        # 执行pandoc命令
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
            logger.info(f"EPUB文件生成成功: {output_file_path}")
            # 清理临时目录
            if temp_chapters_dir.exists():
                shutil.rmtree(temp_chapters_dir)
                logger.info("已清理临时目录")
            
            return {
                "status": "success",
                "message": "EPUB文件生成成功",
                "output_file": str(output_file_path)
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

def build_pdf(src_dir: Path, build_dir: Path) -> Dict[str, Any]:
    """构建PDF文件"""
    try:
        # 配置目录
        chapters_dir = src_dir / "chapters"
        illustrations_dir = src_dir / "illustrations"
        metadata_file = src_dir / "metadata.yml"
        book_file = src_dir / "book.md"
        css_file = src_dir / "css" / "common-style.css"
        chapter_config_file = src_dir / "chapter-config.json"
        
        # wkhtmltopdf路径配置
        wkhtmltopdf_path = os.environ.get("WKHTMLTOPDF_PATH", "wkhtmltopdf")
        
        # 创建输出目录（如果不存在）
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制插图目录到构建目录
        build_illustrations_dir = build_dir / "illustrations"
        copy_illustrations(illustrations_dir, build_illustrations_dir)
        
        # 从metadata.yml加载封面信息
        cover_image_path = None
        try:
            metadata_config = load_metadata_config(src_dir)
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
        chapter_config = load_chapter_config(src_dir)
        chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
        
        # 为PDF创建临时章节目录
        temp_chapters_dir = build_dir / "temp-chapters-pdf"
        process_chapters_for_pdf(chapters_dir, temp_chapters_dir, chapter_files)
        
        # 如果有封面图片文件，则将其转换为base64编码
        cover_base64 = None
        if cover_image_path:
            # 获取封面图片的完整路径
            cover_image_full_path = src_dir / cover_image_path.lstrip('./')
            if cover_image_full_path.exists():
                # 将封面图片转换为base64编码
                import base64
                with open(cover_image_full_path, 'rb') as image_file:
                    cover_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                logger.info("已将封面图片转换为base64编码")
            else:
                logger.warning(f"封面图片文件不存在: {cover_image_full_path}")
        
        # 构建pandoc命令参数，先生成HTML
        input_files = [metadata_file, book_file]
        
        # 添加章节文件
        input_files.extend([temp_chapters_dir / file for file in chapter_files])
        
        html_output_path = build_dir / "katakana-dictionary.html"
        pdf_output_path = build_dir / "katakana-dictionary.pdf"
        
        logger.info("开始生成PDF文件...")
        
        # 先使用pandoc生成HTML文件
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
        if result.returncode != 0:
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
        
        logger.info(f"HTML文件生成成功: {html_output_path}")
        
        # 如果有封面图片的base64编码，则在HTML文件中插入封面
        if cover_base64:
            # 读取生成的HTML文件
            with open(html_output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 创建封面HTML内容
            cover_html_content = f"""<div style="text-align: center; page-break-after: always;">
    <img src="data:image/jpeg;base64,{cover_base64}" alt="封面" style="max-width: 100%; height: auto;" />
</div>"""
            
            # 在<body>标签后插入封面内容
            import re
            html_content = re.sub(r'(<body[^>]*>)', f'\\1\n{cover_html_content}', html_content, count=1)
            
            # 写回修改后的HTML文件
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info("已将封面图片插入到HTML文件中")
        
        # 使用wkhtmltopdf将HTML转换为PDF
        wkhtmltopdf_command = [
            wkhtmltopdf_path,
            "--enable-local-file-access",
            "--print-media-type",
            "--margin-top", "20mm",
            "--margin-bottom", "20mm",
            "--margin-left", "15mm",
            "--margin-right", "15mm",
            str(html_output_path),
            str(pdf_output_path)
        ]
        
        logger.info(f"正在执行命令生成PDF: {' '.join(wkhtmltopdf_command)}")
        
        # 执行wkhtmltopdf命令生成PDF
        pdf_result = subprocess.run(
            wkhtmltopdf_command,
            cwd=src_dir.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        # 检查返回码
        if pdf_result.returncode == 0:
            logger.info(f"PDF文件生成成功: {pdf_output_path}")
            # 清理临时目录
            if temp_chapters_dir.exists():
                shutil.rmtree(temp_chapters_dir)
                logger.info("已清理临时目录")
            
            # 可选：删除临时HTML文件
            # html_output_path.unlink()
            # logger.info("临时HTML文件已删除")
            
            return {
                "status": "success",
                "message": "PDF文件生成成功",
                "output_file": str(pdf_output_path)
            }
        else:
            error_msg = f"生成PDF文件时出错: {pdf_result.stderr}"
            logger.error(error_msg)
            # 清理临时目录
            if temp_chapters_dir.exists():
                shutil.rmtree(temp_chapters_dir)
                logger.info("已清理临时目录")
            
            return {
                "status": "error",
                "message": error_msg,
                "stdout": pdf_result.stdout,
                "stderr": pdf_result.stderr
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