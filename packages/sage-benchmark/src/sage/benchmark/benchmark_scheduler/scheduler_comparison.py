#!/usr/bin/env python3
"""
调度器对比示例
演示如何使用不同的调度策略并对比性能指标

@test:timeout=90
@test:category=scheduler
"""

import time

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler


class DataSource(SourceFunction):
    """简单的数据源，生成一批测试数据"""

    def __init__(self, total_items=20, **kwargs):
        super().__init__(**kwargs)
        self.total_items = total_items
        self.current = 0

    def execute(self, data=None):
        if self.current >= self.total_items:
            return None

        data = f"data_{self.current}"
        self.current += 1
        print(f"📤 Source: {data}")
        return data


class HeavyProcessor(MapFunction):
    """模拟资源密集型处理"""

    def execute(self, data):
        # 模拟耗时计算（减少到0.01秒以加快测试）
        time.sleep(0.01)
        result = f"processed_{data}"
        print(f"⚙️  HeavyProcessor: {data} -> {result}")
        return result


class LightFilter(MapFunction):
    """模拟轻量级过滤"""

    def execute(self, data):
        # 只保留偶数编号的数据
        item_id = int(data.split("_")[-1])
        if item_id % 2 == 0:
            print(f"✅ LightFilter: {data} passed")
            return data
        else:
            print(f"❌ LightFilter: {data} filtered")
            return None


class ResultSink(SinkFunction):
    """收集结果"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []

    def execute(self, data):
        if data:
            self.results.append(data)
            print(f"💾 Sink: {data}")


def run_with_scheduler(scheduler, env_class, scheduler_name):
    """使用指定调度器运行 pipeline"""
    print(f"\n{'=' * 60}")
    print(f"🚀 运行实验: {scheduler_name}")
    print(f"{'=' * 60}\n")

    env = None
    try:
        # 创建环境并指定调度器
        if env_class == LocalEnvironment:
            env = LocalEnvironment(name=f"scheduler_test_{scheduler_name}", scheduler=scheduler)
        else:
            env = RemoteEnvironment(name=f"scheduler_test_{scheduler_name}", scheduler=scheduler)

        # 构建 pipeline
        # 注意：并行度在 operator 级别指定
        sink_op = ResultSink()
        (
            env.from_source(DataSource, total_items=10)  # 减少到10个项目以加快测试
            .map(HeavyProcessor, parallelism=2)  # 资源密集型 operator，2 个并行实例
            .filter(LightFilter, parallelism=1)  # 轻量级 operator，1 个并行实例
            .sink(ResultSink)  # type: ignore[arg-type]  # Pass class, not instance
        )

        # 记录开始时间
        start_time = time.time()

        # 提交执行
        print(f"▶️  开始执行 pipeline (调度器: {scheduler_name})...\n")

        # 使用简单的超时机制
        max_wait_time = 30  # 最大等待30秒
        try:
            # 直接提交，如果超时就进行下一个测试
            env.submit(autostop=True)

            # 等待一小段时间确保完成

            wait_start = time.time()
            while time.time() - wait_start < max_wait_time:
                # 检查是否还有活跃任务
                if hasattr(env, "is_running"):
                    is_running_attr = env.is_running
                    # Check if it's a method or property
                    if callable(is_running_attr):
                        if not is_running_attr():
                            break
                    elif not is_running_attr:  # It's a boolean property
                        break
                time.sleep(0.5)

            if time.time() - wait_start >= max_wait_time:
                print(f"⚠️  {scheduler_name} 执行可能超时，但继续收集结果")

        except Exception as e:
            print(f"❌ {scheduler_name} 执行出错: {e}")
            # 不抛出异常，而是记录错误并继续

        # 记录结束时间
        end_time = time.time()
        elapsed = end_time - start_time

        # 获取调度器指标
        try:
            metrics = {}
            if (
                hasattr(env, "scheduler")
                and env.scheduler is not None
                and hasattr(env.scheduler, "get_metrics")
            ):
                metrics = env.scheduler.get_metrics()  # type: ignore[union-attr]
        except Exception as e:
            print(f"⚠️  无法获取调度器指标: {e}")
            metrics = {"error": str(e)}

        print(f"\n{'=' * 60}")
        print(f"📊 {scheduler_name} 执行结果")
        print(f"{'=' * 60}")
        print(f"总耗时: {elapsed:.2f} 秒")
        print(f"处理结果数: {len(sink_op.results) if hasattr(sink_op, 'results') else 'N/A'}")
        print("调度器指标:")
        for key, value in metrics.items():
            print(f"  - {key}: {value}")
        print(f"{'=' * 60}\n")

        return {
            "scheduler": scheduler_name,
            "elapsed_time": elapsed,
            "metrics": metrics,
            "results_count": len(sink_op.results) if hasattr(sink_op, "results") else 0,
        }

    except Exception as e:
        print(f"❌ {scheduler_name} 运行失败: {e}")
        return {
            "scheduler": scheduler_name,
            "elapsed_time": 0,
            "metrics": {"error": str(e)},
            "results_count": 0,
        }
    finally:
        # 确保资源清理
        if env:
            try:
                if hasattr(env, "close"):
                    env.close()
                elif hasattr(env, "shutdown"):
                    env.shutdown()  # type: ignore[union-attr]
            except Exception:  # noqa: S110
                pass


def main():
    """主函数：对比不同调度策略"""

    print(
        """
╔══════════════════════════════════════════════════════════════╗
║           SAGE 调度器对比示例                                  ║
║  演示如何在 Environment 级别配置不同的调度策略                  ║
╚══════════════════════════════════════════════════════════════╝
    """
    )

    # 检测是否在测试模式
    import os

    test_mode = (
        os.environ.get("SAGE_EXAMPLES_MODE") == "test" or os.environ.get("SAGE_TEST_MODE") == "true"
    )

    results = []

    # 实验 1: FIFO 调度器 (LocalEnvironment)
    print("\n🧪 实验 1: FIFO 调度器 (Local)")
    result1 = run_with_scheduler(
        scheduler=FIFOScheduler(),
        env_class=LocalEnvironment,
        scheduler_name="FIFO_Local",
    )
    results.append(result1)

    # 如果在测试模式，只运行一个实验
    if test_mode:
        print("\n⚠️  测试模式：只运行一个调度器实验")
    else:
        time.sleep(2)  # 等待一下

        # 实验 2: 负载感知调度器 (LocalEnvironment)
        print("\n🧪 实验 2: 负载感知调度器 (Local)")
        result2 = run_with_scheduler(
            scheduler=LoadAwareScheduler(max_concurrent=10),
            env_class=LocalEnvironment,
            scheduler_name="LoadAware_Local",
        )
        results.append(result2)

    # 可选：如果有 Ray 环境，可以测试 RemoteEnvironment
    # 注意：需要先启动 JobManager daemon
    try_remote = False  # 设置为 True 以测试 RemoteEnvironment

    if try_remote:
        time.sleep(2)

        # 实验 3: FIFO 调度器 (RemoteEnvironment)
        print("\n🧪 实验 3: FIFO 调度器 (Remote)")
        result3 = run_with_scheduler(
            scheduler="fifo",  # 也可以使用字符串
            env_class=RemoteEnvironment,
            scheduler_name="FIFO_Remote",
        )
        results.append(result3)

        time.sleep(2)

        # 实验 4: 负载感知调度器 (RemoteEnvironment)
        print("\n🧪 实验 4: 负载感知调度器 (Remote)")
        result4 = run_with_scheduler(
            scheduler="load_aware",  # 也可以使用字符串
            env_class=RemoteEnvironment,
            scheduler_name="LoadAware_Remote",
        )
        results.append(result4)

    # 打印对比总结
    print("\n" + "=" * 80)
    print("📈 调度器性能对比总结")
    print("=" * 80)

    for result in results:
        print(f"\n{result['scheduler']}:")
        print(f"  总耗时: {result['elapsed_time']:.2f} 秒")
        print(f"  调度策略: {result['metrics'].get('scheduler_type', 'N/A')}")
        print(f"  已调度任务数: {result['metrics'].get('total_scheduled', 'N/A')}")
        if "avg_latency_ms" in result["metrics"]:
            print(f"  平均延迟: {result['metrics']['avg_latency_ms']:.2f} ms")
        if "avg_resource_utilization" in result["metrics"]:
            print(f"  平均资源利用率: {result['metrics']['avg_resource_utilization']:.2%}")

    print("\n" + "=" * 80)
    print("✅ 所有实验完成！")
    print("=" * 80)

    print(
        """
💡 关键要点：
  1. 用户在创建 Environment 时指定调度策略
     - env = LocalEnvironment(scheduler="fifo")
     - env = RemoteEnvironment(scheduler=LoadAwareScheduler())

  2. 并行度在定义 transformation 时指定
     - .map(HeavyProcessor, parallelism=4)
     - .filter(LightFilter, parallelism=2)

  3. 调度器在应用级别工作，对用户透明
     - 自动根据策略调度所有任务
     - 开发者可以轻松对比不同策略的性能
    """
    )


if __name__ == "__main__":
    main()
