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
import platform
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
    
    def _detect_and_set_fonts(self) -> List[str]:
        """检测系统字体并设置字体变量"""
        font_variables = []
        
        # 检测操作系统
        is_windows = platform.system() == "Windows"
        
        # 优先字体列表
        if is_windows:
            # Windows默认字体优先级
            main_fonts = ["Times New Roman", "Liberation Serif", "Computer Modern Roman"]
            sans_fonts = ["Arial", "Liberation Sans", "Computer Modern Sans"]
            mono_fonts = ["Consolas", "Courier New", "Liberation Mono", "Computer Modern Typewriter"]
            cjk_fonts = ["Microsoft YaHei", "SimSun", "WenQuanYi Zen Hei", "Noto Sans CJK SC"]
        else:
            # Linux/Unix默认字体优先级
            main_fonts = ["Liberation Serif", "Times New Roman", "Computer Modern Roman"]
            sans_fonts = ["Liberation Sans", "Arial", "Computer Modern Sans"]
            mono_fonts = ["Liberation Mono", "Consolas", "Courier New", "Computer Modern Typewriter"]
            cjk_fonts = ["WenQuanYi Zen Hei", "Microsoft YaHei", "Noto Sans CJK SC"]
        
        # 检查并设置主字体
        main_font = self._find_available_font(main_fonts)
        if main_font:
            font_variables.extend(["--variable", f"mainfont:{main_font}"])
            logger.info(f"使用主字体: {main_font}")
        
        # 检查并设置无衬线字体
        sans_font = self._find_available_font(sans_fonts)
        if sans_font:
            font_variables.extend(["--variable", f"sansfont:{sans_font}"])
            logger.info(f"使用无衬线字体: {sans_font}")
        
        # 检查并设置等宽字体
        mono_font = self._find_available_font(mono_fonts)
        if mono_font:
            font_variables.extend(["--variable", f"monofont:{mono_font}"])
            logger.info(f"使用等宽字体: {mono_font}")
        
        # 检查并设置CJK字体
        cjk_font = self._find_available_font(cjk_fonts)
        if cjk_font:
            font_variables.extend(["--variable", f"CJKmainfont:{cjk_font}"])
            logger.info(f"使用CJK字体: {cjk_font}")
        
        return font_variables
    
    def _find_available_font(self, font_list: List[str]) -> str:
        """从字体列表中找到第一个可用的字体"""
        # 在Windows系统下，为了避免编码问题，直接使用常见字体
        if platform.system() == "Windows":
            return font_list[0] if font_list else "Computer Modern Roman"
        
        # 非Windows系统下使用原有的检查逻辑
        for font in font_list:
            if self._is_font_available(font):
                return font
        return font_list[0] if font_list else "Computer Modern Roman"  # 默认后备字体
    
    def _is_font_available(self, font_name: str) -> bool:
        """检查字体是否可用"""
        try:
            # 检测操作系统并使用相应的字体检查方法
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                # Windows系统使用PowerShell检查字体
                ps_command = f'Get-ChildItem "$env:SystemRoot\\Fonts" | Where-Object {{$_.Name -like "*{font_name}*"}}'
                result = subprocess.run(
                    ["powershell", "-Command", ps_command],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10
                )
                
                if result.returncode == 0:
                    # 如果有输出说明找到了字体文件
                    return bool(result.stdout.strip())
                else:
                    # PowerShell检查失败，假设字体可用
                    logger.warning(f"PowerShell字体检查失败 {font_name}，假设可用")
                    return True
            else:
                # Linux/Unix系统使用fc-list
                result = subprocess.run(
                    ["fc-list", ":", "family"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10
                )
                
                if result.returncode == 0:
                    # 检查字体名称是否在输出中
                    font_families = result.stdout.lower()
                    return font_name.lower() in font_families
                else:
                    # 如果fc-list不可用，假设字体存在
                    logger.warning(f"无法检查字体 {font_name} 的可用性，假设可用")
                    return True
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"字体检查失败 {font_name}: {e}，假设可用")
            return True
        except Exception as e:
            logger.warning(f"字体检查出现异常 {font_name}: {e}，假设可用")
            return True
    
    def _generate_filename_from_title(self, title: str, extension: str) -> str:
        """从标题生成安全的文件名"""
        import re
        
        # 先去掉两端空格
        safe_title = title.strip()
        
        # 替换不安全的字符
        # 保留中文、日文、英文字母、数字、连字符和下划线
        safe_title = re.sub(r'[<>:"/\\|?*]', '-', safe_title)
        
        # 将多个连续的空格或特殊字符替换为单个连字符
        safe_title = re.sub(r'[\s\-]+', '-', safe_title)
        
        # 删除开头和结尾的连字符
        safe_title = safe_title.strip('-')
        
        # 如果标题为空或太短，使用默认名称
        if not safe_title or len(safe_title) < 2:
            safe_title = 'untitled'
        
        # 限制文件名长度（不包括扩展名）
        if len(safe_title) > 100:
            safe_title = safe_title[:100]
        
        return f"{safe_title}.{extension}"
    
    def load_metadata_config(self, src_dir: Path) -> Dict[str, Any]:
        """从 metadata.yml 文件加载元数据配置
        支持处理包含 YAML frontmatter 的文件格式
        """
        metadata_path = src_dir / "metadata.yml"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否以 YAML frontmatter 格式开始（以 --- 开始）
        if content.strip().startswith('---'):
            # 解析 YAML frontmatter 格式
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # 取第二部分（第一部分是空的，第二部分是 YAML，第三部分是其余内容）
                yaml_content = parts[1].strip()
                try:
                    return yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    logger.warning(f"解析 YAML frontmatter 失败: {e}, 尝试作为普通 YAML 文件处理")
                    # 如果 frontmatter 解析失败，尝试直接解析整个文件
                    return yaml.safe_load(content)
            else:
                logger.warning(f"YAML frontmatter 格式不正确，尝试作为普通 YAML 文件处理")
                return yaml.safe_load(content)
        else:
            # 普通的 YAML 文件
            return yaml.safe_load(content)
    
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
        """优化SVG文件以提高epub兼容性"""
        for file in build_illustrations_dir.iterdir():
            if file.suffix == '.svg':
                # 使用SVG优化方案
                logger.info(f"使用SVG优化方案: {file.name}")
                # 读取SVG内容
                with open(file, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # 优化SVG内容
                optimized_svg_content = self.optimize_svg_for_epub(svg_content)
                
                # 写入优化后的SVG内容
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(optimized_svg_content)
                
                logger.info(f"已优化SVG文件: {file.name}")
    
    def convert_svg_to_png(self, svg_file_path: Path, output_dir: Path = None, width: int = 1000, height: int = 800) -> Path:
        """使用Inkscape将SVG文件转换为PNG格式
        
        Args:
            svg_file_path: SVG文件路径
            output_dir: 输出目录，如果为None则使用SVG文件所在目录
            width: PNG图片宽度，默认1000像素
            height: PNG图片高度，默认800像素
            
        Returns:
            转换后的PNG文件路径
        """
        if output_dir is None:
            output_dir = svg_file_path.parent
            
        # 生成PNG文件名
        png_filename = svg_file_path.stem + '.png'
        png_file_path = output_dir / png_filename
        
        try:
            # 构建Inkscape命令
            inkscape_command = [
                "inkscape",
                "--export-type=png",
                f"--export-width={width}",
                f"--export-height={height}",
                f"--export-filename={str(png_file_path)}",
                str(svg_file_path)
            ]
            
            logger.info(f"正在将SVG转换为PNG: {svg_file_path.name} -> {png_filename}")
            logger.debug(f"执行命令: {' '.join(inkscape_command)}")
            
            # 执行Inkscape命令
            result = subprocess.run(
                inkscape_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,  # 1分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            if result.returncode == 0:
                logger.info(f"SVG转PNG成功: {png_filename}")
                return png_file_path
            else:
                error_msg = f"SVG转PNG失败: {result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except FileNotFoundError:
            error_msg = "Inkscape工具未找到，请确保已安装Inkscape"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = f"SVG转PNG超时: {svg_file_path.name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"SVG转PNG时发生错误: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def convert_svgs_to_png_for_pdf(self, build_illustrations_dir: Path):
        """将illustrations目录中的所有SVG文件转换为PNG格式以用于PDF生成"""
        svg_files = [file for file in build_illustrations_dir.iterdir() if file.suffix.lower() == '.svg']
        
        if not svg_files:
            logger.info("illustrations目录中没有找到SVG文件")
            return
            
        logger.info(f"开始转换{len(svg_files)}个SVG文件为PNG格式...")
        
        for svg_file in svg_files:
            try:
                # 转换SVG为PNG
                png_file_path = self.convert_svg_to_png(svg_file, build_illustrations_dir)
                logger.info(f"已转换: {svg_file.name} -> {png_file_path.name}")
            except Exception as e:
                logger.warning(f"转换SVG文件失败 {svg_file.name}: {str(e)}")
                # 转换失败时继续处理其他文件
                continue
                
        logger.info("SVG到PNG转换完成")
    
    def optimize_svgs_for_pdf(self, build_illustrations_dir: Path):
        """优化SVG文件以用于PDF生成，修复字体问题但保持SVG格式"""
        for file in build_illustrations_dir.iterdir():
            if file.suffix == '.svg':
                # 修复SVG字体问题，但保持SVG格式
                # XeTeX可以直接处理优化后的SVG文件
                logger.info(f"为PDF优化SVG文件（保持SVG格式）: {file.name}")
                # 读取SVG内容
                with open(file, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # 修复SVG字体问题
                optimized_svg_content = self.fix_svg_fonts_for_pdf(svg_content)
                
                # 写入优化后的SVG内容
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(optimized_svg_content)
                
                logger.info(f"已为PDF优化SVG文件: {file.name}")
    


    
    def fix_svg_fonts_for_pdf(self, svg_content: str) -> str:
        """修复SVG文件中的字体设置以支持PDF中的中文显示"""
        import re
        
        # 检测系统以确定合适的中文字体
        is_windows = platform.system() == "Windows"
        
        # 根据系统选择合适的中文字体
        if is_windows:
            chinese_font = "Microsoft YaHei"
            japanese_font = "Microsoft YaHei"
        else:
            chinese_font = "WenQuanYi Zen Hei"
            japanese_font = "WenQuanYi Zen Hei"
        
        # 替换CSS样式中的字体定义
        def replace_font_in_style(match):
            style_content = match.group(0)
            # 将 sans-serif 替换为支持中文的字体
            style_content = re.sub(
                r'font:\s*([^;]*?)\s*sans-serif',
                rf'font: \1 "{chinese_font}", sans-serif',
                style_content
            )
            # 处理单独的 font-family 属性
            style_content = re.sub(
                r'font-family:\s*sans-serif',
                f'font-family: "{chinese_font}", sans-serif',
                style_content
            )
            return style_content
        
        # 处理style标签内的字体
        svg_content = re.sub(r'<style[^>]*>[\s\S]*?</style>', replace_font_in_style, svg_content)
        
        # 处理内联样式中的字体
        def replace_inline_font(match):
            style_attr = match.group(1)
            # 替换内联样式中的sans-serif
            style_attr = re.sub(
                r'font:\s*([^;]*?)\s*sans-serif',
                rf'font: \1 "{chinese_font}", sans-serif',
                style_attr
            )
            style_attr = re.sub(
                r'font-family:\s*sans-serif',
                f'font-family: "{chinese_font}", sans-serif',
                style_attr
            )
            return f'style="{style_attr}"'
        
        # 处理元素的内联style属性
        svg_content = re.sub(r'style="([^"]*?)"', replace_inline_font, svg_content)
        
        # 确保SVG有正确的xmlns属性
        if 'xmlns="http://www.w3.org/2000/svg"' not in svg_content:
            svg_content = svg_content.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
        
        logger.info(f"已修复SVG字体，使用字体: {chinese_font}")
        return svg_content
    
    def process_chapters_for_epub(self, chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
        """复制并修改章节文件，调整图片路径以适应EPUB"""
        if not temp_chapters_dir.exists():
            temp_chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制并修改章节文件，调整图片路径
        for file_name in chapter_files:
            # 处理文件路径，如果文件名包含chapters/前缀，需要相对于src_dir处理
            if file_name.startswith('chapters/'):
                # 去掉chapters/前缀，因为chapters_dir已经指向chapters目录
                relative_file_name = file_name[9:]  # 去掉'chapters/'前缀
                src_path = chapters_dir / relative_file_name
                dest_path = temp_chapters_dir / relative_file_name
            else:
                src_path = chapters_dir / file_name
                dest_path = temp_chapters_dir / file_name
            
            # 读取原始章节文件
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修改图片路径，将 "../illustrations/" 和各种 "/user-illustrations/" 格式替换为 "illustrations/"
            content = content.replace('../illustrations/', 'illustrations/')
            # 处理旧格式的用户插图路径
            content = content.replace('/user-illustrations/', 'illustrations/')
            # 处理新格式的用户插图路径（包含用户名）
            import re
            # 匹配 /user-illustrations/username/filename 格式并替换为 illustrations/filename
            content = re.sub(r'/user-illustrations/[^/]+/([^)]+)', r'illustrations/\1', content)
            
            # 写入修改后的章节文件到临时目录
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已处理章节文件: {file_name}")
    
    def process_chapters_for_pdf(self, chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
        """复制并修改章节文件，调整图片路径以适应PDF，并将SVG引用转换为PNG"""
        if not temp_chapters_dir.exists():
            temp_chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制并修改章节文件，调整图片路径
        for file_name in chapter_files:
            # 处理文件路径，如果文件名包含chapters/前缀，需要相对于src_dir处理
            if file_name.startswith('chapters/'):
                # 去掉chapters/前缀，因为chapters_dir已经指向chapters目录
                relative_file_name = file_name[9:]  # 去掉'chapters/'前缀
                src_path = chapters_dir / relative_file_name
                dest_path = temp_chapters_dir / relative_file_name
            else:
                src_path = chapters_dir / file_name
                dest_path = temp_chapters_dir / file_name
            
            # 读取原始章节文件
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修改图片路径，将 "../illustrations/" 和各种 "/user-illustrations/" 格式替换为 "./illustrations/"
            content = content.replace('../illustrations/', './illustrations/')
            # 处理旧格式的用户插图路径
            content = content.replace('/user-illustrations/', './illustrations/')
            # 处理新格式的用户插图路径（包含用户名）
            import re
            # 匹配 /user-illustrations/username/filename 格式并替换为 ./illustrations/filename
            content = re.sub(r'/user-illustrations/[^/]+/([^)]+)', r'./illustrations/\1', content)
            
            # 将Markdown中的SVG图片引用转换为PNG引用
            content = self.convert_svg_references_to_png(content)
            
            # 写入修改后的章节文件到临时目录
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已处理章节文件: {file_name}")
    
    def convert_svg_references_to_png(self, markdown_content: str) -> str:
        """将Markdown内容中的SVG图片引用转换为PNG引用
        
        支持的格式:
        - ![alt text](path/to/image.svg)
        - ![alt text](path/to/image.svg "title")
        """
        import re
        
        # 匹配Markdown图片语法中的SVG文件
        # 模式: ![alt text](path.svg) 或 ![alt text](path.svg "title")
        svg_pattern = r'(!\[[^\]]*\])\(([^\)]*\.svg)([^\)]*)\)'
        
        def replace_svg_with_png(match):
            alt_text = match.group(1)  # ![alt text]
            svg_path = match.group(2)  # path.svg
            additional_params = match.group(3)  # 可能包含的标题或其他参数
            
            # 将.svg扩展名替换为.png
            png_path = svg_path.replace('.svg', '.png')
            
            # 构建新的Markdown图片引用
            new_reference = f"{alt_text}({png_path}{additional_params})"
            
            logger.debug(f"SVG引用转换: {svg_path} -> {png_path}")
            return new_reference
        
        # 执行替换
        converted_content = re.sub(svg_pattern, replace_svg_with_png, markdown_content)
        
        return converted_content
    
    def process_chapters_for_html(self, chapters_dir: Path, temp_chapters_dir: Path, chapter_files: List[str]):
        """复制并修改章节文件，调整图片路径以适应HTML"""
        if not temp_chapters_dir.exists():
            temp_chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制并修改章节文件，调整图片路径
        for file_name in chapter_files:
            # 处理文件路径，如果文件名包含chapters/前缀，需要相对于src_dir处理
            if file_name.startswith('chapters/'):
                # 去掉chapters/前缀，因为chapters_dir已经指向chapters目录
                relative_file_name = file_name[9:]  # 去掉'chapters/'前缀
                src_path = chapters_dir / relative_file_name
                dest_path = temp_chapters_dir / relative_file_name
            else:
                src_path = chapters_dir / file_name
                dest_path = temp_chapters_dir / file_name
            
            # 读取原始章节文件
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修改图片路径，将 "../illustrations/" 和各种 "/user-illustrations/" 格式替换为 "./illustrations/"
            content = content.replace('../illustrations/', './illustrations/')
            # 处理旧格式的用户插图路径
            content = content.replace('/user-illustrations/', './illustrations/')
            # 处理新格式的用户插图路径（包含用户名）
            import re
            # 匹配 /user-illustrations/username/filename 格式并替换为 ./illustrations/filename
            content = re.sub(r'/user-illustrations/[^/]+/([^)]+)', r'./illustrations/\1', content)
            
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
            
            # 从metadata.yml加载元数据配置
            metadata_config = self.load_metadata_config(src_dir)
            title = metadata_config.get('title', 'untitled')
            
            # 生成EPUB文件名，将标题转换为合适的文件名
            epub_name = self._generate_filename_from_title(title, 'epub')
            
            # 从统一配置文件加载章节顺序
            chapter_config = self.load_chapter_config(src_dir)
            chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
            
            # 为EPUB创建临时章节目录
            temp_chapters_dir = build_dir / "temp-chapters-epub"
            self.process_chapters_for_epub(chapters_dir, temp_chapters_dir, chapter_files)
            
            # 构建pandoc命令参数
            input_files = [metadata_file, book_file]
            
            # 添加章节文件，处理包含chapters/前缀的文件名
            for file_name in chapter_files:
                if file_name.startswith('chapters/'):
                    # 去掉chapters/前缀，因为temp_chapters_dir已经在临时目录下
                    relative_file_name = file_name[9:]  # 去掉'chapters/'前缀
                    input_files.append(temp_chapters_dir / relative_file_name)
                else:
                    input_files.append(temp_chapters_dir / file_name)
            
            epub_output_path = build_dir / epub_name
            
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
                encoding='utf-8',
                errors='replace',  # 遇到编码错误时用替换字符处理
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
            
            # 将SVG文件转换为PNG格式（用于XeTeX PDF生成）
            # 这是新增的功能：在使用XeTeX生成PDF时，先将SVG转换为PNG
            try:
                self.convert_svgs_to_png_for_pdf(build_illustrations_dir)
                logger.info("SVG文件已转换为PNG格式，用于PDF生成")
            except Exception as e:
                logger.warning(f"SVG转PNG时发生错误，将继续使用原有的SVG优化方案: {str(e)}")
                # 如果SVG转PNG失败，回退到原有的SVG优化方案
                self.optimize_svgs_for_pdf(build_illustrations_dir)
            
            # 从metadata.yml加载元数据配置
            metadata_config = self.load_metadata_config(src_dir)
            title = metadata_config.get('title', 'untitled')
            
            # 生成PDF文件名
            pdf_name = self._generate_filename_from_title(title, 'pdf')
            
            # 从统一配置文件加载章节顺序
            chapter_config = self.load_chapter_config(src_dir)
            chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
            
            # 为PDF创建临时章节目录
            temp_chapters_dir = build_dir / "temp-chapters-pdf"
            self.process_chapters_for_pdf(chapters_dir, temp_chapters_dir, chapter_files)
            
            # 构建pandoc命令参数
            input_files = [metadata_file, book_file]
            
            # 添加章节文件，处理包含chapters/前缀的文件名
            for file_name in chapter_files:
                if file_name.startswith('chapters/'):
                    # 去掉chapters/前缀，因为temp_chapters_dir已经在临时目录下
                    relative_file_name = file_name[9:]  # 去掉'chapters/'前缀
                    input_files.append(temp_chapters_dir / relative_file_name)
                else:
                    input_files.append(temp_chapters_dir / file_name)
            
            pdf_output_path = build_dir / pdf_name
            
            logger.info("开始生成PDF文件...")
            
            # 使用pandoc生成PDF文件，使用自定义LaTeX模板支持中文日文
            latex_template = src_dir / "templates" / "latex-template.tex"
            
            # 检测系统字体并设置字体变量
            font_variables = self._detect_and_set_fonts()
            
            pandoc_args = [
                "pandoc"
            ] + [str(f) for f in input_files] + [
                "-o", str(pdf_output_path),
                "--from", "markdown",
                "--to", "pdf",
                "--toc",
                "--toc-depth=2",
                "--pdf-engine=xelatex",
                f"--template={latex_template}",
                "--variable=documentclass:article",
                "--variable=fontsize:12pt",
                "--variable=linestretch:1.5",
                f"--resource-path={build_dir}"
            ]
            
            # 添加字体变量
            pandoc_args.extend(font_variables)
            
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
                encoding='utf-8',
                errors='replace',  # 遇到编码错误时用替换字符处理
                timeout=600,  # 10分钟超时（PDF生成可能需要更长时间）
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
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
                    "message": "Pandoc PDF文件生成成功",
                    "output_file": str(pdf_output_path),
                    "file_size": pdf_output_path.stat().st_size,
                    "method": "pandoc"
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
            
            # 从metadata.yml加载元数据配置生成文件名
            metadata_config = self.load_metadata_config(src_dir)
            title = metadata_config.get('title', 'untitled')
            
            # 生成HTML文件名
            html_name = self._generate_filename_from_title(title, 'html')
            
            # 为HTML创建临时章节目录
            temp_chapters_dir = build_dir / "temp-chapters-html"
            self.process_chapters_for_html(chapters_dir, temp_chapters_dir, chapter_files)
            
            # 构建pandoc命令参数
            input_files = [metadata_file, book_file]
            
            # 添加章节文件，处理包含chapters/前缀的文件名
            for file_name in chapter_files:
                if file_name.startswith('chapters/'):
                    # 去掉chapters/前缀，因为temp_chapters_dir已经在临时目录下
                    relative_file_name = file_name[9:]  # 去掉'chapters/'前缀
                    input_files.append(temp_chapters_dir / relative_file_name)
                else:
                    input_files.append(temp_chapters_dir / file_name)
            
            html_output_path = build_dir / html_name
            
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
                encoding='utf-8',
                errors='replace',  # 遇到编码错误时用替换字符处理
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
    
    async def build_pdf_with_wkhtmltopdf(self, src_dir: Path = None, build_dir: Path = None) -> Dict[str, Any]:
        """使用wkhtmltopdf将HTML转换为PDF"""
        if src_dir is None:
            src_dir = self.src_dir
        if build_dir is None:
            build_dir = self.build_dir
            
        try:
            # 首先生成HTML文件
            html_result = await self.build_html(src_dir, build_dir)
            if html_result["status"] != "success":
                return html_result
            
            # 从metadata.yml加载元数据配置生成文件名
            metadata_config = self.load_metadata_config(src_dir)
            title = metadata_config.get('title', 'untitled')
            
            # 生成文件名
            html_name = self._generate_filename_from_title(title, 'html')
            pdf_name = self._generate_filename_from_title(title + '-wkhtmltopdf', 'pdf')
            
            # HTML文件路径
            html_output_path = build_dir / html_name
            pdf_output_path = build_dir / pdf_name
            
            if not html_output_path.exists():
                error_msg = "HTML文件不存在，无法转换为PDF"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            logger.info("开始使用wkhtmltopdf生成PDF文件...")
            
            # 检测wkhtmltopdf路径
            wkhtmltopdf_path = self._find_wkhtmltopdf_path()
            if not wkhtmltopdf_path:
                error_msg = "wkhtmltopdf未找到，请确保已安装wkhtmltopdf"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # 使用wkhtmltopdf将HTML转换为PDF
            wkhtmltopdf_command = [
                wkhtmltopdf_path,
                "--enable-local-file-access",
                "--print-media-type",
                "--margin-top", "20mm",
                "--margin-bottom", "20mm",
                "--margin-left", "15mm",
                "--margin-right", "15mm",
                "--encoding", "UTF-8",
                "--disable-smart-shrinking",
                str(html_output_path),
                str(pdf_output_path)
            ]
            
            logger.info(f"正在执行wkhtmltopdf命令: {' '.join(wkhtmltopdf_command)}")
            
            # 执行wkhtmltopdf命令
            result = subprocess.run(
                wkhtmltopdf_command,
                cwd=src_dir.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,  # 5分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # 检查返回码
            if result.returncode == 0 and pdf_output_path.exists():
                logger.info(f"wkhtmltopdf PDF文件生成成功: {pdf_output_path}")
                return {
                    "status": "success",
                    "message": "wkhtmltopdf PDF文件生成成功",
                    "output_file": str(pdf_output_path),
                    "file_size": pdf_output_path.stat().st_size,
                    "method": "wkhtmltopdf"
                }
            else:
                error_msg = f"wkhtmltopdf生成PDF文件时出错: {result.stderr}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired as e:
            error_msg = f"wkhtmltopdf生成PDF文件时超时: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"wkhtmltopdf生成PDF文件时出现未预期的错误: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": error_msg
            }
    
    def _find_wkhtmltopdf_path(self) -> str:
        """查找wkhtmltopdf可执行文件路径"""
        # 常见的wkhtmltopdf安装路径
        possible_paths = [
            "wkhtmltopdf",  # 系统PATH中
            "/usr/bin/wkhtmltopdf",  # Linux常见路径
            "/usr/local/bin/wkhtmltopdf",  # Linux常见路径
            "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe",  # Windows常见路径
            "C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"  # Windows 32位路径
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
                if result.returncode == 0:
                    logger.info(f"找到wkhtmltopdf: {path}")
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        logger.warning("未找到wkhtmltopdf可执行文件")
        return None