"""
SAGE服务调用模块 - 简化版
统一的请求/响应机制，支持同步和异步调用
"""

import logging
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING


from sage.utils.mmap_queue.sage_queue import SageQueue
if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment

@dataclass 
class ServiceResponse:
    """服务响应数据结构"""
    success: bool
    result: Any = None
    error: str = None


class ServiceManager:
    """
    统一的服务管理器
    负责所有服务调用的请求/响应匹配和管理
    """
    
    def __init__(self, env: 'BaseEnvironment'):
        self.env = env
        self.logger = logging.getLogger(__name__)
        
        # 服务队列缓存
        self._service_queues: Dict[str, SageQueue] = {}
        
        # 响应队列
        self._response_queue_name = f"service_responses_{uuid.uuid4().hex[:8]}"
        self._response_queue: Optional[SageQueue] = None
        
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
    
    def _get_service_queue(self, service_name: str) -> SageQueue:
        """获取服务队列"""
        if service_name not in self._service_queues:
            queue_name = f"service_request_{service_name}"
            self._service_queues[service_name] = SageQueue(name=queue_name)
        return self._service_queues[service_name]
    
    def _get_response_queue(self) -> SageQueue:
        """获取响应队列"""
        if self._response_queue is None:
            self._response_queue = SageQueue(name=self._response_queue_name)
        return self._response_queue
    
    def call_sync(
        self, 
        service_name: str, 
        method_name: str, 
        *args, 
        timeout: Optional[float] = 2.0, # 这里的timeout只容忍本地
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
        
        # 创建等待事件
        event = threading.Event()
        with self._result_lock:
            self._pending_requests[request_id] = event
        
        try:
            # 构造请求数据
            request_data = {
                'request_id': request_id,
                'service_name': service_name,
                'method_name': method_name,
                'args': args,
                'kwargs': kwargs,
                'timeout': timeout,
                'timestamp': time.time(),
                'response_queue': self._response_queue_name
            }
            
            # 发送请求到服务队列
            service_queue = self._get_service_queue(service_name)
            service_queue.put(request_data, timeout=5.0)
            
            self.logger.debug(f"Sent sync request {request_id}: {service_name}.{method_name}")
            
            # 等待结果
            if not event.wait(timeout=timeout):
                raise TimeoutError(f"Service call timeout after {timeout}s: {service_name}.{method_name}")
            
            # 获取结果
            with self._result_lock:
                if request_id not in self._request_results:
                    raise RuntimeError(f"Service call result not found: {request_id}")
                
                response = self._request_results.pop(request_id)
                
                if response.success:
                    return response.result
                else:
                    raise RuntimeError(f"Service call failed: {response.error}")
                    
        except Exception as e:
            # 清理等待状态
            with self._result_lock:
                self._pending_requests.pop(request_id, None)  
                self._request_results.pop(request_id, None)
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
                response_queue = self._get_response_queue()
                
                # 检查队列是否已关闭
                if hasattr(response_queue, 'is_closed') and response_queue.is_closed():
                    self.logger.debug("Response queue is closed, stopping listener")
                    break
                
                # 从响应队列获取响应（阻塞等待1秒）
                try:
                    response_data = response_queue.get(timeout=1.0)
                    
                    # 构造ServiceResponse对象
                    response = ServiceResponse(
                        success=response_data.get('success', True),
                        result=response_data.get('result'),
                        error=response_data.get('error')
                    )
                    
                    request_id = response_data['request_id']
                    self._handle_response(request_id, response)
                    
                except Exception as e:
                    # 如果是超时或队列关闭，不记录错误
                    if "timed out" not in str(e).lower() and "closed" not in str(e).lower():
                        self.logger.error(f"Error receiving response: {e}")
                
            except Exception as e:
                # 检查是否是队列关闭导致的错误
                if "closed" in str(e).lower() or "Queue is closed" in str(e):
                    self.logger.debug("Response queue closed, stopping listener")
                    break
                else:
                    self.logger.error(f"Error in response listener: {e}")
                    time.sleep(1.0)
    
    def _handle_response(self, request_id: str, response: ServiceResponse):
        """处理接收到的响应"""
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
    """统一的服务调用代理类，支持同步和异步调用"""
    
    def __init__(self, service_manager: ServiceManager, service_name: str, async_mode: bool = False):
        self._service_manager = service_manager
        self._service_name = service_name
        self._async_mode = async_mode
    
    @property
    def service_name(self) -> str:
        """获取服务名称"""
        return self._service_name
    
    def __getattr__(self, method_name: str):
        """
        动态创建方法调用
        
        Args:
            method_name: 要调用的服务方法名
            
        Returns:
            如果是异步模式，返回Future对象
            如果是同步模式，返回方法执行结果
        """
        def _call(*args, timeout: Optional[float] = 30.0, **kwargs):
            if self._async_mode:
                return self._service_manager.call_async(
                    self._service_name, method_name, *args, timeout=timeout, **kwargs
                )
            else:
                return self._service_manager.call_sync(
                    self._service_name, method_name, *args, timeout=timeout, **kwargs
                )
        
        return _call
