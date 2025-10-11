"""
Scheduler Module - 分布式任务调度

调度器设计原则：
1. 对用户透明 - 用户只需在创建 Environment 时指定调度策略
2. 并行度是 operator 级别的配置
3. 调度策略是应用级别的配置

用户使用方式:
    # 基础用法 - 使用默认调度器
    env = LocalEnvironment()

    # 指定调度器类型（字符串）
    env = LocalEnvironment(scheduler="fifo")  # FIFO 策略
    env = LocalEnvironment(scheduler="sla")   # SLA-aware 策略

    # 构建 pipeline（并行度在 operator 级别）
    (env.from_source(MySource)
        .map(MyOperator, parallelism=4)   # 4个并行实例
        .filter(MyFilter, parallelism=2)  # 2个并行实例
        .sink(MySink))

    env.submit()  # 调度器自动工作

开发者对比不同策略:
    from sage.kernel.scheduler.impl import FIFOScheduler, SLAScheduler

    # 实验对比
    for scheduler_cls in [FIFOScheduler, SLAScheduler]:
        env = LocalEnvironment(scheduler=scheduler_cls())
        # 构建和运行 pipeline
        env.submit()
        # 获取指标
        metrics = env.scheduler.get_metrics()
        print(f"{scheduler_cls.__name__}: {metrics}")
"""

from sage.kernel.scheduler.api import BaseScheduler

# 默认调度器在 runtime 中自动选择
# 用户可以通过 Environment(scheduler="type") 指定

__all__ = [
    "BaseScheduler",
]
