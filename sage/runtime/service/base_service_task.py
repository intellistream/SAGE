"""
Base Service Task - 服务任务基类

提供统一的服务任务接口，集成高性能mmap队列监听和消息处理功能
"""

import threading
import time
import traceback
import queue
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
from sage.utils.custom_logger import CustomLogger

if TYPE_CHECKING:
    from sage.jobmanager.factory.service_factory import ServiceFactory
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
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.ctx = ctx
        
        # 创建实际的服务实例
        self.service_instance = service_factory.create_service(ctx)
        
        # 为service_instance注入ctx（参考base_task的做法）
        if hasattr(self.service_instance, 'ctx'):
            self.service_instance.ctx = ctx
            self.logger.debug(f"Injected runtime context into service instance '{self.service_name}'")
        
        # 如果service_instance有setup方法，调用它进行初始化
        if hasattr(self.service_instance, 'setup'):
            self.logger.debug(f"Calling setup() method on service instance '{self.service_name}'")
            self.service_instance.setup()
            self.logger.debug(f"Service instance '{self.service_name}' setup completed")
        
        # 提供service别名以便访问
        self.service = self.service_instance
        
        # 基础状态
        self.is_running = False
        self._request_count = 0
        self._error_count = 0
        self._last_activity_time = time.time()
        
        # 日志记录器 - 如果有ctx则使用ctx.logger，否则使用CustomLogger
        self._logger = None
        
        # 高性能队列相关 - 由子类决定具体队列类型
        self._request_queue: Optional[Any] = None
        self._response_queues: Dict[str, Any] = {}  # 缓存响应队列
        self._queue_listener_thread: Optional[threading.Thread] = None
        self._queue_listener_running = False
        
        # 队列名称
        self._request_queue_name = f"service_request_{self.service_name}"
        
        self.logger.info(f"Base service task '{self.service_name}' initialized successfully")
        self.logger.debug(f"Service class: {service_factory.service_class.__name__}")
        self.logger.debug(f"Runtime context: {'provided' if ctx else 'not provided'}")
        self.logger.debug(f"Request queue name: {self._request_queue_name}")
    
    @property
    def logger(self):
        """获取logger，优先使用ctx.logger，否则使用CustomLogger"""
        if not hasattr(self, "_logger") or self._logger is None:
            if self.ctx is None:
                from sage.utils.custom_logger import CustomLogger
                self._logger = CustomLogger(name=f"{self.__class__.__name__}_{self.service_name}")
            else:
                self._logger = self.ctx.logger
        return self._logger
    
    @property
    def name(self):
        """获取service task名称"""
        if self.ctx is not None:
            return self.ctx.name
        return self.service_name
    
    def _initialize_request_queue(self):
        """初始化请求队列 - 由子类实现具体队列类型"""
        self.logger.debug(f"Initializing request queue for service '{self.service_name}'")
        try:
            if self._request_queue is None:
                self._request_queue = self._create_request_queue()
                self.logger.info(f"Successfully initialized request queue: {self._request_queue_name}")
            else:
                self.logger.debug(f"Request queue already initialized for service '{self.service_name}'")
        except Exception as e:
            self.logger.error(f"Failed to initialize request queue for service '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            raise
    
    def _get_response_queue(self, queue_name: str) -> Any:
        """获取或创建响应队列 - 由子类实现具体队列类型"""
        if queue_name not in self._response_queues:
            self.logger.debug(f"Creating new response queue: {queue_name} for service '{self.service_name}'")
            try:
                self._response_queues[queue_name] = self._create_response_queue(queue_name)
                self.logger.debug(f"Successfully created response queue: {queue_name}")
            except Exception as e:
                self.logger.error(f"Failed to create response queue {queue_name} for service '{self.service_name}': {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                raise
        else:
            self.logger.debug(f"Reusing existing response queue: {queue_name}")
        
        return self._response_queues[queue_name]
    
    def _start_queue_listener(self):
        """启动队列监听线程"""
        if self._queue_listener_thread is not None and self._queue_listener_thread.is_alive():
            self.logger.warning(f"Queue listener thread is already running for service '{self.service_name}'")
            return
        
        self.logger.debug(f"Starting queue listener thread for service '{self.service_name}'")
        self._queue_listener_running = True
        self._queue_listener_thread = threading.Thread(
            target=self._queue_listener_loop,
            daemon=True,
            name=f"QueueListener_{self.service_name}"
        )
        self._queue_listener_thread.start()
        self.logger.info(f"Successfully started queue listener thread for service '{self.service_name}'")
    
    def _stop_queue_listener(self):
        """停止队列监听线程"""
        if self._queue_listener_thread is None:
            self.logger.debug(f"No queue listener thread to stop for service '{self.service_name}'")
            return
        
        self.logger.debug(f"Stopping queue listener thread for service '{self.service_name}'")
        self._queue_listener_running = False
        
        # 等待线程结束（最多等待5秒）
        self._queue_listener_thread.join(timeout=5.0)
        
        if self._queue_listener_thread.is_alive():
            self.logger.warning(f"Queue listener thread did not stop gracefully for service '{self.service_name}'")
        else:
            self.logger.info(f"Queue listener thread stopped successfully for service '{self.service_name}'")
        
        self._queue_listener_thread = None
    
    def _queue_listener_loop(self):
        """队列监听循环"""
        self.logger.info(f"Queue listener loop started for service '{self.service_name}'")
        request_count = 0
        
        while self._queue_listener_running:
            try:
                if self._request_queue is None:
                    self.logger.debug(f"Request queue not initialized for service '{self.service_name}', waiting...")
                    time.sleep(0.1)
                    continue
                
                # 从请求队列获取消息（超时1秒）
                try:
                    request_data = self._queue_get(self._request_queue, timeout=1.0)
                    request_count += 1
                    self.logger.debug(f"Received request #{request_count} for service '{self.service_name}': {request_data.get('request_id', 'unknown')}")
                    self._handle_service_request(request_data)
                    
                except Exception as e:
                    # 如果是队列关闭，直接退出循环
                    if "closed" in str(e).lower() or "Queue is closed" in str(e):
                        self.logger.info(f"Request queue closed for service '{self.service_name}', stopping listener")
                        break
                    # 忽略超时和空队列错误（包括queue.Empty异常）
                    elif (isinstance(e, queue.Empty) or 
                          "timed out" in str(e).lower() or 
                          "empty" in str(e).lower()):
                        # 这些是正常的超时/空队列情况，不需要记录错误
                        pass
                    else:
                        self.logger.error(f"Error receiving request for service '{self.service_name}': {e}")
                        self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                
            except Exception as e:
                # 如果是队列关闭相关错误，直接退出循环
                if "closed" in str(e).lower() or "Queue is closed" in str(e):
                    self.logger.info(f"Queue closed for service '{self.service_name}', stopping listener loop")
                    break
                else:
                    self.logger.error(f"Error in queue listener loop for service '{self.service_name}': {e}")
                    self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                    time.sleep(1.0)
        
        self.logger.info(f"Queue listener loop ended for service '{self.service_name}', processed {request_count} requests")
    
    def handle_request(self, request_data: Dict[str, Any]):
        """
        处理服务请求（新接口，直接处理不通过队列）
        
        Args:
            request_data: 请求数据
        """
        request_id = request_data.get('request_id', 'unknown')
        method_name = request_data.get('method_name', 'unknown')
        
        self.logger.info(f"Handling direct service request {request_id} for service '{self.service_name}', method: {method_name}")
        
        try:
            self._last_activity_time = time.time()
            request_start_time = time.time()
            
            # 解析请求数据
            args = request_data.get('args', ())
            kwargs = request_data.get('kwargs', {})
            response_queue = request_data.get('response_queue')
            timeout = request_data.get('timeout', 30.0)
            
            self.logger.debug(
                f"Processing direct service request {request_id} for service '{self.service_name}': "
                f"method={method_name}, args={args}, kwargs={kwargs}, timeout={timeout}"
            )
            
            # 调用服务方法
            try:
                self.logger.debug(f"Calling method '{method_name}' on service '{self.service_name}'")
                result = self.call_method(method_name, *args, **kwargs)
                success = True
                error_msg = None
                self.logger.debug(f"Method '{method_name}' completed successfully for service '{self.service_name}'")
            except Exception as e:
                result = None
                success = False
                error_msg = str(e)
                self.logger.error(f"Service method '{method_name}' call failed for service '{self.service_name}': {e}")
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
            
            # 发送响应到响应队列
            if response_queue:
                self.logger.debug(f"Sending response for request {request_id} to response queue")
                self._send_response_to_queue(response_queue, response_data)
            else:
                self.logger.debug(f"No response queue specified for request {request_id}")
            
            self.logger.info(
                f"Completed direct service request {request_id} for service '{self.service_name}' "
                f"in {execution_time:.3f}s, success={success}"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling direct service request {request_id} for service '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def _send_response_to_queue(self, response_queue, response_data: Dict[str, Any]):
        """
        发送响应到指定的队列对象
        
        Args:
            response_queue: 响应队列对象（可能是Python queue或Ray queue）
            response_data: 响应数据
        """
        request_id = response_data.get('request_id', 'unknown')
        
        try:
            self.logger.debug(f"Sending response for request {request_id} to queue type: {type(response_queue).__name__}")
            
            # 根据队列类型使用不同的put方法
            if hasattr(response_queue, 'put_nowait'):
                # Python标准队列
                response_queue.put_nowait(response_data)
                self.logger.debug(f"Response sent via put_nowait for request {request_id}")
            elif hasattr(response_queue, 'put'):
                # Ray队列或其他支持put的队列
                response_queue.put(response_data, block=False)
                self.logger.debug(f"Response sent via put for request {request_id}")
            else:
                self.logger.error(f"Unknown response queue type: {type(response_queue)} for request {request_id}")
                return
            
            self.logger.debug(f"Successfully sent response for request {request_id} to {type(response_queue).__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to send response for request {request_id} to queue: {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")

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
            self._queue_put(response_queue, response_data, timeout=5.0)
            
            self.logger.debug(f"Sent response to queue {response_queue_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send response to {response_queue_name}: {e}")
    
    def start_running(self):
        """启动服务任务"""
        if self.is_running:
            self.logger.warning(f"Service task '{self.service_name}' is already running")
            return
        
        self.logger.info(f"Starting service task '{self.service_name}'")
        
        try:
            # 初始化请求队列
            self.logger.debug(f"Step 1: Initializing request queue for service '{self.service_name}'")
            self._initialize_request_queue()
            
            # 启动队列监听
            self.logger.debug(f"Step 2: Starting queue listener for service '{self.service_name}'")
            self._start_queue_listener()
            
            # 启动服务实例
            self.logger.debug(f"Step 3: Starting service instance for service '{self.service_name}'")
            self._start_service_instance()
            
            self.is_running = True
            self.logger.info(f"Service task '{self.service_name}' started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start service task '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            self.cleanup()
            raise
    
    def stop(self):
        """停止服务任务"""
        if not self.is_running:
            self.logger.warning(f"Service task '{self.service_name}' is not running")
            return
        
        self.logger.info(f"Stopping service task '{self.service_name}'")
        self.is_running = False
        
        try:
            # 停止队列监听
            self.logger.debug(f"Step 1: Stopping queue listener for service '{self.service_name}'")
            self._stop_queue_listener()
            
            # 停止服务实例
            self.logger.debug(f"Step 2: Stopping service instance for service '{self.service_name}'")
            self._stop_service_instance()
            
            self.logger.info(f"Service task '{self.service_name}' stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping service task '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
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
        self.logger.debug(f"Calling method '{method_name}' on service '{self.service_name}' with args={args}, kwargs={kwargs}")
        
        try:
            self._request_count += 1
            
            if not hasattr(self.service_instance, method_name):
                error_msg = f"Service '{self.service_name}' does not have method '{method_name}'"
                self.logger.error(error_msg)
                raise AttributeError(error_msg)
            
            method = getattr(self.service_instance, method_name)
            self.logger.debug(f"Retrieved method '{method_name}' from service instance '{self.service_name}'")
            
            start_time = time.time()
            result = method(*args, **kwargs)
            execution_time = time.time() - start_time
            
            self.logger.debug(f"Method '{method_name}' on service '{self.service_name}' completed in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error calling method '{method_name}' on service '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
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
        base_stats = {
            "service_name": self.service_name,
            "service_type": self.__class__.__name__,
            "is_running": self.is_running,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "last_activity_time": self._last_activity_time,
            "service_class": self.service_factory.service_class.__name__,
            "request_queue_name": self._request_queue_name,
            "response_queues_count": len(self._response_queues)
        }
        
        # 添加队列统计信息
        if self._request_queue:
            try:
                # 尝试获取队列统计信息，如果失败则忽略
                if hasattr(self._request_queue, 'get_stats'):
                    queue_stats = self._request_queue.get_stats()
                    base_stats["queue_stats"] = queue_stats
                elif hasattr(self._request_queue, 'qsize'):
                    # Python标准队列只提供qsize方法
                    base_stats["queue_stats"] = {"size": self._request_queue.qsize()}
            except Exception as e:
                self.logger.debug(f"Failed to get queue stats: {e}")
        
        return base_stats
    
    def cleanup(self):
        """清理服务任务资源"""
        self.logger.info(f"Starting cleanup for service task '{self.service_name}'")
        
        try:
            # 停止服务
            if self.is_running:
                self.logger.debug(f"Service task '{self.service_name}' is still running, stopping it first")
                self.stop()
            
            # 清理服务实例
            if hasattr(self.service_instance, 'cleanup'):
                self.logger.debug(f"Calling cleanup() on service instance '{self.service_name}'")
                self.service_instance.cleanup()
                self.logger.debug(f"Service instance cleanup completed for '{self.service_name}'")
            elif hasattr(self.service_instance, 'close'):
                self.logger.debug(f"Calling close() on service instance '{self.service_name}'")
                self.service_instance.close()
                self.logger.debug(f"Service instance close completed for '{self.service_name}'")
            else:
                self.logger.debug(f"Service instance '{self.service_name}' has no cleanup or close method")
            
            # 关闭队列
            if self._request_queue:
                try:
                    self.logger.debug(f"Closing request queue for service '{self.service_name}'")
                    self._queue_close(self._request_queue)
                    self._request_queue = None
                    self.logger.debug(f"Request queue closed for service '{self.service_name}'")
                except Exception as e:
                    self.logger.warning(f"Error closing request queue for service '{self.service_name}': {e}")
            
            # 关闭响应队列
            if self._response_queues:
                self.logger.debug(f"Closing {len(self._response_queues)} response queues for service '{self.service_name}'")
                for queue_name, queue in self._response_queues.items():
                    try:
                        self._queue_close(queue)
                        self.logger.debug(f"Response queue '{queue_name}' closed for service '{self.service_name}'")
                    except Exception as e:
                        self.logger.warning(f"Error closing response queue '{queue_name}' for service '{self.service_name}': {e}")
                self._response_queues.clear()
            
            self.logger.info(f"Service task '{self.service_name}' cleanup completed successfully")
            self.logger.debug(f"Final statistics - Requests: {self._request_count}, Errors: {self._error_count}")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of service task '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def get_object(self):
        """获取服务对象，用于兼容接口"""
        return self
    
    # 抽象方法 - 子类需要实现
    
    @abstractmethod
    def _create_request_queue(self) -> Any:
        """创建请求队列 - 子类实现具体队列类型"""
        pass
    
    @abstractmethod
    def _create_response_queue(self, queue_name: str) -> Any:
        """创建响应队列 - 子类实现具体队列类型"""
        pass
    
    @abstractmethod
    def _queue_get(self, queue, timeout: float = 1.0) -> Any:
        """从队列获取数据 - 子类实现具体队列的get方法"""
        pass
    
    @abstractmethod
    def _queue_put(self, queue, data: Any, timeout: float = 5.0) -> None:
        """向队列放入数据 - 子类实现具体队列的put方法"""
        pass
    
    @abstractmethod
    def _queue_close(self, queue) -> None:
        """关闭队列 - 子类实现具体队列的close方法"""
        pass
    
    @abstractmethod
    def _start_service_instance(self):
        """启动服务实例 - 子类实现具体逻辑"""
        pass
    
    @abstractmethod
    def _stop_service_instance(self):
        """停止服务实例 - 子类实现具体逻辑"""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.service_name}: {self.service_factory.service_class.__name__}>"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
