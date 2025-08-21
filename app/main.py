from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response, FileResponse
from pathlib import Path
import os
import json
import zipfile
import datetime
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量存储启动备份文件名
# startup_backup_filename = None  # 已移至 app/shared.py

# 导入管理API路由器
try:
    from app.admin_api import router as admin_router
    from app.auth import setup_auth_routes, get_session, SessionData
    from app.shared import get_user_src_directory
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
    # 现在可以导入admin_api、auth和shared
    from app.admin_api import router as admin_router
    from app.auth import setup_auth_routes, get_session, SessionData
    from app.shared import get_user_src_directory


def backup_src_directory(startup_backup=False):
    """备份src目录到zip文件"""
    try:
        # 创建备份目录
        backup_dir = BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # 获取全局src目录
        src_dir = BASE_DIR / "src"
        
        # 生成备份文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if startup_backup:
            backup_filename = f"src_backup_{timestamp}_startup.zip"
        else:
            backup_filename = f"src_backup_{timestamp}.zip"
        backup_path = backup_dir / backup_filename
        
        # 创建zip文件
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历src目录中的所有文件和子目录
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_path = Path(root) / file
                    # 计算相对路径
                    arcname = file_path.relative_to(BASE_DIR)
                    zipf.write(file_path, arcname)
        
        # 如果是启动备份，保存备份文件名到特定文件和全局变量
        if startup_backup:
            from app.shared import set_startup_backup_filename
            set_startup_backup_filename(backup_filename)
            
            startup_backup_file = backup_dir / "startup_backup.txt"
            with open(startup_backup_file, 'w') as f:
                f.write(backup_filename)
        
        logger.info(f"Src目录备份成功: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份src目录时出错: {str(e)}")
        raise

app = FastAPI(title="MarkEdit Web Editor")

# 设置认证路由
setup_auth_routes(app)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
# 移除了全局src和illustrations的静态文件挂载，改为动态提供用户特定的文件

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
# SRC_DIR = BASE_DIR / "src"  # 全局src目录，不再直接使用
# BUILD_DIR = BASE_DIR / "build"  # 全局build目录，不再直接使用

# 确保全局build目录存在
(BASE_DIR / "build").mkdir(parents=True, exist_ok=True)

def get_current_user_src_dir(request: Request) -> Path:
    """获取当前用户的src目录"""
    session = get_session(request)
    if not session.username:
        raise HTTPException(status_code=401, detail="用户未登录")
    return get_user_src_directory(session.username)

# 定义文本文件扩展名（包含无后缀文件）
TEXT_FILE_EXTENSIONS = {'.md', '.yml', '.yaml', '.css', '.html', '.js', '.json', '.txt', '.xml', '.csv', ''}

# 定义图片文件扩展名
IMAGE_FILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'}

# 定义可预览的二进制文件扩展名
PREVIEWABLE_BINARY_EXTENSIONS = {'.pdf', '.epub'}

# 包含管理API路由器
app.include_router(admin_router)

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件"""
    logger.info("应用启动完成")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/epub-viewer.html", response_class=HTMLResponse)
async def read_epub_viewer(request: Request):
    return templates.TemplateResponse("epub-viewer.html", {"request": request})

@app.get("/user-src/{file_path:path}")
async def serve_user_static_file(file_path: str, request: Request):
    """动态提供用户特定的src目录下的文件"""
    # 获取当前用户的src目录
    user_src_dir = get_current_user_src_dir(request)
    full_path = user_src_dir / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    # 根据文件扩展名确定内容类型
    suffix = full_path.suffix.lower()
    
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

@app.get("/user-illustrations/{file_path:path}")
async def serve_user_illustrations_file(file_path: str, request: Request):
    """动态提供用户特定的illustrations目录下的文件"""
    # 获取当前用户的src目录，然后定位到illustrations子目录
    user_src_dir = get_current_user_src_dir(request)
    illustrations_dir = user_src_dir / "illustrations"
    full_path = illustrations_dir / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    # 根据文件扩展名确定内容类型
    suffix = full_path.suffix.lower()
    
    # 对于图片文件，直接返回文件内容
    if suffix in IMAGE_FILE_EXTENSIONS:
        mime_type = "image/svg+xml" if suffix == ".svg" else f"image/{suffix[1:]}"
        return FileResponse(full_path, media_type=mime_type)
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型")


@app.get("/api/files")
async def list_files(request: Request):
    """分别列出当前用户的src和用户特定build目录下的所有文件"""
    def scan_directory(path, base_dir):
        files = []
        # 检查目录是否存在，如果不存在则创建它
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return files
            
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
    
    # 获取当前用户的src目录
    user_src_dir = get_current_user_src_dir(request)
    
    # 获取当前用户的build目录
    session = get_session(request)
    user_build_dir = BASE_DIR / "users" / session.username / "build"
    user_build_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "src": scan_directory(user_src_dir, user_src_dir),
        "build": scan_directory(user_build_dir, user_build_dir)
    }

@app.get("/api/file/{file_type}/{file_path:path}")
async def read_file(file_type: str, file_path: str, request: Request, raw: bool = False):
    """读取指定文件的内容"""
    if file_type == "src":
        # 获取当前用户的src目录
        user_src_dir = get_current_user_src_dir(request)
        full_path = user_src_dir / file_path
    elif file_type == "build":
        # 获取当前用户的build目录
        session = get_session(request)
        user_build_dir = BASE_DIR / "users" / session.username / "build"
        full_path = user_build_dir / file_path
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
        # 获取当前用户的src目录
        user_src_dir = get_current_user_src_dir(request)
        full_path = user_src_dir / file_path
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
async def delete_file(file_type: str, file_path: str, request: Request):
    """删除指定文件"""
    if file_type == "src":
        # 获取当前用户的src目录
        user_src_dir = get_current_user_src_dir(request)
        full_path = user_src_dir / file_path
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
    # 获取当前用户的src目录
    user_src_dir = get_current_user_src_dir(request)
    full_path = user_src_dir / file_path
    
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
async def create_directory(dir_path: str, request: Request):
    """创建新目录"""
    # 获取当前用户的src目录
    user_src_dir = get_current_user_src_dir(request)
    full_path = user_src_dir / dir_path
    
    # 如果目录已存在，返回错误
    if full_path.exists():
        raise HTTPException(status_code=400, detail="Directory already exists")
    
    # 创建目录
    full_path.mkdir(parents=True, exist_ok=True)
    
    return {"message": "Directory created successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)