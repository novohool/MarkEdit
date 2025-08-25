"""
Response utilities for MarkEdit application.
"""
from fastapi import HTTPException
from fastapi.responses import Response, FileResponse
from pathlib import Path
from .file_utils import is_text_file, is_image_file

def create_file_response(file_path: Path, raw: bool = False) -> Response:
    """创建文件响应"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    suffix = file_path.suffix.lower()
    
    if raw:
        # 原始文件内容响应（用于iframe预览）
        if is_text_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
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
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    return Response(content=content, media_type="text/plain; charset=gbk")
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="无法解码此文本文件")
        elif is_image_file(file_path):
            mime_type = "image/svg+xml" if suffix == ".svg" else f"image/{suffix[1:]}"
            return FileResponse(file_path, media_type=mime_type)
        else:
            return FileResponse(file_path)
    
    # 对于非原始响应，直接返回FileResponse
    return FileResponse(file_path)

def create_static_file_response(file_path: Path) -> Response:
    """创建静态文件响应"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    suffix = file_path.suffix.lower()
    
    # 对于文本文件，直接返回内容
    if is_text_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                return Response(content=content, media_type="text/plain; charset=gbk")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="无法解码此文本文件")
    # 对于图片文件，直接返回文件内容
    elif is_image_file(file_path):
        mime_type = "image/svg+xml" if suffix == ".svg" else f"image/{suffix[1:]}"
        return FileResponse(file_path, media_type=mime_type)
    # 对于其他二进制文件，直接返回文件内容
    else:
        return FileResponse(file_path)