import os
import threading
from typing import TYPE_CHECKING
import ray
from ray.actor import ActorHandle
from typing import List,Dict,Optional, Any, Union
from sage.utils.custom_logger import CustomLogger
from sage.utils.actor_wrapper import ActorWrapper

if TYPE_CHECKING:
    from sage.jobmanager.execution_graph import ExecutionGraph, GraphNode
    from sage.core.transformation.base_transformation import BaseTransformation
    from sage.core.api.base_environment import BaseEnvironment 
    from sage.jobmanager.job_manager import JobManager
    from sage.runtime.service.service_caller import ServiceManager
    from sage.core.function.source_function import StopSignal
    from sage.runtime.communication.queue.base_queue_descriptor import BaseQueueDescriptor
    from sage.runtime.communication.router.connection import Connection
# task, operator和function "形式上共享"的运行上下文

class TaskContext:
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]
    def __init__(self, graph_node: 'GraphNode', transformation: 'BaseTransformation', env: 'BaseEnvironment', execution_graph: 'ExecutionGraph' = None):
        
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
        
        # 队列描述符管理 - 在构造时从graph_node和execution_graph获取
        self.input_qd: 'BaseQueueDescriptor' = graph_node.input_qd
        self.response_qd: 'BaseQueueDescriptor' = graph_node.service_response_qd
        
        # 从execution_graph获取service队列描述符 - 直接遍历service_nodes获取
        self.service_qds: Dict[str, 'BaseQueueDescriptor'] = {}
        if execution_graph:
            for service_name, service_node in execution_graph.service_nodes.items():
                if service_node.service_qd:
                    self.service_qds[service_node.service_name] = service_node.service_qd
        
        # 下游连接组管理 - 从execution_graph构建downstream_groups
        self.downstream_groups: Dict[int, Dict[int, 'Connection']] = {}
        if execution_graph:
            self._build_downstream_groups(graph_node, execution_graph)
    
    def _build_downstream_groups(self, graph_node: 'GraphNode', execution_graph: 'ExecutionGraph'):
        """从execution_graph构建downstream_groups"""
        # 遍历输出通道，构建downstream_groups
        for broadcast_index, output_group in enumerate(graph_node.output_channels):
            if output_group:  # 确保输出组不为空
                self.downstream_groups[broadcast_index] = {}
                
                for edge in output_group:
                    if edge.downstream_node and edge.downstream_node.input_qd:
                        # 使用下游节点的单一输入队列描述符
                        downstream_queue_descriptor = edge.downstream_node.input_qd
                        
                        # 创建Connection对象
                        from sage.runtime.communication.router.connection import Connection
                        connection = Connection(
                            broadcast_index=broadcast_index,
                            parallel_index=edge.downstream_node.parallel_index,
                            target_name=edge.downstream_node.name,
                            queue_descriptor=downstream_queue_descriptor,
                            target_input_index=edge.input_index
                        )
                        
                        # 使用downstream node的parallel_index作为key
                        self.downstream_groups[broadcast_index][edge.downstream_node.parallel_index] = connection
    
    
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

    @property
    def stop_event(self) -> threading.Event:
        """获取共享的停止事件，延迟初始化"""
        if self._stop_event is None:
            self._stop_event = threading.Event()
        return self._stop_event
    
    def set_stop_signal(self):
        self.stop_event.set()
    
    def is_stop_requested(self) -> bool:
        return self.stop_event.is_set()
    
    def clear_stop_signal(self):
        self.stop_event.clear()
    
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
    

    def __del__(self):
        """析构函数 - 确保资源被正确清理"""
        try:
            self.cleanup()
        except Exception:
            # 在析构函数中不记录错误，避免在程序退出时产生问题
            pass

    # ================== 队列描述符管理方法 ==================
    
    def set_input_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置输入队列描述符"""
        self.input_qd = descriptor
    
    def get_input_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取输入队列描述符"""
        return self.input_qd
    
    def set_service_response_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置服务响应队列描述符"""
        self._service_response_queue_descriptor = descriptor
        self.response_qd = descriptor
    
    def get_service_response_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取服务响应队列描述符"""
        return self._service_response_queue_descriptor
    
    def set_upstream_queue_descriptors(self, descriptors: Dict[int, List['BaseQueueDescriptor']]):
        """设置上游队列描述符映射"""
        self._upstream_queue_descriptors = descriptors
    
    def get_upstream_queue_descriptors(self) -> Optional[Dict[int, List['BaseQueueDescriptor']]]:
        """获取上游队列描述符映射"""
        return self._upstream_queue_descriptors
    
    def set_downstream_queue_descriptors(self, descriptors: List[List['BaseQueueDescriptor']]):
        """设置下游队列描述符映射"""
        self._downstream_queue_descriptors = descriptors
        self.downstream_qds = descriptors
    
    def get_downstream_queue_descriptors(self) -> Optional[List[List['BaseQueueDescriptor']]]:
        """获取下游队列描述符映射"""
        return self._downstream_queue_descriptors
    
    def set_service_request_queue_descriptors(self, descriptors: Dict[str, 'BaseQueueDescriptor']):
        """设置服务请求队列描述符映射"""
        self._service_request_queue_descriptors = descriptors
        self.service_qds = descriptors
    
    def get_service_request_queue_descriptors(self) -> Optional[Dict[str, 'BaseQueueDescriptor']]:
        """获取服务请求队列描述符映射"""
        return self._service_request_queue_descriptors