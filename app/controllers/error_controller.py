"""
错误处理控制器

提供错误报告、统计和管理的API接口
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.utils.error_handler import (
    error_handler, ErrorCategory, ErrorLevel, ErrorContext, ErrorInfo,
    handle_controller_error
)
from app.services.error_logging_service import error_logging_service
from app.common import require_permission

logger = logging.getLogger(__name__)

# 创建路由器
error_router = APIRouter(prefix="/api/error", tags=["error"])

@error_router.post("/frontend-error")
@handle_controller_error("前端错误报告")
async def report_frontend_error(request: Request):
    """接收前端错误报告"""
    try:
        error_data = await request.json()
        
        # 创建错误上下文
        context = error_handler.create_error_context(request)
        
        # 根据前端错误类型确定分类
        error_category = _determine_frontend_error_category(error_data)
        error_level = _determine_frontend_error_level(error_data)
        
        # 创建错误信息
        error_info = ErrorInfo(
            message=error_data.get('message', '前端未知错误'),
            error_code=f"FRONTEND_{error_data.get('type', 'UNKNOWN').upper()}",
            level=error_level,
            category=error_category,
            context=context,
            user_message="前端发生错误，已记录到系统日志",
            debug_info={
                'frontend_data': error_data,
                'user_agent': request.headers.get('user-agent'),
                'referer': request.headers.get('referer')
            }
        )
        
        # 记录错误
        await error_logging_service.log_error(error_info, {
            'source': 'frontend',
            'browser_info': {
                'user_agent': request.headers.get('user-agent'),
                'referer': request.headers.get('referer')
            }
        })
        
        return {
            "status": "success",
            "message": "错误报告已记录",
            "error_id": error_info.context.error_id
        }
        
    except Exception as e:
        logger.error(f"处理前端错误报告失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="错误报告处理失败")

def _determine_frontend_error_category(error_data: Dict[str, Any]) -> ErrorCategory:
    """根据前端错误数据确定错误分类"""
    error_type = error_data.get('type', '').lower()
    message = error_data.get('message', '').lower()
    
    if 'network' in error_type or 'fetch' in message or 'network error' in message:
        return ErrorCategory.NETWORK
    elif 'api_error' in error_type:
        return ErrorCategory.BUSINESS_LOGIC
    elif 'javascript_error' in error_type:
        return ErrorCategory.SYSTEM
    elif 'promise_rejection' in error_type:
        return ErrorCategory.SYSTEM
    else:
        return ErrorCategory.UNKNOWN

def _determine_frontend_error_level(error_data: Dict[str, Any]) -> ErrorLevel:
    """根据前端错误数据确定错误级别"""
    error_type = error_data.get('type', '').lower()
    status = error_data.get('status', 0)
    
    if status >= 500 or 'critical' in error_type:
        return ErrorLevel.CRITICAL
    elif status >= 400 or 'javascript_error' in error_type:
        return ErrorLevel.ERROR
    elif 'network' in error_type or 'api_error' in error_type:
        return ErrorLevel.WARNING
    else:
        return ErrorLevel.INFO

@error_router.get("/statistics")
@require_permission("admin_access")
@handle_controller_error("获取错误统计")
async def get_error_statistics(request: Request, 
                             days: int = 7):
    """获取错误统计信息"""
    start_time = datetime.now() - timedelta(days=days)
    end_time = datetime.now()
    
    stats = await error_logging_service.get_error_statistics(start_time, end_time)
    
    return {
        "status": "success",
        "data": stats,
        "period": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "days": days
        }
    }

@error_router.get("/details/{error_id}")
@require_permission("admin_access")
@handle_controller_error("获取错误详情")
async def get_error_details(error_id: str, request: Request):
    """获取特定错误的详细信息"""
    error_details = await error_logging_service.get_error_details(error_id)
    
    if not error_details:
        raise HTTPException(status_code=404, detail="错误记录不存在")
    
    return {
        "status": "success",
        "data": error_details
    }

@error_router.post("/export-report")
@require_permission("admin_access")
@handle_controller_error("导出错误报告")
async def export_error_report(request: Request):
    """导出错误报告"""
    try:
        request_data = await request.json()
        
        days = request_data.get('days', 7)
        format_type = request_data.get('format', 'json')
        
        start_time = datetime.now() - timedelta(days=days)
        end_time = datetime.now()
        
        report_file = await error_logging_service.export_error_report(
            start_time, end_time, format_type
        )
        
        if not report_file:
            raise HTTPException(status_code=500, detail="报告生成失败")
        
        return {
            "status": "success",
            "message": "错误报告已生成",
            "report_file": report_file
        }
        
    except Exception as e:
        logger.error(f"导出错误报告失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="报告导出失败")

@error_router.post("/cleanup")
@require_permission("admin_access")
@handle_controller_error("清理错误日志")
async def cleanup_error_logs(request: Request):
    """清理旧的错误日志"""
    try:
        request_data = await request.json()
        days_to_keep = request_data.get('days_to_keep', 30)
        
        await error_logging_service.cleanup_old_logs(days_to_keep)
        
        return {
            "status": "success",
            "message": f"已清理超过 {days_to_keep} 天的错误日志"
        }
        
    except Exception as e:
        logger.error(f"清理错误日志失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="日志清理失败")

@error_router.get("/health")
@handle_controller_error("错误处理系统健康检查")
async def error_system_health(request: Request):
    """错误处理系统健康检查"""
    try:
        # 检查错误日志服务状态
        recent_stats = await error_logging_service.get_error_statistics(
            datetime.now() - timedelta(hours=1),
            datetime.now()
        )
        
        # 计算健康指标
        total_errors = recent_stats.get('total_errors', 0)
        critical_errors = recent_stats.get('by_level', {}).get('critical', 0)
        error_rate = total_errors / 60  # 每分钟错误数
        
        # 确定健康状态
        if critical_errors > 0:
            health_status = "critical"
            health_message = f"发现 {critical_errors} 个严重错误"
        elif error_rate > 1:
            health_status = "warning"
            health_message = f"错误率较高: {error_rate:.2f} 错误/分钟"
        else:
            health_status = "healthy"
            health_message = "错误处理系统运行正常"
        
        return {
            "status": "success",
            "health": {
                "status": health_status,
                "message": health_message,
                "metrics": {
                    "total_errors_last_hour": total_errors,
                    "critical_errors_last_hour": critical_errors,
                    "error_rate_per_minute": error_rate
                },
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"错误系统健康检查失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "health": {
                "status": "unknown",
                "message": "健康检查失败",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }

