"""
System monitoring utilities for MarkEdit application.

This module contains utility functions for system monitoring, statistics, and health checks.
"""
import os
import sys
import psutil
import logging
import platform
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class SystemMonitor:
    """系统监控类"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.src_dir = self.base_dir / "src"
        self.build_dir = self.base_dir / "build"
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统基本信息"""
        try:
            return {
                "platform": platform.platform(),
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "architecture": platform.architecture()[0],
                "hostname": platform.node(),
                "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "uptime_seconds": (datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).total_seconds()
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            return {"error": str(e)}
    
    def get_memory_info(self) -> Dict[str, Any]:
        """获取内存信息"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "virtual_memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                    "active": getattr(memory, 'active', None),
                    "inactive": getattr(memory, 'inactive', None),
                    "buffers": getattr(memory, 'buffers', None),
                    "cached": getattr(memory, 'cached', None),
                    "shared": getattr(memory, 'shared', None)
                },
                "swap_memory": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                    "sin": swap.sin,
                    "sout": swap.sout
                }
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {str(e)}")
            return {"error": str(e)}
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """获取CPU信息"""
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_times = psutil.cpu_times()
            
            return {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "frequency": {
                    "current": cpu_freq.current if cpu_freq else None,
                    "min": cpu_freq.min if cpu_freq else None,
                    "max": cpu_freq.max if cpu_freq else None
                },
                "usage_percent": psutil.cpu_percent(interval=1),
                "usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                },
                "load_average": getattr(os, 'getloadavg', lambda: [0, 0, 0])()[:3]
            }
        except Exception as e:
            logger.error(f"获取CPU信息失败: {str(e)}")
            return {"error": str(e)}
    
    def get_disk_info(self) -> Dict[str, Any]:
        """获取磁盘信息"""
        try:
            disk_usage = {}
            
            # 获取根目录磁盘使用情况
            root_usage = psutil.disk_usage('/')
            disk_usage['/'] = {
                "total": root_usage.total,
                "used": root_usage.used,
                "free": root_usage.free,
                "percent": (root_usage.used / root_usage.total) * 100
            }
            
            # 获取项目目录磁盘使用情况
            try:
                project_usage = psutil.disk_usage(str(self.base_dir))
                disk_usage['project'] = {
                    "total": project_usage.total,
                    "used": project_usage.used,
                    "free": project_usage.free,
                    "percent": (project_usage.used / project_usage.total) * 100,
                    "path": str(self.base_dir)
                }
            except Exception:
                pass
            
            # 获取磁盘IO统计
            disk_io = psutil.disk_io_counters()
            io_stats = None
            if disk_io:
                io_stats = {
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_time": disk_io.read_time,
                    "write_time": disk_io.write_time
                }
            
            return {
                "usage": disk_usage,
                "io_stats": io_stats
            }
        except Exception as e:
            logger.error(f"获取磁盘信息失败: {str(e)}")
            return {"error": str(e)}
    
    def get_network_info(self) -> Dict[str, Any]:
        """获取网络信息"""
        try:
            # 获取网络IO统计
            net_io = psutil.net_io_counters()
            io_stats = None
            if net_io:
                io_stats = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout
                }
            
            # 获取网络连接信息
            try:
                connections = psutil.net_connections()
                connection_stats = {
                    "total": len(connections),
                    "established": len([c for c in connections if c.status == 'ESTABLISHED']),
                    "listening": len([c for c in connections if c.status == 'LISTEN'])
                }
            except (psutil.AccessDenied, PermissionError):
                connection_stats = {"error": "权限不足，无法获取连接信息"}
            
            return {
                "io_stats": io_stats,
                "connections": connection_stats
            }
        except Exception as e:
            logger.error(f"获取网络信息失败: {str(e)}")
            return {"error": str(e)}
    
    def get_process_info(self) -> Dict[str, Any]:
        """获取进程信息"""
        try:
            current_process = psutil.Process()
            
            # 获取当前进程信息
            process_info = {
                "pid": current_process.pid,
                "name": current_process.name(),
                "cmdline": current_process.cmdline(),
                "create_time": datetime.datetime.fromtimestamp(current_process.create_time()).isoformat(),
                "cpu_percent": current_process.cpu_percent(),
                "memory_percent": current_process.memory_percent(),
                "num_threads": current_process.num_threads()
            }
            
            # 获取内存详细信息
            try:
                memory_info = current_process.memory_info()
                process_info["memory_info"] = {
                    "rss": memory_info.rss,  # 物理内存
                    "vms": memory_info.vms   # 虚拟内存
                }
            except Exception:
                pass
            
            # 获取文件描述符信息
            try:
                process_info["num_fds"] = current_process.num_fds()
            except (AttributeError, psutil.AccessDenied):
                pass
            
            return process_info
        except Exception as e:
            logger.error(f"获取进程信息失败: {str(e)}")
            return {"error": str(e)}
    
    def get_file_system_stats(self) -> Dict[str, Any]:
        """获取文件系统统计信息"""
        try:
            stats = {
                "src_directory": self._get_directory_stats(self.src_dir),
                "build_directory": self._get_directory_stats(self.build_dir),
                "base_directory": self._get_directory_stats(self.base_dir)
            }
            
            return stats
        except Exception as e:
            logger.error(f"获取文件系统统计失败: {str(e)}")
            return {"error": str(e)}
    
    def _get_directory_stats(self, directory: Path) -> Dict[str, Any]:
        """获取目录统计信息"""
        try:
            if not directory.exists():
                return {"exists": False, "path": str(directory)}
            
            stats = {
                "exists": True,
                "path": str(directory),
                "total_files": 0,
                "total_directories": 0,
                "total_size": 0,
                "file_types": {},
                "largest_files": []
            }
            
            file_sizes = []
            
            for item in directory.rglob('*'):
                try:
                    if item.is_file():
                        stats["total_files"] += 1
                        size = item.stat().st_size
                        stats["total_size"] += size
                        
                        # 记录文件类型
                        ext = item.suffix.lower()
                        if ext:
                            stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
                        else:
                            stats["file_types"]["no_extension"] = stats["file_types"].get("no_extension", 0) + 1
                        
                        # 记录大文件
                        file_sizes.append((str(item.relative_to(directory)), size))
                        
                    elif item.is_dir():
                        stats["total_directories"] += 1
                except (PermissionError, OSError):
                    continue
            
            # 获取最大的5个文件
            file_sizes.sort(key=lambda x: x[1], reverse=True)
            stats["largest_files"] = file_sizes[:5]
            
            return stats
        except Exception as e:
            return {"error": str(e), "path": str(directory)}
    
    def get_application_health(self) -> Dict[str, Any]:
        """获取应用程序健康状态"""
        try:
            health = {
                "status": "healthy",
                "checks": {},
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # 检查数据库连接
            try:
                from app.models import database
                # 简单的数据库连接测试
                health["checks"]["database"] = {
                    "status": "connected" if database.is_connected else "disconnected",
                    "details": "数据库连接正常" if database.is_connected else "数据库未连接"
                }
            except Exception as e:
                health["checks"]["database"] = {
                    "status": "error",
                    "details": f"数据库检查失败: {str(e)}"
                }
                health["status"] = "unhealthy"
            
            # 检查关键目录
            critical_dirs = [self.src_dir, self.base_dir]
            for dir_path in critical_dirs:
                dir_name = dir_path.name
                if dir_path.exists():
                    health["checks"][f"directory_{dir_name}"] = {
                        "status": "ok",
                        "details": f"目录 {dir_path} 存在"
                    }
                else:
                    health["checks"][f"directory_{dir_name}"] = {
                        "status": "missing",
                        "details": f"目录 {dir_path} 不存在"
                    }
                    health["status"] = "degraded"
            
            # 检查系统资源
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                health["checks"]["memory"] = {
                    "status": "critical",
                    "details": f"内存使用率过高: {memory.percent}%"
                }
                health["status"] = "unhealthy"
            elif memory.percent > 80:
                health["checks"]["memory"] = {
                    "status": "warning",
                    "details": f"内存使用率较高: {memory.percent}%"
                }
                if health["status"] == "healthy":
                    health["status"] = "degraded"
            else:
                health["checks"]["memory"] = {
                    "status": "ok",
                    "details": f"内存使用率正常: {memory.percent}%"
                }
            
            # 检查磁盘空间
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 95:
                health["checks"]["disk"] = {
                    "status": "critical",
                    "details": f"磁盘空间不足: {disk_percent:.1f}%"
                }
                health["status"] = "unhealthy"
            elif disk_percent > 85:
                health["checks"]["disk"] = {
                    "status": "warning",
                    "details": f"磁盘空间较少: {disk_percent:.1f}%"
                }
                if health["status"] == "healthy":
                    health["status"] = "degraded"
            else:
                health["checks"]["disk"] = {
                    "status": "ok",
                    "details": f"磁盘空间充足: {disk_percent:.1f}%"
                }
            
            return health
        except Exception as e:
            logger.error(f"获取应用程序健康状态失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def get_complete_system_report(self) -> Dict[str, Any]:
        """获取完整的系统报告"""
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "system_info": self.get_system_info(),
            "memory_info": self.get_memory_info(),
            "cpu_info": self.get_cpu_info(),
            "disk_info": self.get_disk_info(),
            "network_info": self.get_network_info(),
            "process_info": self.get_process_info(),
            "file_system_stats": self.get_file_system_stats(),
            "application_health": self.get_application_health()
        }

def format_bytes(bytes_value: int) -> str:
    """格式化字节数为可读格式"""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"

def format_duration(seconds: float) -> str:
    """格式化时间长度为可读格式"""
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} 分钟"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f} 小时"
    else:
        return f"{seconds / 86400:.1f} 天"

def get_quick_stats() -> Dict[str, Any]:
    """获取快速统计信息"""
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "memory_usage": f"{memory.percent}%",
            "disk_usage": f"{(disk.used / disk.total) * 100:.1f}%",
            "cpu_usage": f"{psutil.cpu_percent(interval=1)}%",
            "uptime": format_duration((datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).total_seconds()),
            "available_memory": format_bytes(memory.available),
            "free_disk": format_bytes(disk.free)
        }
    except Exception as e:
        logger.error(f"获取快速统计失败: {str(e)}")
        return {"error": str(e)}

def safe_subprocess_run(args: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    安全的subprocess.run包装函数，针对Windows系统中的编码问题进行了优化
    
    Args:
        args: 命令参数列表
        **kwargs: 其他subprocess.run参数
    
    Returns:
        subprocess.CompletedProcess对象
    """
    # 默认设置，可以被传入的kwargs覆盖
    default_kwargs = {
        'encoding': 'utf-8',
        'errors': 'replace',  # 遇到编码错误时用替换字符处理
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'text': True
    }
    
    # 合并默认参数和用户传入的参数
    final_kwargs = {**default_kwargs, **kwargs}
    
    try:
        logger.debug(f"正在执行命令: {' '.join(args)}")
        result = subprocess.run(args, **final_kwargs)
        logger.debug(f"命令执行完成，返回码: {result.returncode}")
        return result
    except UnicodeDecodeError as e:
        logger.warning(f"遇到编码错误，尝试使用系统默认编码: {str(e)}")
        # 如果仍然有编码错误，尝试不指定编码
        fallback_kwargs = {**final_kwargs}
        fallback_kwargs.pop('encoding', None)
        fallback_kwargs['text'] = False
        
        result = subprocess.run(args, **fallback_kwargs)
        
        # 手动解码输出
        if result.stdout:
            try:
                result.stdout = result.stdout.decode('utf-8', errors='replace')
            except:
                try:
                    result.stdout = result.stdout.decode('gbk', errors='replace')
                except:
                    result.stdout = str(result.stdout)
        
        if result.stderr:
            try:
                result.stderr = result.stderr.decode('utf-8', errors='replace')
            except:
                try:
                    result.stderr = result.stderr.decode('gbk', errors='replace')
                except:
                    result.stderr = str(result.stderr)
        
        return result
    except Exception as e:
        logger.error(f"执行命令失败: {str(e)}")
        raise