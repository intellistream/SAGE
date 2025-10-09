"""
任务调度器

负责创建和调度任务及服务，整合资源管理和放置策略。
"""

from typing import TYPE_CHECKING, Optional

from sage.kernel.scheduler.base import BaseScheduler
from sage.kernel.scheduler.resource_manager import ResourceManager
from sage.kernel.scheduler.placement import PlacementStrategy, SimplePlacementStrategy

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.task.base_task import BaseTask
    from sage.kernel.runtime.service.base_service_task import BaseServiceTask


class TaskScheduler(BaseScheduler):
    """
    任务调度器
    
    负责调度任务和服务的创建，整合资源管理和放置策略。
    """
    
    def __init__(
        self, 
        platform: str = "local",
        placement_strategy: Optional[PlacementStrategy] = None,
        resource_manager: Optional[ResourceManager] = None
    ):
        """
        初始化任务调度器
        
        Args:
            platform: 平台类型 ('local' 或 'remote')
            placement_strategy: 放置策略，如果为 None 则使用 SimplePlacementStrategy
            resource_manager: 资源管理器，如果为 None 则创建新实例
        """
        self.platform = platform
        
        # 初始化资源管理器
        self.resource_manager = resource_manager or ResourceManager(platform)
        
        # 初始化放置策略
        self.placement_strategy = placement_strategy or SimplePlacementStrategy(platform)
    
    def schedule_task(self, task_node: "TaskNode", runtime_ctx=None) -> "BaseTask":
        """
        调度任务节点
        
        使用节点的 task_factory 创建任务实例。
        
        Args:
            task_node: 任务节点（来自执行图）
            runtime_ctx: 运行时上下文（可选，默认使用 task_node.ctx）
            
        Returns:
            创建的任务实例（LocalTask 或 RayTask）
        """
        # 1. 决定放置位置（用于日志和监控）
        placement = self.placement_strategy.decide_placement(task_node)
        
        # 2. 分配资源（可选，当前为简化实现）
        # self.resource_manager.allocate_resource(task_node.name, "cpu", 1.0)
        
        # 3. 使用运行时上下文（如果提供）或节点上下文
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx
        
        # 4. 使用节点的 task_factory 创建任务
        # task_factory 内部会根据 remote 属性决定创建 LocalTask 还是 RayTask
        task = task_node.task_factory.create_task(task_node.name, ctx)
        
        return task
    
    def schedule_service(self, service_node: "ServiceNode", runtime_ctx=None) -> "BaseServiceTask":
        """
        调度服务节点
        
        使用节点的 service_task_factory 创建服务任务实例。
        
        Args:
            service_node: 服务节点（来自执行图）
            runtime_ctx: 运行时上下文（可选，默认使用 service_node.ctx）
            
        Returns:
            创建的服务任务实例
        """
        # 1. 使用运行时上下文（如果提供）或节点上下文
        ctx = runtime_ctx if runtime_ctx is not None else service_node.ctx
        
        # 2. 使用 service_task_factory 创建服务任务
        service_task = service_node.service_task_factory.create_service_task(ctx)
        
        return service_task
    
    def get_placement_decision(self, node) -> str:
        """
        获取放置决策
        
        Args:
            node: 任务节点或服务节点
            
        Returns:
            'local' 或 'remote'
        """
        return self.placement_strategy.decide_placement(node)
    
    def get_resource_status(self):
        """
        获取资源状态
        
        Returns:
            资源状态信息
        """
        return {
            "platform": self.platform,
            "available_resources": self.resource_manager.get_available_resources(),
            "resource_usage": self.resource_manager.get_resource_usage(),
        }
    
    def shutdown(self):
        """
        关闭调度器，释放资源
        """
        # 当前无需特殊清理
        pass


__all__ = ["TaskScheduler"]
