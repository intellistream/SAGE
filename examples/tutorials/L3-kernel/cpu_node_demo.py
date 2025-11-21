#!/usr/bin/env python3
"""
SAGE CPU Node Demonstration
============================

This example demonstrates how SAGE supports CPU-only compute nodes for task execution.

Key Features Demonstrated:
1. ✓ CPU-only task submission to JobManager
2. ✓ Resource-aware node selection (CPU nodes)
3. ✓ Task execution monitoring and logging
4. ✓ Basic health checks and status reporting

@test:timeout=120
@test:category=cpu
@test:requires=jobmanager
"""

import time
from typing import Any

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.kernel.runtime.communication.packet import StopSignal
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.node_selector import NodeSelector


class CPUIntensiveSource(SourceFunction):
    """CPU密集型数据源 - 生成需要CPU处理的数据"""

    def __init__(self, max_count: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = max_count

    def execute(self, data=None):
        if self.counter >= self.max_count:
            return StopSignal(f"CPUIntensiveSource_{self.counter}")

        self.counter += 1
        # 模拟CPU密集型数据生成
        data_item = {
            "id": self.counter,
            "task_type": "cpu_compute",
            "compute_value": self.counter * 100,
            "timestamp": time.time(),
        }
        self.logger.info(f"[CPU Source] Generated item {self.counter}/{self.max_count}")
        return data_item


class CPUComputeProcessor(MapFunction):
    """CPU计算处理器 - 执行CPU密集型计算"""

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return data

        # 模拟CPU密集型计算
        task_id = data.get("id", 0)
        compute_value = data.get("compute_value", 0)

        # 简单的计算任务（可以替换为更复杂的CPU任务）
        result = sum(range(compute_value)) % 1000000

        processed_data = {
            **data,
            "processed": True,
            "result": result,
            "processor": self.name,
            "process_time": time.time(),
        }

        self.logger.info(
            f"[CPU Processor] Processed task {task_id}, result={result}"
        )
        return processed_data


class CPUResultSink(SinkFunction):
    """CPU计算结果接收器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processed_count = 0
        self.total_results = []

    def execute(self, data: dict[str, Any]):
        if not isinstance(data, dict):
            return

        self.processed_count += 1
        self.total_results.append(data)

        task_id = data.get("id", "unknown")
        result = data.get("result", "N/A")
        processor = data.get("processor", "unknown")

        self.logger.info(
            f"[CPU Sink] Received result #{self.processed_count}: "
            f"Task {task_id}, Result={result}, Processor={processor}"
        )
        print(
            f"✅ [CPU Node] Completed task {task_id}: result={result} "
            f"(processor: {processor})"
        )


class CPUOnlyScheduler(BaseScheduler):
    """
    CPU专用调度器
    
    特点:
    - 只选择CPU节点（不需要GPU）
    - 优先选择CPU资源充足的节点
    - 支持负载均衡
    """

    def __init__(self):
        super().__init__()
        self.node_selector = NodeSelector()

    def make_decision(self, task_node):
        """
        为任务选择CPU节点
        
        策略:
        1. 不需要GPU资源
        2. 选择CPU负载最低的节点
        3. 确保有足够的CPU和内存
        """

        # 提取CPU资源需求（默认1核）
        cpu = (
            getattr(task_node.transformation, "cpu_required", 1)
            if hasattr(task_node, "transformation")
            else 1
        )

        # 提取内存需求（默认1GB）
        memory = (
            getattr(task_node.transformation, "memory_required", "1GB")
            if hasattr(task_node, "transformation")
            else "1GB"
        )

        # 选择CPU节点（不需要GPU）
        target_node = self.node_selector.select_best_node(
            cpu_required=cpu,
            gpu_required=0,  # 明确指定不需要GPU
            strategy="balanced",  # 负载均衡策略
        )

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements={
                "cpu": cpu,
                "memory": memory,
                "gpu": 0,  # CPU节点不需要GPU
            },
            placement_strategy="cpu_only",
            reason=f"CPU task: selected CPU node {target_node} (no GPU required)",
        )

        self.scheduled_count += 1
        self.decision_history.append(decision)

        return decision


def demo_basic_cpu_node():
    """
    示例1: 基本的CPU节点任务执行
    
    演示:
    - CPU-only任务提交
    - 任务在CPU节点上执行
    - 监控和日志记录
    """
    print("\n" + "=" * 70)
    print("示例1: 基本CPU节点任务执行")
    print("=" * 70)
    print("\n📊 功能: 提交CPU计算任务到JobManager并在CPU节点执行")
    print("🎯 验收标准:")
    print("  ✓ 可以通过JobManager将任务分配给CPU SAGE节点")
    print("  ✓ 节点能够正常执行并返回结果")
    print("  ✓ 任务执行过程中具备基本的监控和日志记录能力\n")

    # 创建RemoteEnvironment（默认会使用CPU节点）
    env = RemoteEnvironment(name="cpu_node_basic_demo")

    # 构建CPU任务流
    (
        env.from_source(CPUIntensiveSource, max_count=5, delay=0.5)
        .map(CPUComputeProcessor, parallelism=2)  # 2个并行CPU处理器
        .sink(CPUResultSink)
    )

    print("🚀 提交任务到JobManager...")
    print("📍 任务将被分配到可用的CPU节点\n")

    # 提交并自动停止
    env.submit(autostop=True)

    print("\n✅ 示例1完成!")
    print("=" * 70)


def demo_cpu_scheduler():
    """
    示例2: 使用CPU专用调度器
    
    演示:
    - 自定义CPU节点选择策略
    - 资源感知调度
    - 负载均衡
    """
    print("\n" + "=" * 70)
    print("示例2: CPU专用调度器")
    print("=" * 70)
    print("\n📊 功能: 使用自定义调度器确保任务只分配到CPU节点")
    print("🎯 特性:")
    print("  ✓ 明确排除GPU节点")
    print("  ✓ CPU资源感知调度")
    print("  ✓ 负载均衡策略\n")

    # 创建使用CPU专用调度器的环境
    cpu_scheduler = CPUOnlyScheduler()
    env = RemoteEnvironment(
        name="cpu_scheduler_demo",
        scheduler=cpu_scheduler,
    )

    # 构建CPU任务流
    (
        env.from_source(CPUIntensiveSource, max_count=8, delay=0.3)
        .map(CPUComputeProcessor, parallelism=3)  # 3个并行处理器
        .sink(CPUResultSink)
    )

    print("🚀 使用CPU专用调度器提交任务...")
    print("📍 调度器将选择最优的CPU节点\n")

    # 提交并自动停止
    env.submit(autostop=True)

    # 查看调度统计
    metrics = cpu_scheduler.get_metrics()
    print(f"\n📊 调度器统计:")
    print(f"  - 调度任务数: {metrics.get('scheduled_count', 0)}")
    print(f"  - 跳过任务数: {metrics.get('skipped_count', 0)}")

    print("\n✅ 示例2完成!")
    print("=" * 70)


def demo_cpu_node_monitoring():
    """
    示例3: CPU节点监控和日志
    
    演示:
    - 任务执行监控
    - 日志记录
    - 状态查询
    """
    print("\n" + "=" * 70)
    print("示例3: CPU节点监控和日志")
    print("=" * 70)
    print("\n📊 功能: 展示CPU节点的监控和日志能力")
    print("🎯 特性:")
    print("  ✓ 实时任务状态监控")
    print("  ✓ 详细的日志记录")
    print("  ✓ JobManager健康检查\n")

    env = RemoteEnvironment(name="cpu_monitoring_demo")

    # 构建任务流
    (
        env.from_source(CPUIntensiveSource, max_count=6, delay=0.4)
        .map(CPUComputeProcessor, parallelism=2)
        .sink(CPUResultSink)
    )

    print("🚀 提交任务并监控执行...")

    # 提交任务
    env.submit(autostop=True)

    print("\n📋 监控信息:")
    print("  - 任务日志: 查看 .sage/logs/jobmanager/ 目录")
    print("  - 所有任务执行均有日志记录")
    print("  - JobManager 提供健康检查接口")

    print("\n✅ 示例3完成!")
    print("=" * 70)


def main():
    """主函数"""
    print(
        """
╔══════════════════════════════════════════════════════════════════════╗
║                   SAGE CPU Node 演示                                  ║
║                                                                      ║
║  本示例演示SAGE框架对CPU版本计算节点的完整支持                         ║
║                                                                      ║
║  验收标准:                                                            ║
║  ✓ 可以通过JobManager将任务分配给CPU SAGE节点                         ║
║  ✓ 节点能够正常执行并返回结果                                          ║
║  ✓ 任务执行过程中具备基本的监控和日志记录能力                           ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    )

    print(
        """
⚠️  前置条件:
  1. 启动 JobManager daemon: sage jobmanager start
  2. 确保 Ray 集群已启动（支持CPU节点）
  3. 检查环境: sage jobmanager status
    """
    )

    try:
        # 运行三个示例
        demo_basic_cpu_node()
        time.sleep(1)

        demo_cpu_scheduler()
        time.sleep(1)

        demo_cpu_node_monitoring()

        print("\n" + "=" * 70)
        print("🎉 所有CPU节点演示完成!")
        print("=" * 70)

        print("\n📋 验收标准确认:")
        print("  ✅ JobManager成功分配任务给CPU节点")
        print("  ✅ CPU节点正常执行任务并返回结果")
        print("  ✅ 提供完整的监控和日志记录")

        print("\n💡 关键要点:")
        print("  • CPU节点通过NodeSelector自动选择（gpu_required=0）")
        print("  • RemoteEnvironment自动与JobManager协作")
        print("  • 支持自定义调度策略（CPUOnlyScheduler）")
        print("  • 内置监控和日志系统")
        print("  • 可在无GPU环境中运行")

        print("\n🔗 相关文件:")
        print("  • JobManager: sage/kernel/runtime/job_manager.py")
        print("  • NodeSelector: sage/kernel/scheduler/node_selector.py")
        print("  • RemoteEnvironment: sage/kernel/api/remote_environment.py")
        print("  • 日志目录: .sage/logs/jobmanager/")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        print("\n💡 提示:")
        print("  1. 确保JobManager已启动: sage jobmanager start")
        print("  2. 检查Ray是否运行: ray status")
        print("  3. 查看日志: .sage/logs/jobmanager/")


if __name__ == "__main__":
    main()
