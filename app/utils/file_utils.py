"""
File operation utilities for MarkEdit application.
"""
from pathlib import Path
from typing import Dict, List, Any
import json
import base64
from fastapi import HTTPException

# 定义文件扩展名常量
TEXT_FILE_EXTENSIONS = {'.md', '.yml', '.yaml', '.css', '.html', '.js', '.json', '.txt', '.xml', '.csv', ''}
IMAGE_FILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'}
PREVIEWABLE_BINARY_EXTENSIONS = {'.pdf', '.epub'}

def is_text_file(file_path: Path) -> bool:
    """判断是否为文本文件"""
    return file_path.suffix.lower() in TEXT_FILE_EXTENSIONS

def is_image_file(file_path: Path) -> bool:
    """判断是否为图片文件"""
    return file_path.suffix.lower() in IMAGE_FILE_EXTENSIONS

def is_previewable_binary(file_path: Path) -> bool:
    """判断是否为可预览的二进制文件"""
    return file_path.suffix.lower() in PREVIEWABLE_BINARY_EXTENSIONS

def scan_directory(path: Path, base_dir: Path) -> List[Dict[str, Any]]:
    """扫描目录，返回文件和目录信息"""
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

def read_text_file(file_path: Path) -> Dict[str, str]:
    """读取文本文件内容"""
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

def read_image_file(file_path: Path) -> Dict[str, str]:
    """读取图片文件内容，返回base64编码"""
    with open(file_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    suffix = file_path.suffix.lower()
    mime_type = "image/svg+xml" if suffix == ".svg" else f"image/{suffix[1:]}"
    return {"content": content, "type": "image", "mime": mime_type}

def save_text_file(file_path: Path, content: str) -> None:
    """保存文本文件内容"""
    # 确保目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果是JSON文件，验证JSON格式
    if file_path.suffix.lower() == '.json':
        try:
            json.loads(content)  # 验证JSON格式是否正确
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 验证保存后的文件是否为有效的JSON（如果是JSON文件）
    if file_path.suffix.lower() == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
                json.loads(saved_content)  # 再次验证JSON格式是否正确
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Saved file is not valid JSON: {str(e)}")

def delete_file_safely(file_path: Path) -> None:
    """安全删除文件"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if file_path.is_file():
        file_path.unlink()
    else:
        raise HTTPException(status_code=400, detail="Path is not a file")

def create_file_safely(file_path: Path, content: str = "") -> None:
    """安全创建文件"""
    # 确保目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果文件已存在，返回错误
    if file_path.exists():
        raise HTTPException(status_code=400, detail="File already exists")
    
    # 创建文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def create_directory_safely(dir_path: Path) -> None:
    """安全创建目录"""
    # 如果目录已存在，返回错误
    if dir_path.exists():
        raise HTTPException(status_code=400, detail="Directory already exists")
    
    # 创建目录
    dir_path.mkdir(parents=True, exist_ok=True)