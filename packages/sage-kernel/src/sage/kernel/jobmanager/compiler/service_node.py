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
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel.runtime.factory.service_task_factory import ServiceTaskFactory
    from sage.kernel.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor
    from sage.kernel.runtime.context.service_context import ServiceContext


def _create_queue_descriptor(env: 'BaseEnvironment', name: str, maxsize: int) -> 'BaseQueueDescriptor':
    """
    根据环境平台类型创建相应的队列描述符
    
    Args:
        env: 环境对象
        name: 队列名称
        maxsize: 队列最大大小
        
    Returns:
        对应平台的队列描述符
    """
    if env.platform == "remote":
        from sage.kernel.runtime.communication.queue_descriptor.ray_queue_descriptor import RayQueueDescriptor
        return RayQueueDescriptor(maxsize=maxsize, queue_id=name)
    else:  # local 或其他情况使用 python 队列
        from sage.kernel.runtime.communication.queue_descriptor.python_queue_descriptor import PythonQueueDescriptor
        return PythonQueueDescriptor(maxsize=maxsize, queue_id=name)


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
        self.service_qd = _create_queue_descriptor(
            env=env,
            name=f"service_request_{self.service_name}",
            maxsize=10000
        )
        
        # 为每个service node创建service response queue descriptor (与graph node一样)
        self.service_response_qd = _create_queue_descriptor(
            env=env,
            name=f"service_response_{self.name}",
            maxsize=10000
        )
    
    def __repr__(self) -> str:
        return f"ServiceNode(name={self.name}, service_name={self.service_name})"
