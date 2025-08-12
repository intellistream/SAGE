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
from sage.common.utils.logging.custom_logger import CustomLogger

if TYPE_CHECKING:
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.context.service_context import ServiceContext


class BaseServiceTask(ABC):
    """
    服务任务基类
    
    提供统一的服务接口和高性能队列监听功能
    所有服务任务（本地和远程）都应该继承此基类
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        """
        初始化基础服务任务
        
        Args:
            service_factory: 服务工厂实例
            ctx: 服务上下文（ServiceContext）
        """
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.ctx = ctx
        
        # 创建实际的服务实例
        self.service_instance = service_factory.create_service(ctx)
        
        # 为service_instance注入ctx（参考base_task的做法）
        if hasattr(self.service_instance, 'ctx'):
            self.service_instance.ctx = ctx
            self.logger.debug(f"Injected service context into service instance '{self.service_name}'")
        
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
        
        # 队列监听相关
        self._queue_listener_thread: Optional[threading.Thread] = None
        self._queue_listener_running = False
        
        self.logger.info(f"Base service task '{self.service_name}' initialized successfully")
        self.logger.debug(f"Service class: {service_factory.service_class.__name__}")
        self.logger.debug(f"Service context: {'provided' if ctx else 'not provided'}")
        
        # 从ServiceContext获取队列描述符信息
        if ctx:
            request_qd = ctx.get_request_queue_descriptor()
            response_qds = ctx.get_service_response_queue_descriptors()
            self.logger.debug(f"Request queue descriptor: {request_qd}")
            self.logger.debug(f"Response queue descriptors: {len(response_qds)} available")
    
    @property
    def logger(self):
        """获取logger，优先使用ctx.logger，否则使用CustomLogger"""
        if not hasattr(self, "_logger") or self._logger is None:
            if self.ctx is None:
                from sage.common.utils.logging.custom_logger import CustomLogger
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
    
    @property
    def request_queue_descriptor(self):
        """获取请求队列描述符"""
        if self.ctx:
            return self.ctx.get_request_queue_descriptor()
        return None
    
    @property
    def request_queue(self):
        """获取请求队列实例"""
        qd = self.request_queue_descriptor
        if qd:
            return qd.queue_instance
        return None
    
    def get_response_queue_descriptor(self, node_name: str):
        """获取响应队列描述符"""
        if self.ctx:
            return self.ctx.get_service_response_queue_descriptor(node_name)
        return None
    
    def get_response_queue(self, node_name: str):
        """获取响应队列实例"""
        qd = self.get_response_queue_descriptor(node_name)
        if qd:
            return qd.queue_instance
        return None
    
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
        """队列监听循环 - 使用ServiceContext中的队列描述符"""
        self.logger.info(f"Queue listener loop started for service '{self.service_name}'")
        request_count = 0
        
        while self._queue_listener_running:
            try:
                # 从ServiceContext获取请求队列
                request_queue = self.request_queue
                if request_queue is None:
                    self.logger.debug(f"Request queue not available for service '{self.service_name}', waiting...")
                    time.sleep(0.1)
                    continue
                
                # 从请求队列获取消息（超时1秒）
                try:
                    request_data = request_queue.get(block=True, timeout=1.0)
                    request_count += 1
                    request_id = request_data.get('request_id', 'unknown')
                    method_name = request_data.get('method_name', 'unknown')
                    self.logger.info(f"[SERVICE_TASK] Received request #{request_count} for service '{self.service_name}': {method_name} (request_id: {request_id})")
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
        发送响应到指定的队列对象（修正版本）
        
        Args:
            response_queue: 响应队列对象（来自ServiceManager的队列实例）
            response_data: 响应数据
        """
        request_id = response_data.get('request_id', 'unknown')
        
        try:
            self.logger.info(f"[SERVICE_TASK] Starting response send for request {request_id}")
            self.logger.info(f"[SERVICE_TASK] Response queue type: {type(response_queue).__name__}")
            self.logger.debug(f"[SERVICE_TASK] Response data: {response_data}")
            
            # 使用阻塞的put方法，确保消息被成功发送
            if hasattr(response_queue, 'put'):
                send_start_time = time.time()
                # 使用阻塞put，超时10秒
                response_queue.put(response_data, block=True, timeout=10.0)
                send_time = time.time() - send_start_time
                self.logger.info(f"[SERVICE_TASK] Response sent successfully for request {request_id} in {send_time:.3f}s")
            else:
                self.logger.error(f"[SERVICE_TASK] Unknown response queue type: {type(response_queue)} for request {request_id}")
                return
            
        except Exception as e:
            self.logger.error(f"[SERVICE_TASK] Failed to send response for request {request_id}: {e}")
            self.logger.error(f"[SERVICE_TASK] Exception type: {type(e).__name__}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            # 不要抛出异常，避免影响服务任务的继续运行

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
            response_queue = request_data.get('response_queue')  # 现在这是队列实例而不是名称
            response_queue_name = request_data.get('response_queue_name', 'unknown')  # 用于日志的名称
            timeout = request_data.get('timeout', 30.0)
            
            self.logger.info(
                f"[SERVICE_TASK] Processing service request {request_id}: {method_name} "
                f"with args={args}, kwargs={kwargs}"
            )
            
            # 调用服务方法
            try:
                self.logger.debug(f"[SERVICE_TASK] Calling service method {method_name}")
                result = self.call_method(method_name, *args, **kwargs)
                success = True
                error_msg = None
                self.logger.info(f"[SERVICE_TASK] Service method {method_name} succeeded: {result}")
            except Exception as e:
                result = None
                success = False
                error_msg = str(e)
                self.logger.error(f"[SERVICE_TASK] Service method call failed: {e}")
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
            if response_queue:
                # 如果response_queue是字符串，需要通过ServiceContext获取实际队列实例
                if isinstance(response_queue, str):
                    actual_queue = self.get_response_queue(response_queue)
                    queue_name = response_queue
                    if actual_queue:
                        self.logger.info(f"[SERVICE_TASK] Sending response for request {request_id} to queue '{queue_name}'")
                        self._send_response_to_queue(actual_queue, response_data)
                    else:
                        self.logger.error(f"[SERVICE_TASK] Response queue '{queue_name}' not found in service context for request {request_id}")
                else:
                    # response_queue已经是队列实例
                    self.logger.info(f"[SERVICE_TASK] Sending response for request {request_id} to queue {response_queue_name}")
                    self._send_response_to_queue(response_queue, response_data)
            else:
                self.logger.warning(f"[SERVICE_TASK] No response queue specified for request {request_id}")
                
            self.logger.info(
                f"[SERVICE_TASK] Completed service request {request_id} in {execution_time:.3f}s, "
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
    def _send_response(self, response_queue_name: str, response_data: Dict[str, Any]):
        """
        发送响应到响应队列
        
        ServiceManager发送请求时会指定自己的响应队列名称，
        BaseServiceTask通过这个名称找到对应的响应队列并发送响应。
        
        Args:
            response_queue_name: 响应队列名称 (来自ServiceManager的_response_queue_name)
            response_data: 响应数据
        """
        request_id = response_data.get('request_id', 'unknown')
        
        try:
            self.logger.info(f"[SERVICE_TASK] Starting response send process for request {request_id}")
            self.logger.info(f"[SERVICE_TASK] Target response queue name: '{response_queue_name}'")
            self.logger.debug(f"[SERVICE_TASK] Response data: {response_data}")
            
            # 通过队列名称创建/获取队列实例（与ServiceManager的_get_response_queue方法保持一致）
            self.logger.debug(f"[SERVICE_TASK] Creating queue instance for: '{response_queue_name}'")
            response_queue = create_queue(name=response_queue_name)
            self.logger.info(f"[SERVICE_TASK] Created response queue instance type: {type(response_queue).__name__}")
            
            # 发送响应数据 - 使用阻塞模式确保响应被发送
            self.logger.info(f"[SERVICE_TASK] Attempting to put response data to queue '{response_queue_name}' for request {request_id}")
            send_start_time = time.time()
            response_queue.put(response_data, timeout=10.0)  # 增加超时时间到10秒
            send_time = time.time() - send_start_time
            
            self.logger.info(f"[SERVICE_TASK] Successfully sent response for request {request_id} to queue '{response_queue_name}' in {send_time:.3f}s")
            
        except Exception as e:
            self.logger.error(f"[SERVICE_TASK] Failed to send response for request {request_id} to '{response_queue_name}': {e}")
            self.logger.error(f"[SERVICE_TASK] Exception type: {type(e).__name__}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            # 不要抛出异常，避免影响服务任务的继续运行
            # raise
    
    def start_running(self):
        """启动服务任务"""
        if self.is_running:
            self.logger.warning(f"Service task '{self.service_name}' is already running")
            return
        
        self.logger.info(f"Starting service task '{self.service_name}'")
        
        try:
            # 检查ServiceContext中的队列描述符
            if self.ctx:
                request_qd = self.request_queue_descriptor
                if request_qd:
                    self.logger.debug(f"Found request queue descriptor: {request_qd}")
                else:
                    self.logger.warning(f"No request queue descriptor found in service context")
                    
                response_qds = self.ctx.get_service_response_queue_descriptors()
                self.logger.debug(f"Found {len(response_qds)} response queue descriptors")
            else:
                self.logger.warning(f"No service context provided for service '{self.service_name}'")
            
            # 启动队列监听
            self.logger.debug(f"Starting queue listener for service '{self.service_name}'")
            self._start_queue_listener()
            
            # 启动服务实例
            self.logger.debug(f"Starting service instance for service '{self.service_name}'")
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
            "has_service_context": self.ctx is not None
        }
        
        # 添加ServiceContext队列信息
        if self.ctx:
            request_qd = self.request_queue_descriptor
            response_qds = self.ctx.get_service_response_queue_descriptors()
            
            base_stats.update({
                "request_queue_available": request_qd is not None,
                "request_queue_id": request_qd.queue_id if request_qd else None,
                "request_queue_type": request_qd.queue_type if request_qd else None,
                "response_queues_count": len(response_qds),
                "response_queue_names": list(response_qds.keys()) if response_qds else []
            })
        
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
            
            # 队列清理现在由ServiceContext管理，这里不需要直接清理队列
            self.logger.debug(f"Queue cleanup is managed by ServiceContext for service '{self.service_name}'")
            
            self.logger.info(f"Service task '{self.service_name}' cleanup completed successfully")
            self.logger.debug(f"Final statistics - Requests: {self._request_count}, Errors: {self._error_count}")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of service task '{self.service_name}': {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def get_object(self):
        """获取服务对象，用于兼容接口"""
        return self
    
    # 抽象方法 - 子类需要实现（仅保留服务实例管理相关的抽象方法）
    
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
