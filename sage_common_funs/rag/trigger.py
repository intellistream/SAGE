import asyncio
import queue
import threading
import time
from typing import Any, Optional

from sage_core.api.base_function import BaseFunction
from sage_core.api.tuple import Data


class TriggerableSource(BaseFunction):
    """
    可触发的数据源，支持外部输入触发处理
    """
    
    def __init__(self, config: dict):
        """
        初始化可触发数据源
        
        Args:
            config: 配置字典
        """
        super().__init__()
        self.config = config.get("source", {})
        
        # 输入队列，用于接收外部触发的数据
        self.input_queue = queue.Queue()
        
        # 控制标志
        self._running = False
        self._stop_requested = False
        
        # 用于外部调用的锁
        self._trigger_lock = threading.Lock()
        
        # 等待模式配置
        self.wait_timeout = self.config.get("wait_timeout", 1.0)  # 等待新输入的超时时间
        self.enable_polling = self.config.get("enable_polling", True)  # 是否启用轮询模式
        
        self.logger.info(f"TriggerableSource initialized with config: {self.config}")
    
    def execute(self) -> Optional[Data[Any]]:
        """
        执行方法，从输入队列获取数据
        
        Returns:
            Data对象或None
        """
        try:
            if self.enable_polling:
                # 轮询模式：等待一段时间后超时返回None
                try:
                    data = self.input_queue.get(timeout=self.wait_timeout)
                    if data is None:  # 停止信号
                        return None
                    self.logger.debug(f"Got triggered data: {data}")
                    return Data(data)
                except queue.Empty:
                    # 超时，返回None，让调用者决定是否继续轮询
                    return None
            else:
                # 阻塞模式：一直等待直到有数据
                data = self.input_queue.get()
                if data is None:  # 停止信号
                    return None
                self.logger.debug(f"Got triggered data: {data}")
                return Data(data)
                
        except Exception as e:
            self.logger.error(f"Error in TriggerableSource.execute(): {e}")
            return None
    
    def trigger(self, data: Any) -> bool:
        """
        外部触发接口，将数据放入队列
        
        Args:
            data: 要处理的数据
            
        Returns:
            bool: 是否成功触发
        """
        try:
            with self._trigger_lock:
                if self._stop_requested:
                    self.logger.warning("Source has been stopped, ignoring trigger")
                    return False
                
                self.input_queue.put(data)
                self.logger.debug(f"Triggered with data: {data}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error triggering source: {e}")
            return False
    
    def stop(self):
        """停止数据源"""
        self._stop_requested = True
        # 发送停止信号
        try:
            self.input_queue.put(None)
        except Exception as e:
            self.logger.error(f"Error stopping source: {e}")
    
    def is_empty(self) -> bool:
        """检查输入队列是否为空"""
        return self.input_queue.empty()
    
    def queue_size(self) -> int:
        """获取队列大小"""
        return self.input_queue.qsize()


class RESTApiSource(TriggerableSource):
    """
    专门用于REST API请求的数据源
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # API特定配置
        self.request_timeout = self.config.get("request_timeout", 30.0)
        self.max_queue_size = self.config.get("max_queue_size", 100)
        
        # 请求ID追踪
        self._request_counter = 0
        self._pending_requests = {}
        
    def trigger_request(self, request_data: dict, request_id: str = None) -> str:
        """
        触发API请求处理
        
        Args:
            request_data: 请求数据
            request_id: 可选的请求ID
            
        Returns:
            str: 请求ID
        """
        if request_id is None:
            self._request_counter += 1
            request_id = f"req_{self._request_counter}"
        
        # 检查队列大小
        if self.queue_size() >= self.max_queue_size:
            raise ValueError(f"Request queue is full (max: {self.max_queue_size})")
        
        # 包装请求数据
        wrapped_request = {
            "request_id": request_id,
            "data": request_data,
            "timestamp": time.time()
        }
        
        success = self.trigger(wrapped_request)
        if success:
            self._pending_requests[request_id] = wrapped_request
            self.logger.info(f"API request {request_id} queued")
            return request_id
        else:
            raise RuntimeError(f"Failed to queue API request {request_id}")
    
    def get_pending_requests(self) -> list:
        """获取待处理请求列表"""
        return list(self._pending_requests.keys())