"""
SAGE服务调用模块 - 简化版
统一的请求/响应机制，支持同步和异步调用
"""

import logging
import time
import threading
import uuid
import queue
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment

@dataclass 
class ServiceResponse:
    """服务响应数据结构"""
    success: bool
    result: Any = None
    error: str = None
    request_id: str = None


class ServiceManager:
    """
    统一的服务管理器
    负责所有服务调用的请求/响应匹配和管理
    """
    
    def __init__(self, context, logger=None):
        # 支持传入TaskContext或BaseEnvironment
        if hasattr(context, 'env_name'):
            # 这是TaskContext
            self.context = context
            self.env = None
        else:
            # 这是BaseEnvironment
            self.env = context
            self.context = None
            
        # 使用注入的logger或默认logger
        if logger is not None:
            self.logger = logger
        elif self.context is not None and hasattr(self.context, 'logger'):
            self.logger = self.context.logger
        else:
            self.logger = logging.getLogger(__name__)
            
        self.logger.debug(f"ServiceManager initialized for context: {getattr(context, 'name', 'unknown')}")
        
        # 服务队列缓存
        self._service_queues: Dict[str, Any] = {}
        
        # 响应队列 - 使用TaskContext中的响应队列
        self._response_queue: Optional[Any] = None
        if self.context is not None:
            # 从TaskContext获取响应队列名称
            if hasattr(self.context, 'response_qd') and self.context.response_qd:
                self._response_queue_name = self.context.response_qd.queue_id
            else:
                # 如果没有响应队列描述符，创建一个唯一名称
                self._response_queue_name = f"service_responses_{uuid.uuid4().hex[:8]}"
        else:
            # 兼容性处理
            self._response_queue_name = f"service_responses_{uuid.uuid4().hex[:8]}"
        
        # 请求结果管理
        self._result_lock = threading.RLock()
        self._request_results: Dict[str, ServiceResponse] = {}
        self._pending_requests: Dict[str, threading.Event] = {}
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ServiceCall")
        
        # 添加停止标志
        self._shutdown = False
        
        # 启动响应监听线程
        self._listener_thread = threading.Thread(
            target=self._response_listener,
            daemon=True,
            name="ServiceResponseListener"
        )
        self._listener_thread.start()
    
    def _get_service_queue(self, service_name: str):
        """从TaskContext获取服务队列"""
        if self.context is not None:
            # 从TaskContext的服务队列描述符获取队列
            if hasattr(self.context, 'service_qds') and service_name in self.context.service_qds:
                return self.context.service_qds[service_name].queue_instance
            else:
                self.logger.error(f"Service queue descriptor not found for service: {service_name}")
                raise RuntimeError(f"Service queue not available for service: {service_name}")
        else:
            raise RuntimeError("No TaskContext available to get service queue")
    
    def _get_response_queue(self):
        """从TaskContext获取响应队列"""
        if self._response_queue is None:
            if self.context:
                # 从TaskContext的服务响应队列描述符获取队列
                if hasattr(self.context, 'response_qd') and self.context.response_qd:
                    self._response_queue = self.context.response_qd.clone()
                    self.logger.debug(f"Using response queue: {self._response_queue_name}")
                else:
                    context_type = type(self.context).__name__
                    has_response_qd = hasattr(self.context, 'response_qd')
                    response_qd_value = getattr(self.context, 'response_qd', None)
                    self.logger.error(f"Service response queue descriptor not found. Context: {context_type}, has_response_qd: {has_response_qd}, response_qd: {response_qd_value}")
                    raise RuntimeError("Service response queue not available")
        return self._response_queue
    
    def call_sync(
        self, 
        service_name: str, 
        method_name: str, 
        *args, 
        timeout: Optional[float] = 10.0, # 增加默认超时时间到10秒
        **kwargs
    ) -> Any:
        """
        同步调用服务方法
        
        Args:
            service_name: 服务名称
            method_name: 方法名称
            *args: 位置参数
            timeout: 超时时间（秒）
            **kwargs: 关键字参数
            
        Returns:
            服务方法的返回值
            
        Raises:
            TimeoutError: 调用超时
            RuntimeError: 服务调用失败
        """
        request_id = str(uuid.uuid4())
        call_start_time = time.time()
        
        self.logger.info(f"[SERVICE_CALL] Starting sync call: {service_name}.{method_name} (request_id: {request_id})")
        self.logger.debug(f"[SERVICE_CALL] Call args: {args}, kwargs: {kwargs}, timeout: {timeout}s")
        
        # 创建等待事件
        event = threading.Event()
        with self._result_lock:
            self._pending_requests[request_id] = event
        
        try:
            # 构造请求数据 - 传递响应队列实例而不是名称
            self.logger.debug(f"Getting response queue for service call: {service_name}.{method_name}")
            response_queue = self._get_response_queue()
            request_data = {
                'request_id': request_id,
                'service_name': service_name,
                'method_name': method_name,
                'args': args,
                'kwargs': kwargs,
                'timeout': timeout,
                'timestamp': time.time(),
                'response_queue': response_queue,  # 传递队列实例而不是名称
                'response_queue_name': self._response_queue_name  # 仍然保留名称用于日志
            }
            
            # 发送请求到服务队列
            service_queue = self._get_service_queue(service_name)
            
            self.logger.debug(f"[SERVICE_CALL] Sending request to service queue: {service_name}")
            queue_send_start = time.time()
            service_queue.put(request_data, timeout=5.0)
            queue_send_time = time.time() - queue_send_start
            
            self.logger.debug(f"[SERVICE_CALL] Request sent successfully in {queue_send_time:.3f}s (request_id: {request_id})")
            
            # 等待结果
            wait_start_time = time.time()
            self.logger.debug(f"[SERVICE_CALL] Waiting for response (timeout: {timeout}s)")
            
            if not event.wait(timeout=timeout):
                wait_time = time.time() - wait_start_time
                self.logger.error(f"[SERVICE_CALL] TIMEOUT after {wait_time:.3f}s: {service_name}.{method_name} (request_id: {request_id})")
                raise TimeoutError(f"Service call timeout after {timeout}s: {service_name}.{method_name}")
            
            wait_time = time.time() - wait_start_time
            self.logger.debug(f"[SERVICE_CALL] Response received after {wait_time:.3f}s")
            
            # 获取结果
            with self._result_lock:
                if request_id not in self._request_results:
                    self.logger.error(f"[SERVICE_CALL] Result not found for request_id: {request_id}")
                    raise RuntimeError(f"Service call result not found: {request_id}")
                
                response = self._request_results.pop(request_id)
                
                total_time = time.time() - call_start_time
                
                if response.success:
                    self.logger.info(f"[SERVICE_CALL] SUCCESS: {service_name}.{method_name} completed in {total_time:.3f}s (request_id: {request_id})")
                    self.logger.debug(f"[SERVICE_CALL] Response result: {response.result}")
                    return response.result
                else:
                    self.logger.error(f"[SERVICE_CALL] FAILURE: {service_name}.{method_name} failed in {total_time:.3f}s - {response.error} (request_id: {request_id})")
                    raise RuntimeError(f"Service call failed: {response.error}")
                    
        except Exception as e:
            # 清理等待状态
            with self._result_lock:
                self._pending_requests.pop(request_id, None)  
                self._request_results.pop(request_id, None)
            
            total_time = time.time() - call_start_time
            self.logger.error(f"[SERVICE_CALL] EXCEPTION: {service_name}.{method_name} failed in {total_time:.3f}s - {str(e)} (request_id: {request_id})")
            raise
    
    def call_async(
        self,
        service_name: str,
        method_name: str,
        *args,
        timeout: Optional[float] = 30.0,
        **kwargs
    ) -> Future:
        """
        异步调用服务方法
        
        Args:
            service_name: 服务名称
            method_name: 方法名称
            *args: 位置参数
            timeout: 超时时间（秒）
            **kwargs: 关键字参数
            
        Returns:
            Future对象，可以通过future.result()获取结果
        """
        # 在线程池中执行同步调用
        future = self._executor.submit(
            self.call_sync, service_name, method_name, *args, timeout=timeout, **kwargs
        )
        
        self.logger.debug(f"Started async call: {service_name}.{method_name}")
        return future
    
    def _response_listener(self):
        """
        响应监听线程 - 从响应队列接收响应并分发
        """
        self.logger.debug("Service response listener started")
        
        while not self._shutdown:
            try:
                # 获取响应队列
                self.logger.debug("Response listener: Getting response queue")
                response_queue = self._get_response_queue()
                
                # 检查队列是否已关闭
                if hasattr(response_queue, 'is_closed') and response_queue.is_closed():
                    self.logger.debug("Response queue is closed, stopping listener")
                    break
                
                # 从响应队列获取响应（阻塞等待1秒）
                try:
                    response_data = response_queue.get(timeout=1.0)
                    self.logger.debug(f"[SERVICE_RESPONSE] Received raw response data: {response_data}")
                    
                    if response_data is None:
                        self.logger.debug("[SERVICE_RESPONSE] Received None from queue, continuing")
                        continue
                    
                    # 处理响应数据
                    self._handle_response(response_data)
                    
                except Exception as queue_error:
                    # 检查具体的队列异常类型
                    error_type = type(queue_error).__name__
                    
                    # 处理标准Python队列超时异常（queue.Empty）
                    if isinstance(queue_error, queue.Empty):
                        # 这是正常的超时，继续循环而不记录任何消息
                        continue
                    
                    # 处理其他可能的超时异常
                    error_str = str(queue_error).lower()
                    if error_type == 'Empty' or 'empty' in error_type.lower():
                        # 其他类型的Empty异常
                        continue
                    elif "timed out" in error_str or "timeout" in error_str:
                        # 其他类型的超时异常
                        continue
                    elif "closed" in error_str or "queue is closed" in error_str:
                        # 队列关闭
                        self.logger.debug(f"Queue operation result: {queue_error}")
                        continue
                    else:
                        # 其他未知的队列异常
                        if error_str.strip():  # 如果错误消息不为空
                            self.logger.warning(f"Queue operation issue ({error_type}): {queue_error}")
                        else:  # 如果错误消息为空，提供更多上下文
                            self.logger.debug(f"Queue operation ({error_type}): Empty message from queue.get() - likely timeout")
                        continue  # 继续运行，不要因为队列问题停止
                
            except Exception as e:
                # 检查是否是队列关闭导致的错误
                error_str = str(e).lower()
                if "closed" in error_str or "queue is closed" in error_str:
                    self.logger.debug("Response queue closed, stopping listener")
                    break
                else:
                    self.logger.error(f"Error in response listener: {e}")
                    self.logger.debug(f"Listener error details: {type(e).__name__}: {e}")
                    time.sleep(1.0)
    
    def _handle_response(self, response_data: Dict[str, Any]) -> None:
        """处理服务响应"""
        request_id = response_data.get('request_id')
        if not request_id:
            self.logger.warning("[SERVICE_RESPONSE] Received response without request_id")
            return
        
        self.logger.debug(f"[SERVICE_RESPONSE] Received response for request_id: {request_id}")
        
        with self._result_lock:
            if request_id not in self._pending_requests:
                self.logger.warning(f"[SERVICE_RESPONSE] No pending request found for request_id: {request_id}")
                return
            
            # 存储结果
            self._request_results[request_id] = ServiceResponse(
                request_id=request_id,
                success=response_data.get('success', False),
                result=response_data.get('result'),
                error=response_data.get('error')
            )
            
            self.logger.debug(f"[SERVICE_RESPONSE] Stored result for request_id: {request_id}, success: {response_data.get('success', False)}")
            
            # 唤醒等待的线程
            event = self._pending_requests.pop(request_id, None)
            if event:
                event.set()
                self.logger.debug(f"[SERVICE_RESPONSE] Notified waiting thread for request_id: {request_id}")
            else:
                self.logger.warning(f"[SERVICE_RESPONSE] No waiting event found for request_id: {request_id}")
    
    def shutdown(self):
        """关闭服务管理器"""
        self.logger.debug("Shutting down ServiceManager")
        
        # 设置停止标志
        self._shutdown = True
        
        # 关闭所有服务队列
        for service_name, queue in self._service_queues.items():
            try:
                queue.close()
            except Exception as e:
                self.logger.warning(f"Error closing service queue {service_name}: {e}")
        
        # 关闭响应队列
        if self._response_queue:
            try:
                self._response_queue.close()
            except Exception as e:
                self.logger.warning(f"Error closing response queue: {e}")
        
        # 等待监听线程结束（最多等待2秒）
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)
            if self._listener_thread.is_alive():
                self.logger.warning("Response listener thread did not stop gracefully")
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
    
    def __del__(self):
        """析构函数 - 确保资源被正确清理"""
        try:
            if not self._shutdown:
                self.shutdown()
        except Exception:
            # 在析构函数中不记录错误，避免在程序退出时产生问题
            pass


class ServiceCallProxy:
    """服务调用代理，提供语法糖支持"""
    
    def __init__(self, service_manager: 'ServiceManager', service_name: str, logger=None):
        self._service_manager = service_manager
        self._service_name = service_name
        self.logger = logger if logger is not None else logging.getLogger(f"{__name__}.{service_name}")
        
        self.logger.debug(f"[PROXY] Created ServiceCallProxy for service: {service_name}")
    
    def __getattr__(self, method_name: str):
        """获取服务方法的调用代理"""
        self.logger.debug(f"[PROXY] Creating method proxy for {self._service_name}.{method_name}")
        
        def method_call(*args, timeout: Optional[float] = 2.0, **kwargs):
            proxy_call_start = time.time()
            self.logger.info(f"[PROXY] Calling {self._service_name}.{method_name} with args={args}, kwargs={kwargs}, timeout={timeout}s")
            
            try:
                result = self._service_manager.call_sync(
                    self._service_name, 
                    method_name, 
                    *args, 
                    timeout=timeout, 
                    **kwargs
                )
                
                proxy_call_time = time.time() - proxy_call_start
                self.logger.info(f"[PROXY] SUCCESS: {self._service_name}.{method_name} completed in {proxy_call_time:.3f}s")
                self.logger.debug(f"[PROXY] Method result: {result}")
                return result
                
            except Exception as e:
                proxy_call_time = time.time() - proxy_call_start
                self.logger.error(f"[PROXY] FAILED: {self._service_name}.{method_name} failed in {proxy_call_time:.3f}s - {str(e)}")
                raise
        
        # 设置方法名称用于调试
        method_call.__name__ = f"{self._service_name}.{method_name}"
        return method_call
