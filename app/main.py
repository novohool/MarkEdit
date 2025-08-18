from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import os
import json

# 导入管理API路由器
try:
    from app.admin_api import router as admin_router
except ImportError:
    # 如果绝对导入失败，尝试相对导入
    import sys
    import os
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录
    project_root = os.path.dirname(current_dir)
    # 将项目根目录添加到sys.path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # 现在可以导入admin_api
    from app.admin_api import router as admin_router

app = FastAPI(title="MarkEdit Web Editor")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/src", StaticFiles(directory="src"), name="src")
app.mount("/illustrations", StaticFiles(directory="src/illustrations"), name="illustrations")

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

# 定义文本文件扩展名
TEXT_FILE_EXTENSIONS = {'.md', '.yml', '.yaml', '.css', '.html', '.js', '.json', '.txt', '.xml', '.csv'}

# 定义图片文件扩展名
IMAGE_FILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'}

# 包含管理API路由器
app.include_router(admin_router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/api/files")
async def list_files():
    """列出src目录下的所有文件"""
    def scan_directory(path):
        files = []
        for item in path.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(SRC_DIR)),
                    "type": "file",
                    "size": item.stat().st_size,
                    "extension": item.suffix.lower()
                })
            elif item.is_dir():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(SRC_DIR)),
                    "type": "directory",
                    "children": scan_directory(item)
                })
        return files
    
    return scan_directory(SRC_DIR)

@app.get("/api/file/{file_path:path}")
async def read_file(file_path: str):
    """读取指定文件的内容"""
    full_path = SRC_DIR / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if full_path.is_file():
        # 根据文件扩展名确定内容类型
        suffix = full_path.suffix.lower()
        
        # 对于文本文件，返回内容
        if suffix in TEXT_FILE_EXTENSIONS:
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content, "type": "text", "encoding": "utf-8"}
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    with open(full_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    return {"content": content, "type": "text", "encoding": "gbk"}
                except UnicodeDecodeError:
                    return {"content": "无法解码此文本文件", "type": "text", "encoding": "unknown"}
        # 对于图片文件，返回base64编码
        elif suffix in IMAGE_FILE_EXTENSIONS:
            import base64
            with open(full_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            mime_type = "image/svg+xml" if suffix == ".svg" else f"image/{suffix[1:]}"
            return {"content": content, "type": "image", "mime": mime_type}
        else:
            # 其他二进制文件
            return {"content": "Binary file", "type": "binary"}
    else:
        raise HTTPException(status_code=400, detail="Path is not a file")

@app.post("/api/file/{file_path:path}")
async def save_file(file_path: str, request: Request):
    """保存文件内容"""
    full_path = SRC_DIR / file_path
    
    # 确保目录存在
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取请求体中的内容
    body = await request.body()
    content = body.decode('utf-8')
    
    # 保存文件
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {"message": "File saved successfully"}

@app.delete("/api/file/{file_path:path}")
async def delete_file(file_path: str):
    """删除指定文件"""
    full_path = SRC_DIR / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if full_path.is_file():
        full_path.unlink()
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(status_code=400, detail="Path is not a file")

@app.post("/api/create-file/{file_path:path}")
async def create_file(file_path: str, request: Request):
    """创建新文件"""
    full_path = SRC_DIR / file_path
    
    # 确保目录存在
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果文件已存在，返回错误
    if full_path.exists():
        raise HTTPException(status_code=400, detail="File already exists")
    
    # 获取请求体中的内容（可选）
    body = await request.body()
    content = body.decode('utf-8') if body else ""
    
    # 创建文件
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {"message": "File created successfully"}

@app.post("/api/create-directory/{dir_path:path}")
async def create_directory(dir_path: str):
    """创建新目录"""
    full_path = SRC_DIR / dir_path
    
    # 如果目录已存在，返回错误
    if full_path.exists():
        raise HTTPException(status_code=400, detail="Directory already exists")
    
    # 创建目录
    full_path.mkdir(parents=True, exist_ok=True)
    
    return {"message": "Directory created successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)