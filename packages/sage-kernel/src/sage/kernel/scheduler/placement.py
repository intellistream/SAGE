"""
放置策略

定义任务和服务应该部署在本地还是远程（Ray）的策略。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from sage.kernel.core.exceptions import PlacementError

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.scheduler.resource_manager import ResourceManager


class PlacementStrategy(ABC):
    """
    放置策略基类
    
    定义任务放置决策的接口。
    """
    
    @abstractmethod
    def decide_placement(self, node) -> str:
        """
        决定任务放置位置
        
        Args:
            node: 任务节点或服务节点
            
        Returns:
            'local' 或 'remote'
        """
        pass


class SimplePlacementStrategy(PlacementStrategy):
    """
    简单放置策略
    
    基于全局 platform 配置和节点自身的 remote 属性决定放置位置。
    优先级：节点设置 > 全局设置
    """
    
    def __init__(self, platform: str = "local"):
        """
        初始化简单放置策略
        
        Args:
            platform: 全局平台设置 ('local' 或 'remote')
        """
        self.platform = platform
    
    def decide_placement(self, node) -> str:
        """
        决定放置位置
        
        优先使用节点自己的 remote 设置，否则使用全局平台设置。
        
        Args:
            node: 任务节点或服务节点
            
        Returns:
            'local' 或 'remote'
        """
        # 检查节点的 transformation 是否有 remote 属性
        if hasattr(node, 'transformation') and hasattr(node.transformation, 'remote'):
            return "remote" if node.transformation.remote else "local"
        
        # 检查节点的 task_factory 是否有 remote 属性
        if hasattr(node, 'task_factory') and hasattr(node.task_factory, 'remote'):
            return "remote" if node.task_factory.remote else "local"
        
        # 使用全局平台设置
        return "remote" if self.platform == "remote" else "local"


class ResourceAwarePlacementStrategy(PlacementStrategy):
    """
    资源感知放置策略
    
    根据资源可用性动态决定放置位置。
    """
    
    def __init__(self, resource_manager: "ResourceManager"):
        """
        初始化资源感知放置策略
        
        Args:
            resource_manager: 资源管理器实例
        """
        self.resource_manager = resource_manager
    
    def decide_placement(self, node) -> str:
        """
        根据资源可用性决定放置位置
        
        优先选择远程资源（如果可用），否则使用本地资源。
        
        Args:
            node: 任务节点或服务节点
            
        Returns:
            'local' 或 'remote'
            
        Raises:
            PlacementError: 如果没有可用资源
        """
        # 检查远程资源
        if self.resource_manager.has_remote_resources():
            return "remote"
        
        # 检查本地资源
        if self.resource_manager.has_local_resources():
            return "local"
        
        # 没有可用资源
        raise PlacementError("No resources available for task placement")


class HybridPlacementStrategy(PlacementStrategy):
    """
    混合放置策略
    
    结合节点属性和资源状态，智能决定放置位置。
    """
    
    def __init__(
        self, 
        resource_manager: "ResourceManager",
        prefer_remote: bool = True
    ):
        """
        初始化混合放置策略
        
        Args:
            resource_manager: 资源管理器实例
            prefer_remote: 是否优先使用远程资源
        """
        self.resource_manager = resource_manager
        self.prefer_remote = prefer_remote
    
    def decide_placement(self, node) -> str:
        """
        混合决策放置位置
        
        1. 首先检查节点的显式设置
        2. 然后根据资源可用性和偏好决定
        
        Args:
            node: 任务节点或服务节点
            
        Returns:
            'local' 或 'remote'
        """
        # 1. 检查节点的显式设置
        if hasattr(node, 'transformation') and hasattr(node.transformation, 'remote'):
            return "remote" if node.transformation.remote else "local"
        
        # 2. 根据资源和偏好决定
        has_remote = self.resource_manager.has_remote_resources()
        has_local = self.resource_manager.has_local_resources()
        
        if self.prefer_remote and has_remote:
            return "remote"
        elif has_local:
            return "local"
        elif has_remote:
            return "remote"
        else:
            raise PlacementError("No resources available for task placement")


__all__ = [
    "PlacementStrategy",
    "SimplePlacementStrategy",
    "ResourceAwarePlacementStrategy",
    "HybridPlacementStrategy",
]
