from fastapi import APIRouter, HTTPException, Request
from pathlib import Path
import json
import os
import subprocess
import asyncio
import httpx
import logging
import platform
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入自定义的构建工具
from app.build_utils import build_epub, build_pdf


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
BASE_DIR = Path(__file__).resolve().parent.parent

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