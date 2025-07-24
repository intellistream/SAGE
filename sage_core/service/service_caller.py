"""
Service Caller - 提供统一的服务调用接口
支持同步和异步两种调用方式，通过高性能mmap queue与service进程通信
"""

import uuid
import asyncio
import threading
import time
from typing import Any, Dict, Optional, Callable, Union, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum
from sage_utils.mmap_queue.sage_queue import SageQueue

if TYPE_CHECKING:
    from sage_runtime.runtime_context import RuntimeContext

class CallMode(Enum):
    SYNC = "sync"
    ASYNC = "async"

@dataclass
class ServiceRequest:
    """服务请求结构"""
    request_id: str
    service_name: str
    method_name: str
    args: tuple
    kwargs: dict
    call_mode: CallMode
    timeout: Optional[float] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass 
class ServiceResponse:
    """服务响应结构"""
    request_id: str
    result: Any = None
    error: Optional[str] = None
    success: bool = True
    execution_time: float = 0.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class ServiceCallProxy:
    """单个服务的调用代理"""
    
    def __init__(self, service_name: str, service_manager: 'ServiceManager'):
        self.service_name = service_name
        self.service_manager = service_manager
        
    def __getattr__(self, method_name: str):
        """动态创建方法调用代理"""
        def method_caller(*args, **kwargs):
            return self.service_manager.call_service_sync(
                self.service_name, method_name, *args, **kwargs
            )
        return method_caller

class AsyncServiceCallProxy:
    """单个服务的异步调用代理"""
    
    def __init__(self, service_name: str, service_manager: 'ServiceManager'):
        self.service_name = service_name
        self.service_manager = service_manager
        
    def __getattr__(self, method_name: str):
        """动态创建异步方法调用代理"""
        def async_method_caller(*args, **kwargs):
            return self.service_manager.call_service_async(
                self.service_name, method_name, *args, **kwargs
            )
        return async_method_caller

class ServiceManager:
    """服务管理器 - 处理服务调用和结果回收"""
    
    def __init__(self, runtime_context: 'RuntimeContext'):
        self.runtime_context = runtime_context
        self.logger = runtime_context.logger
        
        # 服务队列缓存 - 每个服务一个请求队列
        self._service_queues: Dict[str, SageQueue] = {}
        
        # 结果回收相关
        self._pending_requests: Dict[str, threading.Event] = {}
        self._request_results: Dict[str, ServiceResponse] = {}
        self._result_lock = threading.RLock()
        
        # 异步任务池
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ServiceCaller")
        
        # 响应队列 - 所有服务的响应都通过这个队列返回
        self._response_queue_name = f"service_response_{runtime_context.env_name}_{runtime_context.name}"
        self._response_queue: Optional[SageQueue] = None
        
        # 启动结果监听线程
        self._response_listener_thread = threading.Thread(
            target=self._response_listener,
            daemon=True,
            name="ServiceResponseListener"
        )
        self._response_listener_thread.start()
        
        self.logger.debug("ServiceManager initialized")
    
    def _get_service_queue(self, service_name: str) -> SageQueue:
        """获取或创建服务队列"""
        if service_name not in self._service_queues:
            # 使用服务名称作为队列名称
            queue_name = f"service_request_{service_name}"
            self._service_queues[service_name] = SageQueue(queue_name)
            self.logger.debug(f"Created service queue: {queue_name}")
        
        return self._service_queues[service_name]
    
    def _get_response_queue(self) -> SageQueue:
        """获取响应队列"""
        if self._response_queue is None:
            self._response_queue = SageQueue(self._response_queue_name)
            self.logger.debug(f"Created response queue: {self._response_queue_name}")
        
        return self._response_queue
    
    def get_sync_proxy(self, service_name: str) -> ServiceCallProxy:
        """获取同步调用代理 - 每次都创建新的代理实例以支持并发"""
        return ServiceCallProxy(service_name, self)
    
    def get_async_proxy(self, service_name: str) -> AsyncServiceCallProxy:
        """获取异步调用代理 - 每次都创建新的代理实例以支持并发"""
        return AsyncServiceCallProxy(service_name, self)
    
    def call_service_sync(
        self, 
        service_name: str, 
        method_name: str, 
        *args, 
        timeout: Optional[float] = 30.0,
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
        request = ServiceRequest(
            request_id=request_id,
            service_name=service_name,
            method_name=method_name,
            args=args,
            kwargs=kwargs,
            call_mode=CallMode.SYNC,
            timeout=timeout
        )
        
        # 准备结果等待
        event = threading.Event()
        with self._result_lock:
            self._pending_requests[request_id] = event
        
        try:
            # 发送请求到mmap queue
            self._send_request(request)
            
            # 等待结果
            if not event.wait(timeout=timeout):
                raise TimeoutError(f"Service call timeout after {timeout}s: {service_name}.{method_name}")
            
            # 获取结果
            with self._result_lock:
                response = self._request_results.pop(request_id, None)
                
            if response is None:
                raise RuntimeError(f"Lost response for request {request_id}")
            
            if not response.success:
                raise RuntimeError(f"Service call failed: {response.error}")
            
            self.logger.debug(
                f"Sync service call completed: {service_name}.{method_name} "
                f"in {response.execution_time:.3f}s"
            )
            
            return response.result
            
        finally:
            # 清理
            with self._result_lock:
                self._pending_requests.pop(request_id, None)
                self._request_results.pop(request_id, None)
    
    def call_service_async(
        self, 
        service_name: str, 
        method_name: str, 
        *args,
        timeout: Optional[float] = 30.0,
        **kwargs
    ) -> Future:
        """
        异步调用服务方法，返回Future对象
        
        Args:
            service_name: 服务名称
            method_name: 方法名称
            *args: 位置参数
            timeout: 超时时间（秒）
            **kwargs: 关键字参数
            
        Returns:
            Future对象，可以用于获取结果或检查状态
            
        Example:
            # 发起异步调用
            future = self.call_service_async("cache", "get", "key1")
            
            # 非阻塞检查是否完成
            if future.done():
                result = future.result()
            
            # 阻塞等待结果
            result = future.result(timeout=10.0)
        """
        def _async_call():
            return self.call_service_sync(
                service_name, method_name, *args, timeout=timeout, **kwargs
            )
        
        future = self._executor.submit(_async_call)
        
        self.logger.debug(f"Async service call submitted: {service_name}.{method_name}")
        
        return future
    
    def _send_request(self, request: ServiceRequest):
        """
        发送请求到服务的mmap queue
        """
        try:
            # 获取服务队列
            service_queue = self._get_service_queue(request.service_name)
            
            # 添加响应队列名称到请求中，服务进程知道往哪里回复
            request_data = {
                'request_id': request.request_id,
                'service_name': request.service_name,
                'method_name': request.method_name,
                'args': request.args,
                'kwargs': request.kwargs,
                'call_mode': request.call_mode.value,
                'timeout': request.timeout,
                'timestamp': request.timestamp,
                'response_queue': self._response_queue_name  # 告诉服务进程回复到哪个队列
            }
            
            # 发送到服务队列
            service_queue.put(request_data, timeout=5.0)
            
            self.logger.debug(f"Sent request {request.request_id} to service {request.service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send request to service {request.service_name}: {e}")
            raise RuntimeError(f"Failed to send request: {e}")
    
    def _response_listener(self):
        """
        响应监听线程 - 从响应队列接收响应并分发
        """
        self.logger.debug("Service response listener started")
        
        while True:
            try:
                # 获取响应队列
                response_queue = self._get_response_queue()
                
                # 从响应队列获取响应（阻塞等待1秒）
                try:
                    response_data = response_queue.get(timeout=1.0)
                    
                    # 构造ServiceResponse对象
                    response = ServiceResponse(
                        request_id=response_data['request_id'],
                        result=response_data.get('result'),
                        error=response_data.get('error'),
                        success=response_data.get('success', True),
                        execution_time=response_data.get('execution_time', 0.0),
                        timestamp=response_data.get('timestamp', time.time())
                    )
                    
                    self._handle_response(response)
                    
                except Exception as e:
                    if "timed out" not in str(e).lower():
                        self.logger.error(f"Error receiving response: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in response listener: {e}")
                time.sleep(1.0)
    
    def _handle_response(self, response: ServiceResponse):
        """处理接收到的响应"""
        request_id = response.request_id
        
        with self._result_lock:
            # 保存结果
            self._request_results[request_id] = response
            
            # 通知等待的线程
            event = self._pending_requests.get(request_id)
            if event:
                event.set()
        
        self.logger.debug(f"Response handled for request {request_id}")
    
    def shutdown(self):
        """关闭服务管理器"""
        self.logger.debug("Shutting down ServiceManager")
        
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
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
