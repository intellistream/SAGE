from __future__ import annotations
import os
import threading
import ray
from ray.actor import ActorHandle
from typing import TYPE_CHECKING, List, Dict, Optional, Any, Union
from sage.utils.logging.custom_logger import CustomLogger
from sage.utils.actor_wrapper import ActorWrapper

if TYPE_CHECKING:
    from sage.jobmanager.execution_graph.execution_graph import ExecutionGraph
    from sage.jobmanager.execution_graph.graph_node import GraphNode
    from sage.jobmanager.execution_graph.service_node import ServiceNode
    from sage.core.transformation.base_transformation import BaseTransformation
    from sage.core.api.base_environment import BaseEnvironment 
    from sage.jobmanager.job_manager import JobManager
    from sage.runtime.service.service_caller import ServiceManager
    from sage.core.function.source_function import StopSignal
    from sage.runtime.communication.queue.base_queue_descriptor import BaseQueueDescriptor

# task, operator和function "形式上共享"的运行上下文

class ServiceContext:
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]
    
    def __init__(self, service_node: 'ServiceNode', env: 'BaseEnvironment', execution_graph: 'ExecutionGraph' = None):
        
        self.name: str = service_node.name

        self.env_name = env.name
        self.env_base_dir: str = env.env_base_dir
        self.env_uuid = getattr(env, 'uuid', None)  # 使用 getattr 以避免 AttributeError
        self.env_console_log_level = env.console_log_level  # 保存环境的控制台日志等级

        self._logger: Optional[CustomLogger] = None

        
        # 队列描述符管理 - 在构造时从service_node和execution_graph获取
        self._request_queue_descriptor: Optional['BaseQueueDescriptor'] = service_node.service_qd  # 用于service task接收请求
        
        # 从execution_graph获取service response队列描述符 - 直接遍历nodes获取
        self._service_response_queue_descriptors: Dict[str, 'BaseQueueDescriptor'] = {}
        if execution_graph:
            for node_name, node in execution_graph.nodes.items():
                if node.service_response_qd:
                    self._service_response_queue_descriptors[node_name] = node.service_response_qd

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

    def set_request_queue_descriptor(self, descriptor: 'BaseQueueDescriptor'):
        """设置请求队列描述符（用于service task）"""
        self._request_queue_descriptor = descriptor
    
    def get_request_queue_descriptor(self) -> Optional['BaseQueueDescriptor']:
        """获取请求队列描述符"""
        return self._request_queue_descriptor
    
    def set_service_response_queue_descriptors(self, descriptors: Dict[str, 'BaseQueueDescriptor']):
        """设置service response队列描述符（让service可以访问各个response队列）"""
        self._service_response_queue_descriptors = descriptors
    
    def get_service_response_queue_descriptors(self) -> Dict[str, 'BaseQueueDescriptor']:
        """获取service response队列描述符"""
        return self._service_response_queue_descriptors if self._service_response_queue_descriptors else {}
    
    def get_service_response_queue_descriptor(self, node_name: str) -> Optional['BaseQueueDescriptor']:
        """获取指定节点的service response队列描述符"""
        if self._service_response_queue_descriptors:
            return self._service_response_queue_descriptors.get(node_name)
        return None
