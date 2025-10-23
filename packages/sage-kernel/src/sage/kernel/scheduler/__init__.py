"""
Scheduler Module - 分布式任务调度（重构后架构）

Layer: L3 (Kernel - Scheduler)
Dependencies: sage.platform (L2), sage.common (L1)

架构原则：
1. 职责分离：
   - Scheduler: 纯决策者（返回 PlacementDecision）
   - PlacementExecutor: 纯执行者（接收决策，执行放置）
   - Dispatcher: 协调者（决策 → 执行）

2. 对用户透明：
   - 用户只需在创建 Environment 时指定调度策略
   - 并行度是 operator 级别的配置
   - 调度策略是应用级别的配置

用户使用方式:
    from sage.kernel import LocalEnvironment

    # 基础用法 - 使用默认调度器（FIFO）
    env = LocalEnvironment()

    # 指定调度器类型（字符串）
    env = LocalEnvironment(scheduler="fifo")       # FIFO 策略
    env = LocalEnvironment(scheduler="load_aware") # 负载感知策略

    # 构建 pipeline
    (env.from_source(MySource)
        .map(MyOperator, parallelism=4)
        .sink(MySink))

    env.submit()  # Dispatcher 协调 Scheduler 和 Placement

开发者对比不同策略:
    from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler

    # 实验对比
    for scheduler_cls in [FIFOScheduler, LoadAwareScheduler]:
        env = LocalEnvironment(scheduler=scheduler_cls())
        env.submit()
        metrics = env.scheduler.get_metrics()
        print(f"{scheduler_cls.__name__}: {metrics}")

详细说明请查看:
    FLOW_EXPLANATION.md - 调度和放置流程说明
    ARCHITECTURE.md - 架构设计文档
                decision = scheduler.make_decision(node)

                # 2. 根据决策等待（如果需要）
                if decision.delay > 0:
                    time.sleep(decision.delay)

                # 3. 执行物理放置
                task = placement_executor.place_task(node, decision)
"""

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.placement import PlacementExecutor

# 核心组件：
# - BaseScheduler: 调度器抽象基类
# - PlacementDecision: 调度决策数据结构
# - PlacementExecutor: 放置执行器

__all__ = [
    "BaseScheduler",
    "PlacementDecision",
    "PlacementExecutor",
]
