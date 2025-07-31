"""
Base Service Task - 服务任务基类

提供统一的服务任务接口，集成高性能mmap队列监听和消息处理功能
"""

import threading
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
from sage.utils.custom_logger import CustomLogger
from sage.utils.queue_adapter import create_queue

if TYPE_CHECKING:
    from sage.runtime.factory.service_factory import ServiceFactory
    from sage.runtime.runtime_context import RuntimeContext


class BaseServiceTask(ABC):
    """
    服务任务基类
    
    提供统一的服务接口和高性能队列监听功能
    所有服务任务（本地和远程）都应该继承此基类
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'RuntimeContext' = None):
        """
        初始化基础服务任务
        
        Args:
            service_factory: 服务工厂实例
            ctx: 运行时上下文
        """
        # 初始化默认值，防止在初始化失败时访问未定义的属性
        self.service_name = "Unknown"
        self.service_factory = None
        self.ctx = ctx
        self.service_instance = None
        self.service = None
        self.is_running = False
        self._request_count = 0
        self._error_count = 0
        self._last_activity_time = time.time()
        self._request_queue = None
        self._response_queues = {}
        self._queue_listener_thread = None
        self._queue_listener_running = False
        self._request_queue_name = "unknown_request_queue"
        
        # 确保 service_factory 有必要的属性
        if not hasattr(service_factory, 'service_name'):
            raise ValueError("ServiceFactory missing required attribute: service_name")
        if not hasattr(service_factory, 'service_class'):
            raise ValueError("ServiceFactory missing required attribute: service_class")
            
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        
        # 创建实际的服务实例
        self.service_instance = service_factory.create_service(ctx)
        # 提供service别名以便访问
        self.service = self.service_instance
        
        # 队列名称
        self._request_queue_name = f"service_request_{self.service_name}"
        
        self.logger.debug(f"Base service task '{self.service_name}' initialized")
    
    def _initialize_request_queue(self):
        """初始化请求队列"""
        try:
            if self._request_queue is None:
                self._request_queue = create_queue(name=self._request_queue_name)
                self.logger.info(f"Initialized request queue: {self._request_queue_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize request queue: {e}")
            raise
    
    def _get_response_queue(self, queue_name: str):
        """获取或创建响应队列"""
        if queue_name not in self._response_queues:
            try:
                self._response_queues[queue_name] = create_queue(name=queue_name)
                self.logger.debug(f"Created response queue: {queue_name}")
            except Exception as e:
                self.logger.error(f"Failed to create response queue {queue_name}: {e}")
                raise
        
        return self._response_queues[queue_name]
    
    def _start_queue_listener(self):
        """启动队列监听线程"""
        if self._queue_listener_thread is not None and self._queue_listener_thread.is_alive():
            self.logger.warning("Queue listener thread is already running")
            return
        
        self._queue_listener_running = True
        self._queue_listener_thread = threading.Thread(
            target=self._queue_listener_loop,
            daemon=True,
            name=f"QueueListener_{self.service_name}"
        )
        self._queue_listener_thread.start()
        self.logger.info(f"Started queue listener thread for service {self.service_name}")
    
    def _stop_queue_listener(self):
        """停止队列监听线程"""
        if self._queue_listener_thread is None:
            return
        
        self._queue_listener_running = False
        
        # 等待线程结束（最多等待5秒）
        self._queue_listener_thread.join(timeout=5.0)
        
        if self._queue_listener_thread.is_alive():
            self.logger.warning("Queue listener thread did not stop gracefully")
        else:
            self.logger.info(f"Queue listener thread stopped for service {self.service_name}")
        
        self._queue_listener_thread = None
    
    def _queue_listener_loop(self):
        """队列监听循环"""
        self.logger.debug(f"Queue listener loop started for service {self.service_name}")
        
        while self._queue_listener_running:
            try:
                if self._request_queue is None:
                    time.sleep(0.1)
                    continue
                
                # 从请求队列获取消息（超时1秒）
                try:
                    request_data = self._request_queue.get(timeout=1.0)
                    self._handle_service_request(request_data)
                    
                except Exception as e:
                    # 如果是队列关闭，直接退出循环
                    if "closed" in str(e).lower() or "Queue is closed" in str(e):
                        self.logger.debug("Request queue closed, stopping listener")
                        break
                    # 忽略超时和空队列错误
                    elif "timed out" not in str(e).lower() and "empty" not in str(e).lower():
                        self.logger.error(f"Error receiving request: {e}")
                
            except Exception as e:
                # 如果是队列关闭相关错误，直接退出循环
                if "closed" in str(e).lower() or "Queue is closed" in str(e):
                    self.logger.debug("Queue closed, stopping listener loop")
                    break
                else:
                    self.logger.error(f"Error in queue listener loop: {e}")
                    time.sleep(1.0)
        
        self.logger.debug(f"Queue listener loop ended for service {self.service_name}")
    
    def _handle_service_request(self, request_data: Dict[str, Any]):
        """
        处理服务请求
        
        Args:
            request_data: 请求数据，格式与ServiceRequest兼容
        """
        try:
            self._last_activity_time = time.time()
            request_start_time = time.time()
            
            # 解析请求数据
            request_id = request_data.get('request_id')
            method_name = request_data.get('method_name')
            args = request_data.get('args', ())
            kwargs = request_data.get('kwargs', {})
            response_queue_name = request_data.get('response_queue')
            timeout = request_data.get('timeout', 30.0)
            
            self.logger.debug(
                f"Processing service request {request_id}: {method_name} "
                f"with args={args}, kwargs={kwargs}"
            )
            
            # 调用服务方法
            try:
                result = self.call_method(method_name, *args, **kwargs)
                success = True
                error_msg = None
            except Exception as e:
                result = None
                success = False
                error_msg = str(e)
                self.logger.error(f"Service method call failed: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            
            # 计算执行时间
            execution_time = time.time() - request_start_time
            
            # 构造响应数据
            response_data = {
                'request_id': request_id,
                'result': result,
                'error': error_msg,
                'success': success,
                'execution_time': execution_time,
                'timestamp': time.time()
            }
            
            # 发送响应
            if response_queue_name:
                self._send_response(response_queue_name, response_data)
            
            self.logger.debug(
                f"Completed service request {request_id} in {execution_time:.3f}s, "
                f"success={success}"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling service request: {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def _send_response(self, response_queue_name: str, response_data: Dict[str, Any]):
        """
        发送响应到响应队列
        
        Args:
            response_queue_name: 响应队列名称
            response_data: 响应数据
        """
        try:
            response_queue = self._get_response_queue(response_queue_name)
            response_queue.put(response_data, timeout=5.0)
            
            self.logger.debug(f"Sent response to queue {response_queue_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send response to {response_queue_name}: {e}")
    
    def start_running(self):
        """启动服务任务"""
        if self.is_running:
            self.logger.warning(f"Service task {self.service_name} is already running")
            return
        
        try:
            # 初始化请求队列
            self._initialize_request_queue()
            
            # 启动队列监听
            self._start_queue_listener()
            
            # 启动服务实例
            self._start_service_instance()
            
            self.is_running = True
            self.logger.info(f"Service task {self.service_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start service task {self.service_name}: {e}")
            self.cleanup()
            raise
    
    def stop(self):
        """停止服务任务"""
        if not self.is_running:
            self.logger.warning(f"Service task {self.service_name} is not running")
            return
        
        self.is_running = False
        
        try:
            # 停止队列监听
            self._stop_queue_listener()
            
            # 停止服务实例
            self._stop_service_instance()
            
            self.logger.info(f"Service task {self.service_name} stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service task {self.service_name}: {e}")
    
    def terminate(self):
        """终止服务任务（别名方法）"""
        if hasattr(self.service_instance, 'terminate'):
            self.service_instance.terminate()
        else:
            self.stop()
    
    def call_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        调用服务方法
        
        Args:
            method_name: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            方法调用结果
        """
        try:
            self._request_count += 1
            
            if not hasattr(self.service_instance, method_name):
                raise AttributeError(f"Service {self.service_name} does not have method '{method_name}'")
            
            method = getattr(self.service_instance, method_name)
            result = method(*args, **kwargs)
            
            self.logger.debug(f"Called method {method_name} on service {self.service_name}")
            return result
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error calling method {method_name} on service {self.service_name}: {e}")
            raise
    
    def get_attribute(self, attr_name: str) -> Any:
        """获取服务属性"""
        if not hasattr(self.service_instance, attr_name):
            raise AttributeError(f"Service {self.service_name} does not have attribute '{attr_name}'")
        
        return getattr(self.service_instance, attr_name)
    
    def set_attribute(self, attr_name: str, value: Any):
        """设置服务属性"""
        setattr(self.service_instance, attr_name, value)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        # 安全地获取服务类名
        service_class_name = "Unknown"
        if hasattr(self, 'service_factory') and hasattr(self.service_factory, 'service_class'):
            if self.service_factory.service_class is not None:
                service_class_name = self.service_factory.service_class.__name__
        
        base_stats = {
            "service_name": getattr(self, 'service_name', 'Unknown'),
            "service_type": self.__class__.__name__,
            "is_running": getattr(self, 'is_running', False),
            "request_count": getattr(self, '_request_count', 0),
            "error_count": getattr(self, '_error_count', 0),
            "last_activity_time": getattr(self, '_last_activity_time', 0),
            "service_class": service_class_name,
            "request_queue_name": getattr(self, '_request_queue_name', 'Unknown'),
            "response_queues_count": len(getattr(self, '_response_queues', {}))
        }
        
        # 添加队列统计信息
        if self._request_queue:
            try:
                queue_stats = self._request_queue.get_stats()
                base_stats["queue_stats"] = queue_stats
            except Exception as e:
                self.logger.debug(f"Failed to get queue stats: {e}")
        
        return base_stats
    
    def cleanup(self):
        """清理服务任务资源"""
        self.logger.info(f"Cleaning up service task {self.service_name}")
        
        try:
            # 停止服务
            if self.is_running:
                self.stop()
            
            # 清理服务实例
            if hasattr(self.service_instance, 'cleanup'):
                self.service_instance.cleanup()
            elif hasattr(self.service_instance, 'close'):
                self.service_instance.close()
            
            # 关闭队列
            if self._request_queue:
                try:
                    self._request_queue.close()
                    self._request_queue = None
                except Exception as e:
                    self.logger.warning(f"Error closing request queue: {e}")
            
            # 关闭响应队列
            for queue_name, queue in self._response_queues.items():
                try:
                    queue.close()
                except Exception as e:
                    self.logger.warning(f"Error closing response queue {queue_name}: {e}")
            self._response_queues.clear()
            
            self.logger.debug(f"Service task {self.service_name} cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of service task {self.service_name}: {e}")
    
    def get_object(self):
        """获取服务对象，用于兼容接口"""
        return self
    
    # 抽象方法 - 子类需要实现
    
    @abstractmethod
    def _start_service_instance(self):
        """启动服务实例 - 子类实现具体逻辑"""
        pass
    
    @abstractmethod
    def _stop_service_instance(self):
        """停止服务实例 - 子类实现具体逻辑"""
        pass
    
    def __repr__(self) -> str:
        service_name = getattr(self, 'service_name', 'Unknown')
        service_factory = getattr(self, 'service_factory', None)
        if service_factory and hasattr(service_factory, 'service_class') and service_factory.service_class is not None:
            service_class_name = service_factory.service_class.__name__
        else:
            service_class_name = 'Unknown'
        return f"<{self.__class__.__name__} {service_name}: {service_class_name}>"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    @property
    def logger(self):
        """获取当前任务的日志记录器"""
        return self.ctx.logger