from abc import ABC, abstractmethod
import threading
import time
from typing import Any, TYPE_CHECKING, Optional, Dict
from sage.utils.custom_logger import CustomLogger

if TYPE_CHECKING:
    pass


class BaseService(ABC):
    """服务基类，提供服务实例的基础通信能力"""
    
    def __init__(self, service_name: str, service_instance: Any):
        """
        初始化服务基类
        
        Args:
            service_name: 服务名称
            service_instance: 实际的服务实例
        """
        self.service_name = service_name
        self.service_instance = service_instance
        
        # 线程控制
        self._worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self._stop_event = threading.Event()
        
        # 性能监控
        self._request_count = 0
        self._error_count = 0
        self._last_activity_time = time.time()
        
        # 日志记录器
        self.logger = CustomLogger(name=f"Service_{service_name}")
        
        self.logger.info(f"Service '{service_name}' initialized")

    def start_running(self):
        """启动服务的工作循环"""
        if self.is_running:
            self.logger.warning(f"Service {self.service_name} is already running")
            return
        
        self.logger.info(f"Starting service {self.service_name}")
        
        # 设置运行状态
        self.is_running = True
        self._stop_event.clear()
        
        # 启动工作线程（如果服务需要后台处理）
        if self._needs_background_worker():
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name=f"{self.service_name}_worker",
                daemon=True
            )
            self._worker_thread.start()
            self.logger.info(f"Service {self.service_name} started with worker thread")
        else:
            self.logger.info(f"Service {self.service_name} started (no background worker needed)")

    def stop(self):
        """停止服务"""
        if not self.is_running:
            self.logger.warning(f"Service {self.service_name} is not running")
            return
            
        self.logger.info(f"Stopping service {self.service_name}")
        
        # 发送停止信号
        self._stop_event.set()
        self.is_running = False
        
        # 等待工作线程结束
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                self.logger.warning(f"Service {self.service_name} worker thread did not stop gracefully")
        
        self.logger.info(f"Service {self.service_name} stopped")

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
            self._last_activity_time = time.time()
            
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
        """
        获取服务属性
        
        Args:
            attr_name: 属性名称
            
        Returns:
            属性值
        """
        try:
            if not hasattr(self.service_instance, attr_name):
                raise AttributeError(f"Service {self.service_name} does not have attribute '{attr_name}'")
            
            return getattr(self.service_instance, attr_name)
            
        except Exception as e:
            self.logger.error(f"Error getting attribute {attr_name} from service {self.service_name}: {e}")
            raise

    def set_attribute(self, attr_name: str, value: Any):
        """
        设置服务属性
        
        Args:
            attr_name: 属性名称
            value: 属性值
        """
        try:
            setattr(self.service_instance, attr_name, value)
            self.logger.debug(f"Set attribute {attr_name} on service {self.service_name}")
            
        except Exception as e:
            self.logger.error(f"Error setting attribute {attr_name} on service {self.service_name}: {e}")
            raise

    def get_object(self):
        """获取服务对象，用于兼容Task接口"""
        return self

    def get_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "service_name": self.service_name,
            "is_running": self.is_running,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "last_activity_time": self._last_activity_time,
            "uptime": time.time() - self._last_activity_time if self._last_activity_time > 0 else 0
        }

    def cleanup(self):
        """清理服务资源"""
        self.logger.info(f"Cleaning up service {self.service_name}")
        
        try:
            # 停止服务
            if self.is_running:
                self.stop()
            
            # 清理服务实例资源（如果有cleanup方法）
            if hasattr(self.service_instance, 'cleanup'):
                self.service_instance.cleanup()
            elif hasattr(self.service_instance, 'close'):
                self.service_instance.close()
            
            self.logger.debug(f"Service {self.service_name} cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of service {self.service_name}: {e}")

    def _needs_background_worker(self) -> bool:
        """
        判断服务是否需要后台工作线程
        子类可以重写此方法来决定是否需要后台处理
        
        Returns:
            True表示需要后台工作线程，False表示不需要
        """
        # 检查服务实例是否有后台处理方法
        return hasattr(self.service_instance, '_background_process') or \
               hasattr(self.service_instance, 'background_worker')

    def _worker_loop(self):
        """
        后台工作循环，子类可以重写此方法实现自定义后台处理逻辑
        """
        self.logger.debug(f"Starting worker loop for service {self.service_name}")
        
        while not self._stop_event.is_set():
            try:
                # 如果服务实例有后台处理方法，则调用
                if hasattr(self.service_instance, '_background_process'):
                    self.service_instance._background_process()
                elif hasattr(self.service_instance, 'background_worker'):
                    self.service_instance.background_worker()
                
                # 短暂休眠避免占用过多CPU
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop for service {self.service_name}: {e}")
                time.sleep(1.0)  # 出错时等待更长时间
        
        self.logger.debug(f"Worker loop stopped for service {self.service_name}")

    def __repr__(self) -> str:
        return f"<BaseService {self.service_name}: {type(self.service_instance).__name__}>"
