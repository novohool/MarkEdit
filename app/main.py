"""
Main application entry point for MarkEdit.

This module sets up the FastAPI application and includes all necessary routers.
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

# 导入自定义模块
from app.auth import setup_auth_routes
from app.controllers import main_router, file_router, static_router, user_router, admin_router
from app.common import get_startup_service

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('markedit.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 设置特定模块的日志级别
logging.getLogger('app.services.oauth_service').setLevel(logging.DEBUG)
logging.getLogger('app.auth').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.WARNING)

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 确保全局build目录存在
(BASE_DIR / "build").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MarkEdit Web Editor", docs_url=None)

# 设置认证路由
setup_auth_routes(app)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 包含路由器
app.include_router(main_router)
app.include_router(file_router)
app.include_router(static_router)
app.include_router(user_router)
app.include_router(admin_router)

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件"""
    startup_service = get_startup_service()
    await startup_service.startup_initialization()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的事件"""
    startup_service = get_startup_service()
    await startup_service.shutdown_cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)