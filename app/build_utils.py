import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging

# 创建logger
logger = logging.getLogger(__name__)

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
        
        # 从统一配置文件加载章节顺序
        chapter_config = load_chapter_config(src_dir)
        chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
        
        # 为EPUB创建临时章节目录
        temp_chapters_dir = build_dir / "temp-chapters"
        process_chapters_for_epub(chapters_dir, temp_chapters_dir, chapter_files)
        
        # 构建pandoc命令参数
        input_files = [metadata_file, book_file] + [temp_chapters_dir / file for file in chapter_files]
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
        
        # 从统一配置文件加载章节顺序
        chapter_config = load_chapter_config(src_dir)
        chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
        
        # 为PDF创建临时章节目录
        temp_chapters_dir = build_dir / "temp-chapters-pdf"
        process_chapters_for_pdf(chapters_dir, temp_chapters_dir, chapter_files)
        
        # 构建pandoc命令参数，先生成HTML
        input_files = [metadata_file, book_file] + [temp_chapters_dir / file for file in chapter_files]
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