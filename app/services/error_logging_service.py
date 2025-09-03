"""
错误日志记录服务

提供统一的错误日志记录、分析和报告功能
同时支持用户操作日志记录
"""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict, deque

from app.utils.error_handler import ErrorInfo, ErrorCategory, ErrorLevel

logger = logging.getLogger(__name__)

class ErrorLoggingService:
    """错误日志记录服务"""
    
    def __init__(self, log_directory: str = "logs/errors"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # 用户操作日志目录
        self.user_log_directory = Path("logs/user_operations")
        self.user_log_directory.mkdir(parents=True, exist_ok=True)
        
        # 内存中的错误统计
        self.error_stats = defaultdict(int)
        self.recent_errors = deque(maxlen=100)  # 最近100个错误
        self.error_trends = defaultdict(lambda: defaultdict(int))  # 按时间统计
        
        # 错误阈值配置
        self.alert_thresholds = {
            ErrorLevel.CRITICAL: 1,  # 严重错误立即告警
            ErrorLevel.ERROR: 10,    # 10个错误/小时告警
            ErrorLevel.WARNING: 50   # 50个警告/小时告警
        }
        
        # 初始化日志文件
        self._setup_logging()
    
    def _setup_logging(self):
        """设置错误日志记录"""
        # 创建错误日志处理器
        error_log_file = self.log_directory / "application_errors.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        
        # 创建详细日志格式
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'Context: %(pathname)s:%(lineno)d in %(funcName)s\n'
            '%(exc_info)s\n' + '-' * 80
        )
        error_handler.setFormatter(detailed_formatter)
        
        # 添加到根日志记录器
        root_logger = logging.getLogger()
        root_logger.addHandler(error_handler)
        
        # 创建用户操作日志处理器
        user_log_file = self.user_log_directory / "user_operations.log"
        user_handler = logging.FileHandler(user_log_file, encoding='utf-8')
        user_handler.setLevel(logging.INFO)
        
        # 创建用户操作日志格式
        user_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - USER_OPERATION - %(message)s'
        )
        user_handler.setFormatter(user_formatter)
        
        # 添加到根日志记录器
        root_logger.addHandler(user_handler)
    
    async def log_error(self, error_info: ErrorInfo, additional_context: Dict[str, Any] = None):
        """记录错误信息"""
        try:
            # 更新统计信息
            self._update_statistics(error_info)
            
            # 添加到最近错误列表
            self.recent_errors.append({
                'timestamp': error_info.context.timestamp,
                'level': error_info.level.value,
                'category': error_info.category.value,
                'message': error_info.message,
                'error_id': error_info.context.error_id,
                'user_id': error_info.context.user_id
            })
            
            # 写入详细日志文件
            await self._write_detailed_log(error_info, additional_context)
            
            # 检查是否需要告警
            await self._check_alert_conditions(error_info)
            
        except Exception as e:
            logger.error(f"记录错误信息失败: {str(e)}", exc_info=True)
    
    def _update_statistics(self, error_info: ErrorInfo):
        """更新错误统计信息"""
        # 按级别统计
        self.error_stats[f"level_{error_info.level.value}"] += 1
        
        # 按分类统计
        self.error_stats[f"category_{error_info.category.value}"] += 1
        
        # 按用户统计
        if error_info.context.user_id:
            self.error_stats[f"user_{error_info.context.user_id}"] += 1
        
        # 按时间统计（小时级别）
        hour_key = error_info.context.timestamp.strftime("%Y-%m-%d_%H")
        self.error_trends[hour_key][error_info.level.value] += 1
    
    async def _write_detailed_log(self, error_info: ErrorInfo, additional_context: Dict[str, Any] = None):
        """写入详细的错误日志"""
        try:
            # 创建日志条目
            log_entry = {
                'timestamp': error_info.context.timestamp.isoformat(),
                'error_id': error_info.context.error_id,
                'level': error_info.level.value,
                'category': error_info.category.value,
                'message': error_info.message,
                'user_message': error_info.user_message,
                'context': error_info.context.to_dict(),
                'recovery_suggestions': error_info.recovery_suggestions,
                'debug_info': error_info.debug_info,
                'additional_context': additional_context or {}
            }
            
            # 按日期分文件存储
            date_str = error_info.context.timestamp.strftime("%Y-%m-%d")
            log_file = self.log_directory / f"errors_{date_str}.json"
            
            # 异步写入文件
            await self._append_to_json_log(log_file, log_entry)
            
        except Exception as e:
            logger.error(f"写入详细错误日志失败: {str(e)}", exc_info=True)
    
    async def _append_to_json_log(self, log_file: Path, log_entry: Dict[str, Any]):
        """异步追加JSON日志条目"""
        try:
            # 读取现有日志
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # 添加新条目
            logs.append(log_entry)
            
            # 写回文件
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"追加JSON日志失败: {str(e)}", exc_info=True)
    
    async def _check_alert_conditions(self, error_info: ErrorInfo):
        """检查告警条件"""
        try:
            level = error_info.level
            threshold = self.alert_thresholds.get(level, float('inf'))
            
            if threshold == float('inf'):
                return
            
            # 获取当前小时的错误数量
            current_hour = datetime.now().strftime("%Y-%m-%d_%H")
            current_count = self.error_trends[current_hour][level.value]
            
            if current_count >= threshold:
                await self._send_alert(error_info, current_count, threshold)
                
        except Exception as e:
            logger.error(f"检查告警条件失败: {str(e)}", exc_info=True)
    
    async def _send_alert(self, error_info: ErrorInfo, current_count: int, threshold: int):
        """发送告警"""
        try:
            alert_message = (
                f"错误告警: {error_info.level.value.upper()} 级别错误超过阈值\n"
                f"当前数量: {current_count}, 阈值: {threshold}\n"
                f"错误类别: {error_info.category.value}\n"
                f"错误消息: {error_info.message}\n"
                f"错误ID: {error_info.context.error_id}\n"
                f"时间: {error_info.context.timestamp}"
            )
            
            # 这里可以集成邮件、短信、钉钉等告警方式
            logger.critical(f"ALERT: {alert_message}")
            
            # 可以扩展为发送到监控系统
            # await self._send_to_monitoring_system(alert_message)
            
        except Exception as e:
            logger.error(f"发送告警失败: {str(e)}", exc_info=True)
    
    async def get_error_statistics(self, 
                                 start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """获取错误统计信息"""
        try:
            if not start_time:
                start_time = datetime.now() - timedelta(days=7)
            if not end_time:
                end_time = datetime.now()
            
            # 从日志文件中读取统计信息
            stats = await self._calculate_statistics(start_time, end_time)
            
            # 添加实时统计
            stats['current_stats'] = dict(self.error_stats)
            stats['recent_errors'] = list(self.recent_errors)
            
            # 确保所有字典都是普通字典而不是defaultdict
            for key in ['by_level', 'by_category', 'by_user', 'by_hour', 'top_errors']:
                if key in stats and hasattr(stats[key], 'default_factory'):
                    stats[key] = dict(stats[key])
            
            return stats
            
        except Exception as e:
            logger.error(f"获取错误统计失败: {str(e)}", exc_info=True)
            return {}
    
    async def _calculate_statistics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """从日志文件计算统计信息"""
        stats = {
            'total_errors': 0,
            'by_level': defaultdict(int),
            'by_category': defaultdict(int),
            'by_user': defaultdict(int),
            'by_hour': defaultdict(int),
            'top_errors': defaultdict(int)
        }
        
        try:
            # 遍历时间范围内的日志文件
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                log_file = self.log_directory / f"errors_{current_date.strftime('%Y-%m-%d')}.json"
                
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                    
                    for log_entry in logs:
                        entry_time = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if start_time <= entry_time <= end_time:
                            stats['total_errors'] += 1
                            stats['by_level'][log_entry['level']] += 1
                            stats['by_category'][log_entry['category']] += 1
                            
                            if log_entry['context'].get('user_id'):
                                stats['by_user'][log_entry['context']['user_id']] += 1
                            
                            hour_key = entry_time.strftime('%Y-%m-%d %H:00')
                            stats['by_hour'][hour_key] += 1
                            
                            # 统计最常见的错误
                            error_key = f"{log_entry['category']}:{log_entry['message'][:50]}"
                            stats['top_errors'][error_key] += 1
                
                current_date += timedelta(days=1)
            
            # 转换为普通字典并排序
            stats['by_level'] = dict(stats['by_level'])
            stats['by_category'] = dict(stats['by_category'])
            stats['by_user'] = dict(sorted(stats['by_user'].items(), key=lambda x: x[1], reverse=True)[:10])
            stats['top_errors'] = dict(sorted(stats['top_errors'].items(), key=lambda x: x[1], reverse=True)[:10])
            
            return stats
            
        except Exception as e:
            logger.error(f"计算统计信息失败: {str(e)}", exc_info=True)
            return stats
    
    async def get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """根据错误ID获取详细信息"""
        try:
            # 搜索最近7天的日志文件
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                log_file = self.log_directory / f"errors_{date.strftime('%Y-%m-%d')}.json"
                
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                    
                    for log_entry in logs:
                        if log_entry.get('error_id') == error_id:
                            return log_entry
            
            return None
            
        except Exception as e:
            logger.error(f"获取错误详情失败: {str(e)}", exc_info=True)
            return None
    
    async def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧的日志文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for log_file in self.log_directory.glob("errors_*.json"):
                try:
                    # 从文件名提取日期
                    date_str = log_file.stem.replace("errors_", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        logger.info(f"删除旧日志文件: {log_file}")
                        
                except ValueError:
                    # 文件名格式不正确，跳过
                    continue
                    
        except Exception as e:
            logger.error(f"清理旧日志失败: {str(e)}", exc_info=True)
    
    async def export_error_report(self, 
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None,
                                format: str = 'json') -> str:
        """导出错误报告"""
        try:
            if not start_time:
                start_time = datetime.now() - timedelta(days=7)
            if not end_time:
                end_time = datetime.now()
            
            # 获取统计信息
            stats = await self.get_error_statistics(start_time, end_time)
            
            # 创建报告
            report = {
                'report_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'summary': {
                    'total_errors': stats.get('total_errors', 0),
                    'error_rate': stats.get('total_errors', 0) / max(1, (end_time - start_time).total_seconds() / 3600),  # 每小时错误数
                    'most_common_level': max(stats.get('by_level', {}).items(), key=lambda x: x[1], default=('none', 0))[0],
                    'most_common_category': max(stats.get('by_category', {}).items(), key=lambda x: x[1], default=('none', 0))[0]
                },
                'statistics': stats,
                'generated_at': datetime.now().isoformat()
            }
            
            # 保存报告
            report_file = self.log_directory / f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"错误报告已生成: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"导出错误报告失败: {str(e)}", exc_info=True)
            return ""

# 全局错误日志服务实例
# 全局错误日志服务实例
error_logging_service = ErrorLoggingService()

def log_user_operation(username: str, operation: str, details: Dict[str, Any] = None):
    """记录用户操作日志的便捷函数"""
    logger.info(f"User {username}: {operation}" + (f" - Details: {details}" if details else ""))

async def log_user_operation_async(username: str, operation: str, details: Dict[str, Any] = None):
    """异步记录用户操作日志的便捷函数"""
    logger.info(f"User {username}: {operation}" + (f" - Details: {details}" if details else ""))

async def log_application_error(error_info: ErrorInfo, additional_context: Dict[str, Any] = None):
    """记录应用程序错误的便捷函数"""
    await error_logging_service.log_error(error_info, additional_context)

async def get_error_statistics(start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> Dict[str, Any]:
    """获取错误统计信息的便捷函数"""
    return await error_logging_service.get_error_statistics(start_time, end_time)