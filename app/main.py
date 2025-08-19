from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response, FileResponse
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
BUILD_DIR = BASE_DIR / "build"

# 确保build目录存在
BUILD_DIR.mkdir(parents=True, exist_ok=True)

# 定义文本文件扩展名（包含无后缀文件）
TEXT_FILE_EXTENSIONS = {'.md', '.yml', '.yaml', '.css', '.html', '.js', '.json', '.txt', '.xml', '.csv', ''}

# 定义图片文件扩展名
IMAGE_FILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'}

# 定义可预览的二进制文件扩展名
PREVIEWABLE_BINARY_EXTENSIONS = {'.pdf', '.epub'}

# 包含管理API路由器
app.include_router(admin_router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/epub-viewer.html", response_class=HTMLResponse)
async def read_epub_viewer(request: Request):
    return templates.TemplateResponse("epub-viewer.html", {"request": request})


@app.get("/api/files")
async def list_files():
    """分别列出src和build目录下的所有文件"""
    def scan_directory(path, base_dir):
        files = []
        for item in path.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(base_dir)),
                    "type": "file",
                    "size": item.stat().st_size,
                    "extension": item.suffix.lower()
                })
            elif item.is_dir():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(base_dir)),
                    "type": "directory",
                    "children": scan_directory(item, base_dir)
                })
        return files
    
    return {
        "src": scan_directory(SRC_DIR, SRC_DIR),
        "build": scan_directory(BUILD_DIR, BUILD_DIR)
    }

@app.get("/api/file/{file_type}/{file_path:path}")
async def read_file(file_type: str, file_path: str, request: Request, raw: bool = False):
    """读取指定文件的内容"""
    if file_type == "src":
        full_path = SRC_DIR / file_path
    elif file_type == "build":
        full_path = BUILD_DIR / file_path
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if full_path.is_file():
        # 根据文件扩展名确定内容类型
        suffix = full_path.suffix.lower()
        
        # 如果请求原始文件内容（用于iframe预览）
        if raw:
            # 对于文本文件，直接返回内容
            if suffix in TEXT_FILE_EXTENSIONS:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # 根据文件类型设置正确的Content-Type
                    if suffix == '.html':
                        return Response(content=content, media_type="text/html; charset=utf-8")
                    elif suffix == '.css':
                        return Response(content=content, media_type="text/css; charset=utf-8")
                    elif suffix == '.js':
                        return Response(content=content, media_type="application/javascript; charset=utf-8")
                    else:
                        return Response(content=content, media_type="text/plain; charset=utf-8")
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试其他编码
                    try:
                        with open(full_path, 'r', encoding='gbk') as f:
                            content = f.read()
                        return Response(content=content, media_type="text/plain; charset=gbk")
                    except UnicodeDecodeError:
                        raise HTTPException(status_code=400, detail="无法解码此文本文件")
            # 对于图片文件，直接返回文件内容
            elif suffix in IMAGE_FILE_EXTENSIONS:
                mime_type = "image/svg+xml" if suffix == ".svg" else f"image/{suffix[1:]}"
                return FileResponse(full_path, media_type=mime_type)
            # 对于其他二进制文件，直接返回文件内容
            else:
                return FileResponse(full_path)
        
        # 对于文本文件，返回内容（JSON格式）
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
        # 对于可预览的二进制文件，返回FileResponse以支持iframe预览
        elif suffix in PREVIEWABLE_BINARY_EXTENSIONS:
            mime_type = "application/pdf" if suffix == ".pdf" else "application/epub+zip"
            return FileResponse(full_path, media_type=mime_type)
        else:
            # 其他二进制文件
            return {"content": "Binary file", "type": "binary"}
    else:
        raise HTTPException(status_code=400, detail="Path is not a file")

@app.post("/api/file/{file_type}/{file_path:path}")
async def save_file(file_type: str, file_path: str, request: Request):
    """保存文件内容"""
    if file_type == "src":
        full_path = SRC_DIR / file_path
    else:
        raise HTTPException(status_code=400, detail="只能保存src目录下的文件")
    
    # 确保目录存在
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取请求体中的内容
    body = await request.body()
    content = body.decode('utf-8')
    
    # 如果是JSON文件，验证JSON格式
    if full_path.suffix.lower() == '.json':
        try:
            json.loads(content)  # 验证JSON格式是否正确
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    
    # 保存文件
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 验证保存后的文件是否为有效的JSON（如果是JSON文件）
    if full_path.suffix.lower() == '.json':
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
                json.loads(saved_content)  # 再次验证JSON格式是否正确
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Saved file is not valid JSON: {str(e)}")
    
    return {"message": "File saved successfully"}

@app.delete("/api/file/{file_type}/{file_path:path}")
async def delete_file(file_type: str, file_path: str):
    """删除指定文件"""
    if file_type == "src":
        full_path = SRC_DIR / file_path
    else:
        raise HTTPException(status_code=400, detail="只能删除src目录下的文件")
    
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
    uvicorn.run(app, host="0.0.0.0", port=8080)