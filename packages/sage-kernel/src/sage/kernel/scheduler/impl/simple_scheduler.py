"""
FIFO 调度器 - First-In-First-Out Baseline

最简单的调度策略：按任务到达顺序调度。
适合作为对比实验的 baseline。

特点：
- 简单、可预测
- 按 FIFO 顺序调度
- 尊重 operator 级别的并行度设置
- 适合负载均匀的场景

使用方式:
    # 方式 1: 字符串指定
    env = LocalEnvironment(scheduler="fifo")
    
    # 方式 2: 实例化指定
    from sage.kernel.scheduler.impl import FIFOScheduler
    env = LocalEnvironment(scheduler=FIFOScheduler())
"""

from typing import TYPE_CHECKING, Dict, Any
import time

from sage.kernel.scheduler.api import BaseScheduler

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.task.base_task import BaseTask
    from sage.kernel.runtime.service.base_service_task import BaseServiceTask


class FIFOScheduler(BaseScheduler):
    """
    FIFO 调度器
    
    按照任务到达顺序调度，不进行任何重新排序。
    尊重 transformation.parallelism 设置。
    作为最简单的 baseline。
    """
    
    def __init__(self, platform: str = "local"):
        """
        初始化 FIFO 调度器
        
        Args:
            platform: 平台类型 ('local' 或 'remote')
        """
        self.platform = platform
        self.scheduled_count = 0
        self.total_latency = 0.0
        self.start_times = {}
    
    def schedule_task(self, task_node: "TaskNode", runtime_ctx=None) -> "BaseTask":
        """
        FIFO 调度：直接按顺序调度
        
        并行度由 task_node.transformation.parallelism 决定，
        调度器只负责创建任务实例。
        
        Args:
            task_node: 任务节点（包含 transformation 和 parallelism 信息）
            runtime_ctx: 运行时上下文
            
        Returns:
            创建的任务实例
        """
        start_time = time.time()
        
        # FIFO 策略：直接创建任务，不考虑任何优先级
        # 并行度在 ExecutionGraph 构建时已经处理
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx
        task = task_node.task_factory.create_task(task_node.name, ctx)
        
        # 记录调度指标
        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed
        self.start_times[task_node.name] = start_time
        
        return task
    
    def schedule_service(self, service_node: "ServiceNode", runtime_ctx=None) -> "BaseServiceTask":
        """
        调度服务节点（FIFO 策略同样适用）
        
        Args:
            service_node: 服务节点
            runtime_ctx: 运行时上下文
            
        Returns:
            创建的服务任务实例
        """
        ctx = runtime_ctx if runtime_ctx is not None else service_node.ctx
        service_task = service_node.service_task_factory.create_service_task(ctx)
        return service_task
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取 FIFO 调度器的性能指标
        
        Returns:
            指标字典
        """
        avg_latency = self.total_latency / self.scheduled_count if self.scheduled_count > 0 else 0
        return {
            "scheduler_type": "FIFO",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "platform": self.platform,
        }
    
    def shutdown(self):
        """关闭调度器"""
        self.start_times.clear()


__all__ = ["FIFOScheduler"]
