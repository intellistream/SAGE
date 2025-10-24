#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RemoteEnvironment 简单示例
演示如何使用 RemoteEnvironment 和调度器
"""

from sage.kernel.api.function.map_function import MapFunction
from sage.kernel.api.function.sink_function import SinkFunction
from sage.kernel.api.function.source_function import SourceFunction
from sage.kernel.api.remote_environment import RemoteEnvironment


class SimpleSource(SourceFunction):
    """简单数据源"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0
        self.max_count = 10

    def execute(self):
        if self.count >= self.max_count:
            # 返回 StopSignal 来正确停止任务
            # 在函数内部导入以确保 Ray 远程执行时可用
            from sage.kernel.runtime.communication.router.packet import StopSignal
            return StopSignal("SimpleSource completed")

        data = f"item_{self.count}"
        self.count += 1
        return data


class SimpleProcessor(MapFunction):
    """简单处理器"""

    def execute(self, data):
        result = data.upper()
        return result


class ConsoleSink(SinkFunction):
    """控制台输出"""

    def execute(self, data):
        if data:
            print(f"✅ Result: {data}")


def example_default_scheduler():
    """示例 1: 使用默认调度器 (FIFO)"""
    print("\n" + "=" * 60)
    print("示例 1: 使用默认调度器")
    print("=" * 60 + "\n")

    # 不指定 scheduler 参数，使用默认的 FIFO 调度器
    env = RemoteEnvironment(name="default_scheduler_demo")

    (
        env.from_source(SimpleSource)
        .map(SimpleProcessor, parallelism=2)  # 并行度在 operator 级别指定
        .sink(ConsoleSink)
    )

    print("▶️  提交任务...")
    env.submit(autostop=True)

    # 查看调度器指标
    metrics = env.scheduler.get_metrics()
    print(f"\n📊 调度器指标: {metrics}")


def example_fifo_scheduler():
    """示例 2: 显式指定 FIFO 调度器"""
    print("\n" + "=" * 60)
    print("示例 2: 显式指定 FIFO 调度器 (字符串)")
    print("=" * 60 + "\n")

    # 使用字符串指定调度器
    env = RemoteEnvironment(name="fifo_scheduler_demo", scheduler="fifo")  # 字符串方式

    (
        env.from_source(SimpleSource)
        .map(SimpleProcessor, parallelism=3)
        .sink(ConsoleSink)
    )

    print("▶️  提交任务...")
    env.submit(autostop=True)

    metrics = env.scheduler.get_metrics()
    print(f"\n📊 调度器指标: {metrics}")


def example_load_aware_scheduler():
    """示例 3: 使用负载感知调度器"""
    print("\n" + "=" * 60)
    print("示例 3: 使用负载感知调度器")
    print("=" * 60 + "\n")

    # 使用字符串指定负载感知调度器
    env = RemoteEnvironment(
        name="load_aware_demo", scheduler="load_aware"  # 负载感知调度器
    )

    (
        env.from_source(SimpleSource)
        .map(SimpleProcessor, parallelism=4)
        .sink(ConsoleSink)
    )

    print("▶️  提交任务...")
    env.submit(autostop=True)

    metrics = env.scheduler.get_metrics()
    print(f"\n📊 调度器指标: {metrics}")
    print(f"   当前活跃任务: {metrics.get('active_tasks', 'N/A')}")
    print(f"   最大并发数: {metrics.get('max_concurrent', 'N/A')}")


def example_custom_scheduler_instance():
    """示例 4: 使用自定义调度器实例"""
    print("\n" + "=" * 60)
    print("示例 4: 使用自定义调度器实例")
    print("=" * 60 + "\n")

    from sage.kernel.scheduler.impl import LoadAwareScheduler

    # 创建自定义配置的调度器实例
    custom_scheduler = LoadAwareScheduler(
        platform="remote", max_concurrent=15  # 自定义最大并发数
    )

    env = RemoteEnvironment(
        name="custom_scheduler_demo", scheduler=custom_scheduler  # 传入调度器实例
    )

    (
        env.from_source(SimpleSource)
        .map(SimpleProcessor, parallelism=5)
        .sink(ConsoleSink)
    )

    print("▶️  提交任务...")
    env.submit(autostop=True)

    metrics = env.scheduler.get_metrics()
    print(f"\n📊 调度器指标: {metrics}")


def main():
    """运行所有示例"""
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║        RemoteEnvironment 调度器使用示例                        ║
║                                                              ║
║  演示如何在 RemoteEnvironment 中配置和使用调度器                ║
╚══════════════════════════════════════════════════════════════╝
    """
    )

    print(
        """
⚠️  注意事项：
  1. 运行前需要启动 JobManager daemon
  2. 确保 Ray 已正确安装和配置
  3. 如果连接失败，请检查 daemon 是否在运行
    """
    )

    try:
        # 运行示例
        example_default_scheduler()
        example_fifo_scheduler()
        example_load_aware_scheduler()
        example_custom_scheduler_instance()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)

        print(
            """
💡 关键要点：
  
  1️⃣  三种指定调度器的方式：
     • 不指定 (使用默认 FIFO)
       env = RemoteEnvironment()
     
     • 字符串指定
       env = RemoteEnvironment(scheduler="fifo")
       env = RemoteEnvironment(scheduler="load_aware")
     
     • 实例指定
       scheduler = LoadAwareScheduler(max_concurrent=20)
       env = RemoteEnvironment(scheduler=scheduler)
  
  2️⃣  并行度在 operator 级别配置：
     .map(Processor, parallelism=4)
     .filter(Filter, parallelism=2)
  
  3️⃣  调度器在应用级别工作，用户无感知：
     • 自动处理所有任务调度
     • 尊重 operator 的 parallelism 设置
     • 提供性能指标供开发者分析
        """
        )

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n提示: 请确保 JobManager daemon 正在运行")
        print("启动命令: python -m sage.kernel.daemon.start")


if __name__ == "__main__":
    main()
