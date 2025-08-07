"""
ServiceNode - 服务节点类

ServiceNode代表一个服务实例，包含：
- 服务工厂和服务任务工厂
- 服务队列描述符
- 服务运行时上下文
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment
    from sage.kernel.runtime.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.factory.service_task_factory import ServiceTaskFactory
    from sage.kernel.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor
    from sage.kernel.runtime.service_context import ServiceContext


class ServiceNode:
    """
    服务节点类
    
    服务节点，简化版本只记录基本信息
    """
    
    def __init__(self, name: str, service_factory: 'ServiceFactory', service_task_factory: 'ServiceTaskFactory', env: 'BaseEnvironment'):
        """
        服务节点构造函数
        
        Args:
            name: 节点名称
            service_factory: 服务工厂
            service_task_factory: 服务任务工厂
            env: 环境对象
        """
        self.name: str = name
        self.service_factory: 'ServiceFactory' = service_factory
        self.service_task_factory: 'ServiceTaskFactory' = service_task_factory
        self.service_name: str = service_factory.service_name
        
        # 在构造时创建队列描述符
        self._create_queue_descriptors(env)
        
        self.ctx: 'ServiceContext' = None
    
    def _create_queue_descriptors(self, env: 'BaseEnvironment'):
        """在服务节点构造时创建队列描述符"""
        # 为每个service创建request queue descriptor
        self.service_qd = env.get_qd(
            name=f"service_request_{self.service_name}",
            maxsize=10000
        )
        
        # 为每个service node创建service response queue descriptor (与graph node一样)
        self.service_response_qd = env.get_qd(
            name=f"service_response_{self.name}",
            maxsize=10000
        )
    
    def __repr__(self) -> str:
        return f"ServiceNode(name={self.name}, service_name={self.service_name})"
