from fastapi import APIRouter, HTTPException, Request
from pathlib import Path
import json
import os
import subprocess
import asyncio
import httpx

# 创建路由器
router = APIRouter(prefix="/api/admin", tags=["admin"])

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
    # 确定脚本文件
    if script_type == "pdf":
        file_name = "build-pdf.js"
    elif script_type == "epub":
        file_name = "build-epub.js"
    else:
        raise HTTPException(status_code=400, detail="Invalid script type")
    
    if file_name not in ALLOWED_FILES:
        raise HTTPException(status_code=403, detail="File access not allowed")
    
    file_path = ALLOWED_FILES[file_name]
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取章节顺序
    import re
    regex = r'const\s+chapterFiles\s*=\s*\[([\s\S]*?)\];'
    match = re.search(regex, content)
    
    if match:
        files_content = match.group(1)
        file_matches = re.findall(r"'([^']+)'", files_content)
        return {"chapters": file_matches}
    else:
        return {"chapters": []}

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
    # 验证脚本名称
    allowed_scripts = ["build", "build:epub", "build:pdf"]
    if script_name not in allowed_scripts:
        raise HTTPException(status_code=400, detail="Invalid script name")
    
    # 构建命令
    if script_name == "build":
        cmd = ["npm", "run", "build"]
    elif script_name == "build:epub":
        cmd = ["npm", "run", "build:epub"]
    elif script_name == "build:pdf":
        cmd = ["npm", "run", "build:pdf"]
    
    try:
        # 执行命令
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=BASE_DIR
        )
        
        # 等待进程完成
        stdout, stderr = await process.communicate()
        
        # 检查返回码
        if process.returncode == 0:
            return {
                "status": "success",
                "message": f"Successfully executed {script_name}",
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to execute {script_name}",
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing script: {str(e)}")