from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
import json
import os
import subprocess
import asyncio
import httpx
import logging
import platform
import sys
import zipfile
import shutil
import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入自定义的构建工具
from app.build_utils import build_epub, build_pdf

# 导入全局变量
from app.main import startup_backup_filename


# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
project_root = os.path.dirname(current_dir)
# 将项目根目录添加到sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 创建路由器
router = APIRouter(prefix="/api/admin", tags=["admin"])

# 创建logger
logger = logging.getLogger(__name__)

# 获取项目根目录

# 获取项目根目录和src目录
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

# 定义允许管理的文件
ALLOWED_FILES = {
    "package.json": BASE_DIR / "package.json",
    "build-pdf.js": BASE_DIR / "src" / "build-pdf.js",
    "build-epub.js": BASE_DIR / "src" / "build-epub.js"
}

# 定义文本文件扩展名
TEXT_FILE_EXTENSIONS = {'.md', '.yml', '.yaml', '.css', '.html', '.js', '.json', '.txt', '.xml', '.csv'}

def is_text_file(file_path: Path) -> bool:
    """判断是否为文本文件"""
    return file_path.suffix.lower() in TEXT_FILE_EXTENSIONS

@router.get("/file/{file_name}")
async def read_admin_file(file_name: str):
    """读取管理文件的内容"""
    # 检查文件是否在允许列表中
    if file_name not in ALLOWED_FILES:
        raise HTTPException(status_code=403, detail="File access not allowed")
    
    file_path = ALLOWED_FILES[file_name]
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if file_path.is_file():
        # 检查是否为文本文件
        if is_text_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content, "type": "text", "encoding": "utf-8"}
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    return {"content": content, "type": "text", "encoding": "gbk"}
                except UnicodeDecodeError:
                    return {"content": "无法解码此文本文件", "type": "text", "encoding": "unknown"}
        else:
            # 其他二进制文件
            return {"content": "Binary file", "type": "binary"}
    else:
        raise HTTPException(status_code=400, detail="Path is not a file")

@router.post("/file/{file_name}")
async def save_admin_file(file_name: str, request: Request):
    """保存管理文件的内容"""
    # 检查文件是否在允许列表中
    if file_name not in ALLOWED_FILES:
        raise HTTPException(status_code=403, detail="File access not allowed")
    
    file_path = ALLOWED_FILES[file_name]
    
    # 读取原始文件内容（如果文件存在）
    original_content = None
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception:
            # 如果无法读取原始内容，继续执行但不保存原始内容
            pass
    
    # 获取请求体中的内容
    body = await request.body()
    
    # 如果是JSON内容类型，格式化JSON
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        try:
            json_data = await request.json()
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
            
            # 验证生成的JSON是否有效
            json.loads(content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    else:
        content = body.decode('utf-8')
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 如果是JSON文件，验证保存后的文件是否为有效的JSON
    if file_path.suffix.lower() == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
                json.loads(saved_content)  # 验证JSON格式是否正确
        except json.JSONDecodeError as e:
            # 如果保存后的文件不是有效的JSON，恢复原始内容
            if original_content is not None:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            raise HTTPException(status_code=500, detail=f"Saved file is not valid JSON, restored original content: {str(e)}")
    
    return {"message": "File saved successfully"}

@router.get("/chapters/{script_type}")
async def get_chapter_order(script_type: str):
    """获取章节顺序"""
    # 从统一配置文件加载章节顺序
    chapter_config_path = BASE_DIR / "src" / "chapter-config.json"
    
    if not chapter_config_path.exists():
        raise HTTPException(status_code=404, detail="Chapter config file not found")
    
    try:
        with open(chapter_config_path, 'r', encoding='utf-8') as f:
            chapter_config = json.load(f)
        
        # 提取章节文件名
        chapter_files = [chapter["file"] for chapter in chapter_config.get("chapters", [])]
        return {"chapters": chapter_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading chapter config: {str(e)}")

@router.get("/chapter-config")
async def get_chapter_config():
    """获取完整的章节配置信息"""
    # 从统一配置文件加载章节配置
    chapter_config_path = BASE_DIR / "src" / "chapter-config.json"
    
    if not chapter_config_path.exists():
        raise HTTPException(status_code=404, detail="Chapter config file not found")
    
    try:
        with open(chapter_config_path, 'r', encoding='utf-8') as f:
            chapter_config = json.load(f)
        
        # 返回完整的章节配置
        return chapter_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading chapter config: {str(e)}")

@router.post("/chapter-config")
async def save_chapter_config(request: Request):
    """保存章节配置信息"""
    try:
        # 获取请求体中的JSON数据
        chapter_config = await request.json()
        
        # 验证数据结构
        if "chapters" not in chapter_config:
            raise HTTPException(status_code=400, detail="Invalid chapter config format: missing 'chapters' key")
        
        # 验证每个章节对象
        for chapter in chapter_config["chapters"]:
            if "file" not in chapter or "title" not in chapter:
                raise HTTPException(status_code=400, detail="Invalid chapter config format: each chapter must have 'file' and 'title' keys")
        
        # 保存到章节配置文件
        chapter_config_path = BASE_DIR / "src" / "chapter-config.json"
        
        # 读取原始配置文件内容
        original_content = None
        if chapter_config_path.exists():
            with open(chapter_config_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        
        # 保存新配置
        with open(chapter_config_path, 'w', encoding='utf-8') as f:
            json.dump(chapter_config, f, indent=2, ensure_ascii=False)
        
        # 验证保存后的文件是否为有效的JSON
        try:
            with open(chapter_config_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
                json.loads(saved_content)  # 验证JSON格式是否正确
            
            # 如果原始内容存在且与新内容不同，记录日志
            if original_content and original_content != saved_content:
                logger.info("Chapter config file updated successfully")
        except json.JSONDecodeError as e:
            # 如果保存后的文件不是有效的JSON，恢复原始内容
            if original_content:
                with open(chapter_config_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            raise HTTPException(status_code=500, detail=f"Saved file is not valid JSON, restored original content: {str(e)}")
        
        return {"message": "Chapter config saved successfully"}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving chapter config: {str(e)}")

@router.post("/llm/process")
async def process_with_llm(request: Request):
    """使用LLM处理文本内容"""
    try:
        # 获取请求数据
        data = await request.json()
        prompt = data.get("prompt", "")
        content = data.get("content", "")
        model = data.get("model", "gpt-4o")
        
        if not prompt or not content:
            raise HTTPException(status_code=400, detail="Prompt and content are required")
        
        # 构造请求到外部LLM API
        llm_url = "https://ch.at/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": ""  # 在实际使用中需要设置API密钥
        }
        
        # 构造消息
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{prompt}\n\nContent:\n{content}"}
        ]
        
        # 构造请求数据
        llm_data = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }
        
        # 发送请求到LLM API
        async with httpx.AsyncClient() as client:
            response = await client.post(llm_url, headers=headers, json=llm_data, timeout=30.0)
            
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"LLM API error: {response.text}")
        
        # 解析响应
        result = response.json()
        processed_content = result["choices"][0]["message"]["content"]
        
        return {
            "status": "success",
            "processed_content": processed_content
        }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM API request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing with LLM: {str(e)}")

@router.post("/build/{script_name}")
async def build_book(script_name: str):
    """执行图书构建脚本"""
    logger.info(f"Starting build process for script: {script_name}")
    
    # 验证脚本名称
    allowed_scripts = ["build", "build:epub", "build:pdf"]
    if script_name not in allowed_scripts:
        logger.warning(f"Invalid script name received: {script_name}")
        raise HTTPException(status_code=400, detail="Invalid script name")
    
    # 确定源目录和构建目录
    src_dir = BASE_DIR / "src"
    build_dir = BASE_DIR / "build"
    
    try:
        # 根据脚本名称执行相应的构建过程
        if script_name == "build":
            # 构建EPUB和PDF
            logger.info("Building both EPUB and PDF")
            
            # 构建EPUB
            epub_result = build_epub(src_dir, build_dir)
            if epub_result["status"] != "success":
                logger.error(f"EPUB build failed: {epub_result['message']}")
                return {
                    "status": "error",
                    "message": f"EPUB构建失败: {epub_result['message']}",
                    "details": epub_result
                }
            
            # 构建PDF
            pdf_result = build_pdf(src_dir, build_dir)
            if pdf_result["status"] != "success":
                logger.error(f"PDF build failed: {pdf_result['message']}")
                return {
                    "status": "error",
                    "message": f"PDF构建失败: {pdf_result['message']}",
                    "details": pdf_result
                }
            
            logger.info("Both EPUB and PDF build completed successfully")
            return {
                "status": "success",
                "message": "EPUB和PDF文件生成成功",
                "details": {
                    "epub": epub_result,
                    "pdf": pdf_result
                }
            }
        elif script_name == "build:epub":
            # 只构建EPUB
            logger.info("Building EPUB")
            result = build_epub(src_dir, build_dir)
            if result["status"] == "success":
                logger.info("EPUB build completed successfully")
                return {
                    "status": "success",
                    "message": "EPUB文件生成成功",
                    "details": result
                }
            else:
                logger.error(f"EPUB build failed: {result['message']}")
                return {
                    "status": "error",
                    "message": f"EPUB构建失败: {result['message']}",
                    "details": result
                }
        elif script_name == "build:pdf":
            # 只构建PDF
            logger.info("Building PDF")
            result = build_pdf(src_dir, build_dir)
            if result["status"] == "success":
                logger.info("PDF build completed successfully")
                return {
                    "status": "success",
                    "message": "PDF文件生成成功",
                    "details": result
                }
            else:
                logger.error(f"PDF build failed: {result['message']}")
                return {
                    "status": "error",
                    "message": f"PDF构建失败: {result['message']}",
                    "details": result
                }
    except Exception as e:
        error_msg = f"Unexpected error during build process: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        # 记录堆栈跟踪信息
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"构建过程中出现未预期的错误: {str(e)}")

@router.post("/upload-src")
async def upload_src(file: UploadFile = File(...)):
    """上传src目录的zip包"""
    try:
        # 检查文件类型
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="只允许上传.zip文件")
        
        # 创建临时文件
        temp_file_path = BASE_DIR / f"temp_upload_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        # 保存上传的文件
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 验证zip文件
        try:
            with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                # 检查zip文件是否有效
                zip_ref.testzip()
        except zipfile.BadZipFile:
            # 删除临时文件
            temp_file_path.unlink()
            raise HTTPException(status_code=400, detail="上传的文件不是有效的zip文件")
        
        # 创建临时解压目录
        temp_extract_dir = BASE_DIR / f"temp_extract_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_extract_dir.mkdir(exist_ok=True)
        
        # 解压到临时目录进行校验
        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                # 处理解压路径
                if member.filename.startswith('src/'):
                    # 移除路径前缀
                    target_path = temp_extract_dir / member.filename[4:]
                else:
                    # 如果没有src/前缀，直接解压到临时目录
                    target_path = temp_extract_dir / member.filename
                
                # 处理目录
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    # 确保父目录存在
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    # 解压文件
                    with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
        
        # 校验必要文件是否存在
        required_files = [
            "chapter-config.json",
            "metadata.yml",
            "book.md"
        ]
        
        missing_files = []
        for required_file in required_files:
            if not (temp_extract_dir / required_file).exists():
                missing_files.append(required_file)
        
        # 如果有缺失的文件，删除临时文件和目录，返回错误信息
        if missing_files:
            # 删除临时文件和目录
            temp_file_path.unlink()
            shutil.rmtree(temp_extract_dir)
            
            raise HTTPException(
                status_code=400,
                detail=f"上传的zip包格式不正确，缺少以下必要文件: {', '.join(missing_files)}。必须包含: {', '.join(required_files)}"
            )
        
        # 校验通过，备份当前src目录
        backup_src_directory()
        
        # 删除当前src目录
        if SRC_DIR.exists():
            shutil.rmtree(SRC_DIR)
        
        # 将临时解压目录重命名为src目录
        temp_src_dir = temp_extract_dir / "src"
        if temp_src_dir.exists():
            # 如果解压后有src目录，直接移动
            shutil.move(str(temp_src_dir), str(SRC_DIR))
        else:
            # 如果解压后没有src目录，将临时目录重命名为src
            shutil.move(str(temp_extract_dir), str(SRC_DIR))
        
        # 删除临时文件
        temp_file_path.unlink()
        
        logger.info("Src目录上传并替换成功")
        return {"message": "Src目录上传并替换成功"}
    except Exception as e:
        logger.error(f"上传src目录时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传src目录时出错: {str(e)}")

@router.get("/download-src")
async def download_src():
    """下载src目录的zip包"""
    try:
        logger.info("开始下载src目录")
        # 创建备份
        backup_path = backup_src_directory()
        logger.info(f"备份文件路径: {backup_path}")
        
        # 返回文件下载
        response = FileResponse(
            path=backup_path,
            filename=backup_path.name,
            media_type='application/zip'
        )
        logger.info("已创建FileResponse")
        return response
    except Exception as e:
        logger.error(f"下载src目录时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载src目录时出错: {str(e)}")

@router.post("/reset-src")
async def reset_src():
    """重置src目录到启动时备份"""
    try:
        logger.info("开始重置src目录")
        # 查找启动时备份文件
        backup_dir = BASE_DIR / "backups"
        logger.info(f"备份目录路径: {backup_dir}")
        if not backup_dir.exists():
            logger.error("备份目录不存在")
            raise HTTPException(status_code=404, detail="备份目录不存在")
        
        # 使用全局变量获取启动备份文件名
        from app.main import startup_backup_filename
        if not startup_backup_filename:
            logger.error("启动备份文件记录不存在")
            raise HTTPException(status_code=404, detail="启动备份文件记录不存在")
        
        startup_backup_path = backup_dir / startup_backup_filename
        logger.info(f"启动备份文件路径: {startup_backup_path}")
        if not startup_backup_path.exists():
            logger.error("启动备份文件不存在")
            raise HTTPException(status_code=404, detail="启动备份文件不存在")
        
        # 删除当前src目录
        if SRC_DIR.exists():
            logger.info("删除当前src目录")
            shutil.rmtree(SRC_DIR)
        
        # 解压启动备份文件到src目录
        logger.info("开始解压启动备份文件")
        with zipfile.ZipFile(startup_backup_path, 'r') as zip_ref:
            # 先创建src目录
            SRC_DIR.mkdir(exist_ok=True)
            # 解压到src目录
            for member in zip_ref.infolist():
                # 处理路径，确保文件解压到src目录中
                if member.filename.startswith('src/'):
                    # 移除路径前缀
                    target_path = SRC_DIR / member.filename[4:]
                else:
                    # 如果没有src/前缀，直接解压到src目录
                    target_path = SRC_DIR / member.filename
                
                # 处理目录
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    # 确保父目录存在
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    # 解压文件
                    with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
        logger.info("启动备份文件解压完成")
        
        logger.info("Src目录重置成功")
        return {"message": "Src目录重置成功"}
    except Exception as e:
        logger.error(f"重置src目录时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重置src目录时出错: {str(e)}")

def backup_src_directory():
    """备份src目录到zip文件"""
    try:
        # 创建备份目录
        backup_dir = BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"src_backup_{timestamp}.zip"
        backup_path = backup_dir / backup_filename
        
        # 创建zip文件
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历src目录中的所有文件和子目录
            for root, dirs, files in os.walk(SRC_DIR):
                for file in files:
                    file_path = Path(root) / file
                    # 计算相对路径
                    arcname = file_path.relative_to(BASE_DIR)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Src目录备份成功: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份src目录时出错: {str(e)}")
        raise

@router.get("/backups")
async def list_backup_files():
    """获取备份文件列表"""
    try:
        # 定义备份目录
        backup_dir = BASE_DIR / "backups"
        
        # 检查备份目录是否存在
        if not backup_dir.exists():
            return {"files": []}
        
        # 获取启动时备份文件名
        startup_backup_filename = None
        startup_backup_file = backup_dir / "startup_backup.txt"
        if startup_backup_file.exists():
            with open(startup_backup_file, 'r') as f:
                startup_backup_filename = f.read().strip()
        
        # 获取所有.zip文件
        import glob
        zip_files = list(backup_dir.glob("*.zip"))
        
        # 提取文件信息
        files_info = []
        for file_path in zip_files:
            stat = file_path.stat()
            is_startup_backup = (file_path.name == startup_backup_filename) if startup_backup_filename else False
            files_info.append({
                "name": file_path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_startup_backup": is_startup_backup
            })
        
        # 按修改时间倒序排列
        files_info.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files_info}
    except Exception as e:
        logger.error(f"获取备份文件列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取备份文件列表时出错: {str(e)}")

@router.get("/backups/{filename}/download")
async def download_backup_file(filename: str):
    """下载指定的备份文件"""
    try:
        # 验证文件名是否安全
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        # 确保文件名以.zip结尾
        if not filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="只能下载.zip文件")
        
        # 构造文件路径
        backup_dir = BASE_DIR / "backups"
        file_path = backup_dir / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查是否为文件（而不是目录）
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="指定路径不是文件")
        
        # 返回文件下载
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/zip'
        )
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"下载备份文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载备份文件时出错: {str(e)}")

@router.delete("/backups/{filename}")
async def delete_backup_file(filename: str):
    """删除指定的备份文件"""
    try:
        # 验证文件名是否安全
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        # 确保文件名以.zip结尾
        if not filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="只能删除.zip文件")
        
        # 构造文件路径
        backup_dir = BASE_DIR / "backups"
        file_path = backup_dir / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查是否为文件（而不是目录）
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="指定路径不是文件")
        
        # 检查是否为启动时备份文件
        startup_backup_file = backup_dir / "startup_backup.txt"
        if startup_backup_file.exists():
            with open(startup_backup_file, 'r') as f:
                startup_backup_filename = f.read().strip()
            if filename == startup_backup_filename:
                raise HTTPException(status_code=403, detail="不能删除启动时备份文件")
        
        # 删除文件
        file_path.unlink()
        
        logger.info(f"备份文件已删除: {filename}")
        return {"message": f"备份文件 {filename} 已删除"}
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"删除备份文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除备份文件时出错: {str(e)}")