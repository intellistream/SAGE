"""
调度器抽象基类

定义了调度器的接口和抽象方法。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.task.base_task import BaseTask
    from sage.kernel.runtime.service.base_service_task import BaseServiceTask


class BaseScheduler(ABC):
    """
    调度器抽象基类
    
    定义了任务调度器必须实现的接口。
    """
    
    @abstractmethod
    def schedule_task(self, node: "TaskNode") -> "BaseTask":
        """
        调度一个任务节点
        
        Args:
            node: 任务节点（来自执行图）
            
        Returns:
            创建的任务实例（LocalTask 或 RayTask）
        """
        pass
    
    @abstractmethod
    def schedule_service(self, node: "ServiceNode") -> "BaseServiceTask":
        """
        调度一个服务节点
        
        Args:
            node: 服务节点（来自执行图）
            
        Returns:
            创建的服务任务实例
        """
        pass
    
    @abstractmethod
    def get_placement_decision(self, node) -> str:
        """
        获取放置决策
        
        Args:
            node: 任务或服务节点
            
        Returns:
            放置位置：'local' 或 'remote'
        """
        pass
    
    def shutdown(self):
        """
        关闭调度器，释放资源
        
        默认实现为空，子类可以覆盖。
        """
        pass


__all__ = ["BaseScheduler"]
