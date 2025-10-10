"""
Scheduler API - 调度器核心 API 定义

调度器设计原则：
1. 对用户透明 - 用户只需在创建 Environment 时指定调度策略
2. 并行度是 operator 级别的 - 在定义 transformation 时指定
3. 调度策略是应用级别的 - 在 Environment 中配置

用户使用示例:
    # 应用级别指定调度策略
    env = LocalEnvironment(scheduler="fifo")  # 或 "sla", "priority" 等
    
    # operator 级别指定并行度
    (env.from_source(MySource)
        .map(MyOperator, parallelism=4)  # 4个并行实例
        .filter(MyFilter, parallelism=2)  # 2个并行实例
        .sink(MySink))
    
    env.submit()  # 调度器自动处理

开发者使用示例（对比不同调度策略）:
    from sage.kernel.scheduler.impl import FIFOScheduler, SLAScheduler
    
    # 策略 1
    env1 = LocalEnvironment(scheduler=FIFOScheduler())
    # 策略 2  
    env2 = LocalEnvironment(scheduler=SLAScheduler())
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.task.base_task import BaseTask
    from sage.kernel.runtime.service.base_service_task import BaseServiceTask


class BaseScheduler(ABC):
    """
    调度器抽象基类
    
    调度器在 Environment 级别配置，对用户透明。
    并行度在 operator 级别指定（transformation.parallelism）。
    """
    
    @abstractmethod
    def schedule_task(self, node: "TaskNode", runtime_ctx=None) -> "BaseTask":
        """
        调度任务节点
        
        调度器根据：
        - node.transformation.parallelism (并行度)
        - 当前系统负载
        - 调度策略
        做出调度决策。
        
        Args:
            node: 任务节点（包含 transformation 和 parallelism 信息）
            runtime_ctx: 运行时上下文
            
        Returns:
            创建的任务实例（LocalTask 或 RayTask）
        """
        pass
    
    @abstractmethod
    def schedule_service(self, node: "ServiceNode", runtime_ctx=None) -> "BaseServiceTask":
        """
        调度服务节点
        
        Args:
            node: 服务节点
            runtime_ctx: 运行时上下文
            
        Returns:
            创建的服务任务实例
        """
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取调度器性能指标（供开发者对比不同策略）
        
        Returns:
            指标字典，例如：
            {
                'total_scheduled': 100,
                'avg_latency_ms': 45.2,
                'resource_utilization': 0.85
            }
        """
        return {}
    
    def shutdown(self):
        """关闭调度器，释放资源"""
        pass


__all__ = ["BaseScheduler"]
