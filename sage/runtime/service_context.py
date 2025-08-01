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
# task, operator和function "形式上共享"的运行上下文

class ServiceContext:
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]
    def __init__(self, graph_node: 'GraphNode', transformation: 'BaseTransformation', env: 'BaseEnvironment'):
        
        self.name:str = graph_node.name

        self.env_name = env.name
        self.env_base_dir:str = env.env_base_dir
        self.env_uuid = getattr(env, 'uuid', None)  # 使用 getattr 以避免 AttributeError
        self.env_console_log_level = env.console_log_level  # 保存环境的控制台日志等级

        self._logger:Optional[CustomLogger] = None

        
        # 队列描述符管理
        self.input_qd: Optional['BaseQueueDescriptor'] = None

        self.response_qds: Optional[Dict[str, 'BaseQueueDescriptor']] = None  # service task访问各个response队列



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