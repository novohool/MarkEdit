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
    
    # 获取请求体中的内容
    body = await request.body()
    
    # 如果是JSON内容类型，格式化JSON
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        try:
            json_data = await request.json()
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # 如果不是有效的JSON，使用原始内容
            content = body.decode('utf-8')
    else:
        content = body.decode('utf-8')
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
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
    
    npm_executable =  "npm"
    if script_name == "build":
        cmd = [npm_executable, "run", "build"]
        logger.info(f"Build command set to: {npm_executable} run build")
    elif script_name == "build:epub":
        cmd = [npm_executable, "run", "build:epub"]
        logger.info(f"Build command set to: {npm_executable} run build:epub")
    elif script_name == "build:pdf":
        cmd = [npm_executable, "run", "build:pdf"]
        logger.info(f"Build command set to: {npm_executable} run build:pdf")
    
    try:
        logger.info(f"Executing build command: {' '.join(cmd)}")
        # 执行命令，传递完整的环境变量
        env = os.environ.copy()
        
        # 使用subprocess.run替代asyncio.create_subprocess_exec
        try:
            import subprocess
            # 执行命令，设置超时时间（300秒）
            result = subprocess.run(
                cmd,
                cwd=BASE_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5分钟超时
                text=True
            )
            
            logger.info(f"Build process completed with return code: {result.returncode}")
            
            # 检查返回码
            if result.returncode == 0:
                logger.info(f"Build process succeeded for script: {script_name}")
                return {
                    "status": "success",
                    "message": f"Successfully executed {script_name}",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                error_msg = f"Build process failed for script: {script_name} with return code: {result.returncode}"
                logger.error(error_msg)
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return {
                    "status": "error",
                    "message": f"Failed to execute {script_name}",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "details": {
                        "return_code": result.returncode,
                        "command": ' '.join(cmd)
                    }
                }
        except subprocess.TimeoutExpired as e:
            error_msg = f"Build process timed out for script: {script_name}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=f"Build process timed out for {script_name}")
    except FileNotFoundError as e:
        error_msg = f"File not found error during build process: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Current environment PATH: {os.environ.get('PATH', '')}")
        # 尝试查找npm的完整路径
        try:
            import subprocess
            npm_path = subprocess.run(["where", "npm"], capture_output=True, text=True, shell=True).stdout.strip()
            logger.info(f"Found npm at: {npm_path}")
        except Exception as path_error:
            logger.error(f"Error finding npm path: {path_error}")
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during build process: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        # 记录堆栈跟踪信息
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error executing script: {str(e)}")