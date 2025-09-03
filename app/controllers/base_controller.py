"""
Base controller for MarkEdit application.

This module provides common functionality for all controllers to reduce code duplication.
"""
import logging
from typing import Any, Dict, Optional, Union, Callable, List
from functools import wraps

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# 导入权限检查混入类
try:
    from .permission_mixin import PermissionMixin
except ImportError:
    # 处理循环导入或文件不存在的情况
    PermissionMixin = object

logger = logging.getLogger(__name__)

class BaseController(PermissionMixin):
    """基础Controller类，提供通用的控制器功能，包含CRUD和管理功能"""
    
    def __init__(self, controller_name: str = None):
        """初始化基础controller"""
        # 初始化权限检查混入类
        super().__init__()
        
        self.controller_name = controller_name or self.__class__.__name__
        self.logger = logging.getLogger(f"app.controllers.{self.controller_name.lower()}")
        
        # 服务实例的延迟加载
        self._services = {}
    
    def get_service(self, service_name: str):
        """延迟加载服务实例以避免循环导入"""
        if service_name not in self._services:
            from app.common import (
                get_admin_service, get_build_service, get_epub_service,
                get_file_service, get_user_service, get_session_service
            )
            
            service_map = {
                'admin': get_admin_service,
                'build': get_build_service, 
                'epub': get_epub_service,
                'file': get_file_service,
                'user': get_user_service,
                'session': get_session_service
            }
            
            if service_name in service_map:
                self._services[service_name] = service_map[service_name]()
            else:
                raise ValueError(f"Unknown service: {service_name}")
                
        return self._services[service_name]
    
    async def parse_request_json(self, request: Request, 
                                required_fields: list = None) -> Dict[str, Any]:
        """安全地解析请求的JSON数据，支持必需字段验证"""
        try:
            body = await request.json()
            
            # 验证必需字段
            if required_fields:
                missing_fields = [field for field in required_fields if field not in body]
                if missing_fields:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"缺少必需字段: {', '.join(missing_fields)}"
                    )
            
            return body
            
        except ValueError as e:
            self.logger.error(f"JSON解析失败: {str(e)}")
            raise HTTPException(status_code=400, detail="无效的JSON格式")
        except Exception as e:
            self.logger.error(f"请求解析异常: {str(e)}")
            raise HTTPException(status_code=500, detail="请求解析失败")
    
    def handle_controller_exception(self, operation_name: str):
        """统一的controller异常处理装饰器"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    # 重新抛出HTTP异常
                    raise
                except ValueError as e:
                    # 业务逻辑错误
                    self.logger.warning(f"{operation_name}业务异常: {str(e)}")
                    raise HTTPException(status_code=400, detail=str(e))
                except FileNotFoundError as e:
                    # 文件未找到错误
                    self.logger.warning(f"{operation_name}文件未找到: {str(e)}")
                    raise HTTPException(status_code=404, detail=str(e))
                except PermissionError as e:
                    # 权限错误
                    self.logger.warning(f"{operation_name}权限错误: {str(e)}")
                    raise HTTPException(status_code=403, detail=str(e))
                except Exception as e:
                    # 系统异常
                    self.logger.error(f"{operation_name}失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
            return wrapper
        return decorator
    
    def create_success_response(self, data: Any = None, 
                              message: str = "操作成功") -> Dict[str, Any]:
        """创建标准的成功响应"""
        response = {
            "status": "success",
            "message": message
        }
        
        if data is not None:
            if isinstance(data, dict):
                response.update(data)
            else:
                response["data"] = data
        
        return response
    
    def create_error_response(self, message: str, 
                            error_code: str = None,
                            details: Any = None) -> Dict[str, Any]:
        """创建标准的错误响应"""
        response = {
            "status": "error",
            "message": message
        }
        
        if error_code:
            response["error_code"] = error_code
        
        if details:
            response["details"] = details
        
        return response
    
    def validate_required_params(self, data: Dict[str, Any], 
                                required_params: list) -> None:
        """验证必需参数"""
        missing_params = []
        empty_params = []
        
        for param in required_params:
            if param not in data:
                missing_params.append(param)
            elif not data[param] or (isinstance(data[param], str) and not data[param].strip()):
                empty_params.append(param)
        
        if missing_params:
            raise HTTPException(
                status_code=400, 
                detail=f"缺少必需参数: {', '.join(missing_params)}"
            )
        
        if empty_params:
            raise HTTPException(
                status_code=400, 
                detail=f"参数不能为空: {', '.join(empty_params)}"
            )
    
    def log_operation(self, operation: str, username: str = None, 
                     details: Dict[str, Any] = None) -> None:
        """记录操作日志"""
        log_message = f"操作: {operation}"
        
        if username:
            log_message += f", 用户: {username}"
        
        if details:
            log_message += f", 详情: {details}"
        
        self.logger.info(log_message)
    
    # ===================
    # 通用路由操作模式
    # ===================
    
    async def handle_api_operation(self, operation_type: str, service_name: str,
                                 method_name: str, request: Request = None,
                                 path_params: Dict = None, query_params: Dict = None,
                                 body_data: Dict = None, 
                                 session: 'SessionData' = None,
                                 required_permissions: Union[str, List[str]] = None) -> Dict[str, Any]:
        """通用的API操作处理器
        
        Args:
            operation_type: 操作类型 (list, get, create, update, delete)
            service_name: 服务名称
            method_name: 服务方法名
            request: FastAPI请求对象
            path_params: 路径参数
            query_params: 查询参数  
            body_data: 请求体数据
            session: 用户会话
            required_permissions: 必需的权限列表
        """
        try:
            # 获取会话（如果没有提供）
            if not session and request:
                from app.common import require_auth_session
                session = await require_auth_session(request)
            
            # 权限检查
            if required_permissions and session:
                if isinstance(required_permissions, str):
                    required_permissions = [required_permissions]
                await self._check_user_permissions(session, required_permissions)
            
            # 获取服务实例
            service = self.get_service(service_name)
            method = getattr(service, method_name)
            
            # 准备方法参数
            method_kwargs = {}
            if request:
                method_kwargs['request'] = request
            if path_params:
                method_kwargs.update(path_params)
            if query_params:
                method_kwargs.update(query_params)
            if body_data:
                method_kwargs.update(body_data)
            
            # 执行操作
            if operation_type == "list":
                result = await method(**method_kwargs)
                return self.create_success_response(result)
                
            elif operation_type == "get":
                result = await method(**method_kwargs)
                if not result:
                    raise HTTPException(status_code=404, detail="记录不存在")
                return self.create_success_response(result)
                
            elif operation_type == "create":
                result = await method(**method_kwargs)
                return self.create_success_response(result, "创建成功")
                
            elif operation_type == "update":
                result = await method(**method_kwargs)
                return self.create_success_response(result, "更新成功")
                
            elif operation_type == "delete":
                result = await method(**method_kwargs)
                return self.create_success_response(result, "删除成功")
                
            else:
                raise ValueError(f"不支持的操作类型: {operation_type}")
                
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"API操作失败 [{operation_type}-{service_name}-{method_name}]: {str(e)}")
            raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
    
    async def handle_file_operation(self, operation_type: str, file_type: str,
                                  file_path: str, request: Request, 
                                  session: 'SessionData' = None,
                                  content: str = None, raw: bool = False) -> Any:
        """通用的文件操作处理器
        
        Args:
            operation_type: 操作类型 (read, save, delete, create)
            file_type: 文件类型 (src, build, backup)
            file_path: 文件路径
            request: 请求对象
            session: 用户会话
            content: 文件内容（保存时使用）
            raw: 是否返回原始内容
        """
        try:
            # 参数验证
            self.validate_file_type(file_type)
            self.validate_file_path(file_path)
            
            # 权限检查
            if session:
                await self._check_file_type_permission(session, file_type)
            
            # 获取文件服务
            file_service = self.get_service('file')
            
            # 执行文件操作
            if operation_type == "read":
                result = file_service.read_file(file_type, file_path, request, raw)
                return result
                
            elif operation_type == "save":
                if content is None:
                    body = await request.body()
                    content = body.decode('utf-8')
                result = file_service.save_file(file_type, file_path, content, request)
                return self.create_success_response(result, "文件保存成功")
                
            elif operation_type == "delete":
                result = file_service.delete_file(file_type, file_path, request)
                return self.create_success_response(result, "文件删除成功")
                
            elif operation_type == "create":
                if content is None:
                    content = ""
                result = file_service.create_file(file_path, content, request)
                return self.create_success_response(result, "文件创建成功")
                
            else:
                raise ValueError(f"不支持的文件操作类型: {operation_type}")
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"文件操作失败 [{operation_type}-{file_type}]: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件操作失败: {str(e)}")
    
    def create_route_handler(self, operation_type: str, service_name: str,
                           method_name: str, required_permissions: Union[str, List[str]] = None):
        """创建标准的路由处理器
        
        这是一个工厂方法，用于创建标准化的路由处理函数
        """
        async def route_handler(request: Request, **kwargs):
            from app.common import require_auth_session
            from fastapi import Depends
            
            # 获取会话
            session_dependency = Depends(require_auth_session)
            session = await session_dependency(request)
            
            # 解析参数
            path_params = {k: v for k, v in kwargs.items() if not k.startswith('_')}
            query_params = dict(request.query_params)
            
            # 解析请求体
            body_data = None
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body_data = await request.json()
                except:
                    body_data = {}
            
            return await self.handle_api_operation(
                operation_type=operation_type,
                service_name=service_name,
                method_name=method_name,
                request=request,
                path_params=path_params,
                query_params=query_params,
                body_data=body_data,
                session=session,
                required_permissions=required_permissions
            )
        
        return route_handler
    
    def validate_file_type(self, file_type: str, allowed_types: list = None) -> str:
        """验证文件类型"""
        if allowed_types is None:
            allowed_types = ['src', 'build', 'backup']
        
        if file_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_type}。支持的类型: {', '.join(allowed_types)}"
            )
        
        return file_type
    
    def validate_file_path(self, file_path: str) -> str:
        """验证文件路径安全性"""
        if not file_path:
            raise HTTPException(status_code=400, detail="文件路径不能为空")
        
        # 检查路径是否包含危险字符
        dangerous_patterns = ['..', '//', '\\\\', '|', '&', ';']
        for pattern in dangerous_patterns:
            if pattern in file_path:
                raise HTTPException(status_code=400, detail="文件路径包含非法字符")
        
        return file_path


class CRUDControllerMixin:
    """CRUD操作混入类，提供通用的增删改查功能"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    async def handle_batch_operation(self, service_method: Callable,
                                   batch_data: List[Dict[str, Any]],
                                   operation_name: str = "批量操作") -> Dict[str, Any]:
        """处理批量操作"""
        try:
            results = []
            for item in batch_data:
                result = await service_method(**item)
                results.append(result)
            return self.create_success_response(results, f"{operation_name}成功")
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    async def handle_search_operation(self, service_method: Callable,
                                    search_params: Dict[str, Any],
                                    operation_name: str = "搜索") -> Dict[str, Any]:
        """处理搜索操作"""
        try:
            result = await service_method(**search_params)
            return self.create_success_response(result)
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    async def handle_list_operation(self, service_method: Callable,
                                  operation_name: str = "获取列表") -> Dict[str, Any]:
        """处理列表查询操作"""
        try:
            result = await service_method()
            return self.create_success_response(result)
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    async def handle_get_operation(self, service_method: Callable,
                                 item_id: Union[int, str],
                                 operation_name: str = "获取记录") -> Dict[str, Any]:
        """处理单个记录获取操作"""
        try:
            result = await service_method(item_id)
            if not result:
                raise HTTPException(status_code=404, detail="记录不存在")
            return self.create_success_response(result)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    async def handle_create_operation(self, service_method: Callable,
                                    create_data: Dict[str, Any],
                                    operation_name: str = "创建记录") -> Dict[str, Any]:
        """处理创建操作"""
        try:
            result = await service_method(**create_data)
            return self.create_success_response(result, f"{operation_name}成功")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    async def handle_update_operation(self, service_method: Callable,
                                    item_id: Union[int, str],
                                    update_data: Dict[str, Any],
                                    operation_name: str = "更新记录") -> Dict[str, Any]:
        """处理更新操作"""
        try:
            result = await service_method(item_id, **update_data)
            return self.create_success_response(result, f"{operation_name}成功")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
    
    async def handle_delete_operation(self, service_method: Callable,
                                    item_id: Union[int, str],
                                    operation_name: str = "删除记录") -> Dict[str, Any]:
        """处理删除操作"""
        try:
            result = await service_method(item_id)
            return self.create_success_response(result, f"{operation_name}成功")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")


class FileControllerMixin:
    """文件操作控制器混入类"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_file_type(self, file_type: str, allowed_types: list = None) -> str:
        """验证文件类型"""
        if allowed_types is None:
            allowed_types = ['src', 'build']
        
        if file_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_type}。支持的类型: {', '.join(allowed_types)}"
            )
        
        return file_type
    
    def validate_file_path(self, file_path: str) -> str:
        """验证文件路径安全性"""
        if not file_path:
            raise HTTPException(status_code=400, detail="文件路径不能为空")
        
        # 检查路径是否包含危险字符
        dangerous_patterns = ['..', '//', '\\\\', '|', '&', ';']
        for pattern in dangerous_patterns:
            if pattern in file_path:
                raise HTTPException(status_code=400, detail="文件路径包含非法字符")
        
        return file_path
    
    async def handle_file_read_operation(self, service_method: Callable,
                                       file_type: str, file_path: str,
                                       request: Request,
                                       raw: bool = False) -> Any:
        """处理文件读取操作"""
        try:
            # 验证参数
            self.validate_file_type(file_type)
            self.validate_file_path(file_path)
            
            # 调用服务方法
            return service_method(file_type, file_path, request, raw)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"读取文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    async def handle_file_save_operation(self, service_method: Callable,
                                       file_type: str, file_path: str,
                                       request: Request) -> Dict[str, Any]:
        """处理文件保存操作"""
        try:
            # 验证参数
            self.validate_file_type(file_type)
            self.validate_file_path(file_path)
            
            # 调用服务方法
            result = service_method(file_type, file_path, request)
            return self.create_success_response(result, "文件保存成功")
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")


class AdminControllerMixin:
    """管理员控制器混入类，提供管理功能的通用方法"""
    
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    # === 通用管理操作方法 ===
    async def handle_generic_admin_operation(self, operation_type: str, 
                                           service_name: str,
                                           method_name: str,
                                           request_data: Dict[str, Any] = None,
                                           item_id: Union[int, str] = None) -> Dict[str, Any]:
        """处理通用管理操作（用户、角色、权限等）"""
        try:
            service = self.get_service(service_name)
            method = getattr(service, method_name)
            
            if operation_type == "list":
                result = await method()
                return {f"{service_name}s": result}
            elif operation_type == "create":
                result = await method(**request_data)
                return self.create_success_response(result, f"{service_name}创建成功")
            elif operation_type == "update":
                result = await method(item_id, **request_data)
                return self.create_success_response(result, f"{service_name}更新成功")
            elif operation_type == "delete":
                result = await method(item_id)
                return self.create_success_response(result, f"{service_name}删除成功")
            else:
                raise ValueError(f"不支持的操作类型: {operation_type}")
                
        except Exception as e:
            self.logger.error(f"{service_name}{operation_type}操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
    
    def admin_exception_handler(self, operation_name: str):
        """管理员操作专用的异常处理装饰器"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except ValueError as e:
                    # 业务逻辑错误（如用户不存在、角色不存在等）
                    if "不存在" in str(e):
                        raise HTTPException(status_code=404, detail=str(e))
                    else:
                        raise HTTPException(status_code=400, detail=str(e))
                except PermissionError as e:
                    self.logger.warning(f"{operation_name}权限错误: {str(e)}")
                    raise HTTPException(status_code=403, detail=str(e))
                except Exception as e:
                    self.logger.error(f"{operation_name}失败: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
            return wrapper
        return decorator


def controller_exception_handler(operation_name: str):
    """通用的controller异常处理装饰器（独立函数）"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # 重新抛出HTTP异常
                raise
            except ValueError as e:
                # 业务逻辑错误
                logger.warning(f"{operation_name}业务异常: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except FileNotFoundError as e:
                # 文件未找到错误
                logger.warning(f"{operation_name}文件未找到: {str(e)}")
                raise HTTPException(status_code=404, detail=str(e))
            except PermissionError as e:
                # 权限错误
                logger.warning(f"{operation_name}权限错误: {str(e)}")
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                # 系统异常
                logger.error(f"{operation_name}失败: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
        return wrapper
    return decorator


class UnifiedController(BaseController, CRUDControllerMixin, FileControllerMixin, AdminControllerMixin):
    """统一控制器类，整合所有功能"""
    
    def __init__(self, controller_name: str = None):
        BaseController.__init__(self, controller_name)
        CRUDControllerMixin.__init__(self)
        FileControllerMixin.__init__(self)
        AdminControllerMixin.__init__(self)