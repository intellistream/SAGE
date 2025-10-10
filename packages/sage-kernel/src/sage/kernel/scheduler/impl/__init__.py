"""
Scheduler Implementation Module - 调度器实现模块

这个模块包含各种调度策略的具体实现，供开发者对比实验使用。

调度策略在 Environment 级别配置：
    env = LocalEnvironment(scheduler="fifo")  # 使用 FIFO 调度器
    env = LocalEnvironment(scheduler="load_aware")  # 使用负载感知调度器

已实现的 Baseline 策略:
- FIFOScheduler: 先进先出调度（最简单）
- LoadAwareScheduler: 负载感知调度（考虑系统资源）

待实现的策略:
- PriorityScheduler: 优先级调度
- RoundRobinScheduler: 轮询调度
- CostOptimizedScheduler: 成本优化调度
"""

from sage.kernel.scheduler.impl.simple_scheduler import FIFOScheduler
from sage.kernel.scheduler.impl.resource_aware_scheduler import LoadAwareScheduler

__all__ = [
    "FIFOScheduler",
    "LoadAwareScheduler",
]
