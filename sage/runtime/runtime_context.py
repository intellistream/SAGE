import os
import threading
from typing import TYPE_CHECKING
import ray
from ray.actor import ActorHandle
from typing import List,Dict,Optional, Any, Union
from sage.utils.custom_logger import CustomLogger
from sage.utils.actor_wrapper import ActorWrapper            return False
        else:
            self.logger.info(f"Task {self.name} stop signal count: {self.stop_signal_count}/{self.stop_signal_num}")
            return False

    # ================== 队列描述符管理方法 ==================
    
    def set_input_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置输入队列描述符（用于graph node）"""
        self._input_queue_descriptor = descriptor
    
    def get_input_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取输入队列描述符"""
        return self._input_queue_descriptor
    
    def set_service_response_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置服务响应队列描述符（用于graph node）"""
        self._service_response_queue_descriptor = descriptor
    
    def get_service_response_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取服务响应队列描述符"""
        return self._service_response_queue_descriptor
    
    def set_request_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置请求队列描述符（用于service task）"""
        self._request_queue_descriptor = descriptor
    
    def get_request_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取请求队列描述符"""
        return self._request_queue_descriptor
    
    def set_service_request_queue_descriptors(self, descriptors: Dict[str, 'BaseQueueDescriptor']):
        """设置服务请求队列描述符映射（用于graph node访问各个service）"""
        self._service_request_queue_descriptors = descriptors
    
    def get_service_request_queue_descriptors(self) -> Optional[Dict[str, 'BaseQueueDescriptor']]:
        """获取服务请求队列描述符映射"""
        return self._service_request_queue_descriptors
        
    def get_service_request_queue_descriptor(self, service_name: str) -> Optional['BaseQueueDescriptor']:
        """获取指定服务的请求队列描述符"""
        if self._service_request_queue_descriptors:
            return self._service_request_queue_descriptors.get(service_name)
        return None
    
    def set_service_response_queue_descriptors(self, descriptors: Dict[str, 'BaseQueueDescriptor']):
        """设置服务响应队列描述符映射（用于service task访问各个response队列）"""
        self._service_response_queue_descriptors = descriptors
    
    def get_service_response_queue_descriptors(self) -> Optional[Dict[str, 'BaseQueueDescriptor']]:
        """获取服务响应队列描述符映射"""
        return self._service_response_queue_descriptors
        
    def get_service_response_queue_descriptor(self, service_name: str) -> Optional['BaseQueueDescriptor']:
        """获取指定服务的响应队列描述符"""
        if self._service_response_queue_descriptors:
            return self._service_response_queue_descriptors.get(service_name)
        return None TYPE_CHECKING:
    from sage.jobmanager.execution_graph import ExecutionGraph, GraphNode
    from sage.core.transformation.base_transformation import BaseTransformation
    from sage.core.api.base_environment import BaseEnvironment 
    from sage.jobmanager.job_manager import JobManager
    from sage.runtime.service.service_caller import ServiceManager
    from sage.core.function.source_function import StopSignal
    from sage.runtime.communication.queue.base_queue_descriptor import BaseQueueDescriptor
# task, operator和function "形式上共享"的运行上下文

class RuntimeContext:
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]
    def __init__(self, graph_node: 'GraphNode', transformation: 'BaseTransformation', env: 'BaseEnvironment'):
        
        self.name:str = graph_node.name

        self.env_name = env.name
        self.env_base_dir:str = env.env_base_dir
        self.env_uuid = getattr(env, 'uuid', None)  # 使用 getattr 以避免 AttributeError
        self.env_console_log_level = env.console_log_level  # 保存环境的控制台日志等级

        self.parallel_index:int = graph_node.parallel_index
        self.parallelism:int = graph_node.parallelism

        self._logger:Optional[CustomLogger] = None

        self.is_spout = transformation.is_spout

        self.delay = 0.01
        self.stop_signal_num = graph_node.stop_signal_num
        
        # 保存JobManager的网络地址信息而不是直接引用
        self.jobmanager_host = getattr(env, 'jobmanager_host', '127.0.0.1')
        self.jobmanager_port = getattr(env, 'jobmanager_port', 19001)
        
        # 这些属性将在task层初始化，避免序列化问题
        self._stop_event = None  # 延迟初始化
        self.received_stop_signals = None  # 延迟初始化
        self.stop_signal_count = 0
        
        # 服务调用相关
        self._service_manager: Optional['ServiceManager'] = None
        self._service_names: Optional[Dict[str, str]] = None  # 只保存服务名称映射而不是实例
        
        # 队列描述符管理
        self._input_queue_descriptor: Optional['BaseQueueDescriptor'] = None
        self._service_response_queue_descriptor: Optional['BaseQueueDescriptor'] = None
        self._request_queue_descriptor: Optional['BaseQueueDescriptor'] = None  # 用于service task
        self._service_request_queue_descriptors: Optional[Dict[str, 'BaseQueueDescriptor']] = None  # graph node访问service的队列
        self._service_response_queue_descriptors: Optional[Dict[str, 'BaseQueueDescriptor']] = None  # service task访问各个response队列
    
    def initialize_task_context(self):
        """
        在task层初始化不可序列化的属性
        这些属性需要在task创建时才初始化，避免序列化问题
        """
        if self._stop_event is None:
            self._stop_event = threading.Event()
        if self.received_stop_signals is None:
            self.received_stop_signals = set()
        self.stop_signal_count = 0  # 重置计数
    
    @property
    def service_manager(self) -> 'ServiceManager':
        """懒加载服务管理器"""
        if self._service_manager is None:
            from sage.runtime.service.service_caller import ServiceManager
            # ServiceManager需要完整的运行时上下文来访问dispatcher服务
            self._service_manager = ServiceManager(self)
        return self._service_manager

    def cleanup(self):
        """清理运行时上下文资源"""
        if self._service_manager is not None:
            try:
                self._service_manager.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down service manager: {e}")
            finally:
                self._service_manager = None

    def __del__(self):
        """析构函数 - 确保资源被正确清理"""
        try:
            self.cleanup()
        except Exception:
            # 在析构函数中不记录错误，避免在程序退出时产生问题
            pass

    def _is_ray_actor(self, obj) -> bool:
        """检测执行模式"""
        if isinstance(obj, ActorHandle):
            return 1
        elif hasattr(obj, 'remote'):
            return 1
        else:
            return 0
        # return hasattr(obj, '_actor_id') and hasattr(obj, '_remote')



    @property
    def logger(self) -> CustomLogger:
        """懒加载logger"""
        if self._logger is None:
            self._logger = CustomLogger([
                ("console", self.env_console_log_level),  # 使用环境设置的控制台日志等级
                (os.path.join(self.env_base_dir, f"{self.name}_debug.log"), "DEBUG"),  # 详细日志
                (os.path.join(self.env_base_dir, "Error.log"), "ERROR"),  # 错误日志
                (os.path.join(self.env_base_dir, f"{self.name}_info.log"), "INFO")  # 错误日志
            ],
            name = f"{self.name}",
        )
        return self._logger

    def set_service_names(self, service_names: Dict[str, str]):
        """设置服务名称映射（由dispatcher调用）"""
        self._service_names = service_names

    def get_service(self, service_name: str) -> Any:
        """
        获取服务实例，通过service_manager获取
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务实例
            
        Raises:
            ValueError: 当服务不存在时
        """
        if self._service_names is None:
            raise RuntimeError("Services not available - dispatcher not initialized")
        
        if service_name not in self._service_names:
            available_services = list(self._service_names.keys())
            raise ValueError(f"Service '{service_name}' not found. Available services: {available_services}")
        
        # 通过service_manager获取实际的服务实例
        return self.service_manager.get_service(service_name)

    def call_service(self, service_name: str, method_name: str, *args, **kwargs) -> Any:
        """
        调用服务方法
        
        Args:
            service_name: 服务名称
            method_name: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            方法调用结果
        """
        # 通过service_manager调用服务方法
        return self.service_manager.call_service(service_name, method_name, *args, **kwargs)

    def list_services(self) -> List[str]:
        """列出所有可用的服务名称"""
        if self._service_names is None:
            return []
        return list(self._service_names.keys())

    @property
    def stop_event(self) -> threading.Event:
        """获取共享的停止事件，延迟初始化"""
        if self._stop_event is None:
            self._stop_event = threading.Event()
        return self._stop_event
    
    def set_stop_signal(self):
        """设置停止信号"""
        if self._stop_event is None:
            self._stop_event = threading.Event()
        self._stop_event.set()
    
    def is_stop_requested(self) -> bool:
        """检查是否请求停止"""
        if self._stop_event is None:
            return False
        return self._stop_event.is_set()
    
    def clear_stop_signal(self):
        """清除停止信号"""
        if self._stop_event is None:
            self._stop_event = threading.Event()
        else:
            self._stop_event.clear()
        # 同时清除停止信号计数
        if self.received_stop_signals is None:
            self.received_stop_signals = set()
        else:
            self.received_stop_signals.clear()
        self.stop_signal_count = 0
    
    def send_stop_signal_back(self, node_name: str):
        """
        通过网络向JobManager发送节点停止信号
        支持本地和远程(Ray Actor)环境
        """
        try:
            # 导入JobManagerClient来发送网络请求
            from sage.jobmanager.jobmanager_client import JobManagerClient
            
            self.logger.info(f"Task {node_name} sending stop signal back to JobManager at {self.jobmanager_host}:{self.jobmanager_port}")
            
            # 创建客户端并发送停止信号
            client = JobManagerClient(host=self.jobmanager_host, port=self.jobmanager_port)
            response = client.receive_node_stop_signal(self.env_uuid, node_name)
            
            if response.get('status') == 'success':
                self.logger.debug(f"Successfully sent stop signal for node {node_name}")
            else:
                self.logger.warning(f"JobManager response: {response}")
                
        except Exception as e:
            self.logger.error(f"Failed to send stop signal back for node {node_name}: {e}", exc_info=True)
    
    def handle_stop_signal(self, stop_signal: 'StopSignal') -> bool:
        """
        在task层处理停止信号计数
        返回True表示收到了所有预期的停止信号
        """
        # 确保received_stop_signals已初始化
        if self.received_stop_signals is None:
            self.received_stop_signals = set()
            
        if stop_signal.name in self.received_stop_signals:
            self.logger.debug(f"Already received stop signal from {stop_signal.name}")
            return False
        
        self.received_stop_signals.add(stop_signal.name)
        self.logger.info(f"Task {self.name} received stop signal from {stop_signal.name}")

        self.stop_signal_count += 1
        if self.stop_signal_count >= self.stop_signal_num:
            self.logger.info(f"Task {self.name} received all expected stop signals ({self.stop_signal_count}/{self.stop_signal_num})")
            
            # 只有非源节点在收到所有预期的停止信号时才通知JobManager
            # 源节点应该在自己完成时直接通知JobManager
            if not self.is_spout:
                self.send_stop_signal_back(self.name)
            
            return True
        else:
            self.logger.info(f"Task {self.name} stop signal count: {self.stop_signal_count}/{self.stop_signal_num}")
            return False

    # ================== 队列描述符管理方法 ==================
    
    def set_input_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置输入队列描述符（用于graph node）"""
        self._input_queue_descriptor = descriptor
    
    def get_input_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取输入队列描述符"""
        return self._input_queue_descriptor
    
    def set_service_response_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置服务响应队列描述符（用于graph node）"""
        self._service_response_queue_descriptor = descriptor
    
    def get_service_response_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取服务响应队列描述符"""
        return self._service_response_queue_descriptor
    
    def set_request_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置请求队列描述符（用于service task）"""
        self._request_queue_descriptor = descriptor
    
    def get_request_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取请求队列描述符"""
        return self._request_queue_descriptor
    
    def set_service_request_queue_descriptors(self, descriptors: Dict[str, 'BaseQueueDescriptor']):
        """设置服务请求队列描述符映射（用于graph node访问各个service）"""
        self._service_request_queue_descriptors = descriptors
    
    def get_service_request_queue_descriptors(self) -> Optional[Dict[str, 'BaseQueueDescriptor']]:
        """获取服务请求队列描述符映射"""
        return self._service_request_queue_descriptors
        
    def get_service_request_queue_descriptor(self, service_name: str) -> Optional['BaseQueueDescriptor']:
        """获取指定服务的请求队列描述符"""
        if self._service_request_queue_descriptors:
            return self._service_request_queue_descriptors.get(service_name)
        return None
    
    def set_service_response_queue_descriptors(self, descriptors: Dict[str, 'BaseQueueDescriptor']):
        """设置服务响应队列描述符映射（用于service task访问各个response队列）"""
        self._service_response_queue_descriptors = descriptors
    
    def get_service_response_queue_descriptors(self) -> Optional[Dict[str, 'BaseQueueDescriptor']]:
        """获取服务响应队列描述符映射"""
        return self._service_response_queue_descriptors
        
    def get_service_response_queue_descriptor(self, service_name: str) -> Optional['BaseQueueDescriptor']:
        """获取指定服务的响应队列描述符"""
        if self._service_response_queue_descriptors:
            return self._service_response_queue_descriptors.get(service_name)
        return None
