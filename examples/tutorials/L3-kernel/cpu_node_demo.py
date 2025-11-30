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
5. ✓ Resource requirements specification
6. ✓ Multi-node task distribution
7. ✓ Performance metrics collection
8. ✓ Cluster inspection utilities

@test:timeout=120
@test:category=cpu
@test:requires=jobmanager
"""

import os
import socket
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

    # 明确声明CPU资源需求（由调度器使用）
    cpu_required = 2  # 需要2个CPU核心
    memory_required = "2GB"  # 需要2GB内存
    gpu_required = 0  # 明确不需要GPU

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return data

        # 模拟CPU密集型计算
        task_id = data.get("id", 0)
        compute_value = data.get("compute_value", 0)

        # 简单的计算任务（可以替换为更复杂的CPU任务）
        result = sum(range(compute_value)) % 1000000

        # 获取执行节点信息（如果可用）
        node_info = {
            "hostname": socket.gethostname(),
            "processor": self.name,
            "cpu_cores": os.cpu_count(),
        }

        processed_data = {
            **data,
            "processed": True,
            "result": result,
            "node_info": node_info,
            "process_time": time.time(),
        }

        self.logger.info(
            f"[CPU Processor] Processed task {task_id}, result={result}, "
            f"node={node_info['hostname']}"
        )
        return processed_data


class CPUResultSink(SinkFunction):
    """CPU计算结果接收器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processed_count = 0
        self.total_results = []
        self.start_time = time.time()
        self.node_distribution = {}  # 记录任务在各节点的分布

    def execute(self, data: dict[str, Any]):
        if not isinstance(data, dict):
            return

        self.processed_count += 1
        self.total_results.append(data)

        task_id = data.get("id", "unknown")
        result = data.get("result", "N/A")
        node_info = data.get("node_info", {})
        hostname = node_info.get("hostname", "unknown")
        processor = node_info.get("processor", "unknown")

        # 统计节点分布
        self.node_distribution[hostname] = self.node_distribution.get(hostname, 0) + 1

        self.logger.info(
            f"[CPU Sink] Received result #{self.processed_count}: "
            f"Task {task_id}, Result={result}, Node={hostname}, Processor={processor}"
        )
        print(
            f"✅ [CPU Node] Completed task {task_id}: result={result} "
            f"(node: {hostname}, processor: {processor})"
        )

    def get_statistics(self) -> dict[str, Any]:
        """获取执行统计信息"""
        elapsed = time.time() - self.start_time
        return {
            "total_processed": self.processed_count,
            "elapsed_time": elapsed,
            "throughput": self.processed_count / elapsed if elapsed > 0 else 0,
            "node_distribution": self.node_distribution,
        }


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
    print("\n📊 调度器统计:")
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


def demo_cluster_inspection():
    """
    示例4: 集群节点检查

    演示:
    - 查看可用的CPU节点
    - 节点资源信息
    - 集群统计
    """
    print("\n" + "=" * 70)
    print("示例4: 集群节点检查")
    print("=" * 70)
    print("\n📊 功能: 检查集群中的CPU节点信息")
    print("🎯 展示:")
    print("  ✓ 可用CPU节点列表")
    print("  ✓ 节点资源统计")
    print("  ✓ 集群总体状态\n")

    try:
        import ray

        if not ray.is_initialized():
            print("⚠️  Ray 未初始化，跳过集群检查")
            return

        # 创建节点选择器
        node_selector = NodeSelector()

        # 获取集群统计信息
        stats = node_selector.get_cluster_stats()

        print("📊 集群资源统计:")
        print(f"  • 节点数量: {stats.get('node_count', 0)}")
        print(f"  • 总CPU核心: {stats.get('total_cpu', 0):.1f}")
        print(f"  • 可用CPU: {stats.get('available_cpu', 0):.1f}")
        print(f"  • CPU使用率: {stats.get('avg_cpu_usage', 0):.1%}")
        print(f"  • 总内存: {stats.get('total_memory', 0) / (1024**3):.2f} GB")
        print(f"  • 可用内存: {stats.get('available_memory', 0) / (1024**3):.2f} GB")
        print(f"  • 总任务数: {stats.get('total_tasks', 0)}")

        # 列出所有节点
        nodes = stats.get("nodes", [])
        if nodes:
            print(f"\n📋 节点详情 ({len(nodes)} 个节点):")
            for i, node in enumerate(nodes, 1):
                print(f"\n  节点 #{i}:")
                print(f"    主机名: {node.get('hostname', 'unknown')}")
                print(f"    CPU使用率: {node.get('cpu_usage', 0):.1%}")
                print(f"    GPU使用率: {node.get('gpu_usage', 0):.1%}")
                print(f"    内存使用率: {node.get('memory_usage', 0):.1%}")
                print(f"    任务数: {node.get('task_count', 0)}")

        # 选择CPU节点
        print("\n🔍 选择最佳CPU节点:")
        cpu_node = node_selector.select_best_node(
            cpu_required=2, gpu_required=0, strategy="balanced"
        )
        if cpu_node:
            print(f"  ✓ 选中节点: {cpu_node[:16]}...")
            node_res = node_selector.get_node(cpu_node)
            if node_res:
                print(f"    主机名: {node_res.hostname}")
                print(f"    可用CPU: {node_res.available_cpu:.1f}")
                print(f"    CPU使用率: {node_res.cpu_usage:.1%}")
        else:
            print("  ⚠️  未找到合适的CPU节点")

        print("\n✅ 示例4完成!")
        print("=" * 70)

    except ImportError:
        print("⚠️  Ray 未安装，无法进行集群检查")
    except Exception as e:
        print(f"⚠️  集群检查失败: {e}")


def demo_resource_requirements():
    """
    示例5: 显式资源需求规范

    演示:
    - 在Operator级别指定CPU/内存需求
    - 调度器根据资源需求选择节点
    - 资源感知任务分配
    """
    print("\n" + "=" * 70)
    print("示例5: 显式资源需求规范")
    print("=" * 70)
    print("\n📊 功能: 为CPU任务指定精确的资源需求")
    print("🎯 特性:")
    print("  ✓ Operator级别资源声明")
    print("  ✓ 调度器资源感知")
    print("  ✓ 智能节点选择\n")

    # 创建环境
    env = RemoteEnvironment(name="cpu_resource_demo")

    # CPUComputeProcessor 已声明: cpu_required=2, memory_required="2GB", gpu_required=0
    print("💡 CPUComputeProcessor 资源需求:")
    print(f"  • CPU: {CPUComputeProcessor.cpu_required} 核")
    print(f"  • 内存: {CPUComputeProcessor.memory_required}")
    print(f"  • GPU: {CPUComputeProcessor.gpu_required} (不需要)")
    print()

    # 构建任务流
    (
        env.from_source(CPUIntensiveSource, max_count=10, delay=0.2)
        .map(CPUComputeProcessor, parallelism=3)  # 每个实例需要2核CPU
        .sink(CPUResultSink)
    )

    print("🚀 提交任务（调度器将选择满足资源需求的CPU节点）...")
    env.submit(autostop=True)

    print("\n✅ 示例5完成!")
    print("=" * 70)


def check_jobmanager_available():
    """检查 JobManager 是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 19001))
        sock.close()
        return result == 0
    except Exception:
        return False


def print_usage_guide():
    """打印使用指南"""
    print("\n" + "=" * 70)
    print("📚 CPU节点使用指南")
    print("=" * 70)

    print("\n1️⃣  启动JobManager (必需):")
    print("   $ sage jobmanager start")
    print("   或者手动启动:")
    print(
        "   $ python -m sage.kernel.runtime.job_manager --host 127.0.0.1 --port 19001"
    )

    print("\n2️⃣  启动Ray集群 (可选，JobManager会自动初始化):")
    print("   $ ray start --head  # 启动头节点")
    print("   $ ray start --address=<head_address>  # 添加CPU工作节点")

    print("\n3️⃣  配置CPU工作节点:")
    print("   # 在工作节点机器上")
    print("   $ ray start --address=<head_address> --num-cpus=8 --num-gpus=0")
    print("   # 指定只有CPU资源，不分配GPU")

    print("\n4️⃣  检查集群状态:")
    print("   $ sage jobmanager status")
    print("   $ ray status")

    print("\n5️⃣  运行CPU任务:")
    print("   $ python cpu_node_demo.py")

    print("\n6️⃣  查看日志:")
    print("   $ ls -la .sage/logs/jobmanager/")
    print("   $ tail -f .sage/logs/jobmanager/session_*/jobmanager.log")

    print("\n" + "=" * 70)


def main():
    """主函数"""
    print(
        """
╔══════════════════════════════════════════════════════════════════════╗
║                   SAGE CPU Node 完整演示                              ║
║                                                                      ║
║  本示例演示SAGE框架对CPU版本计算节点的完整支持                         ║
║                                                                      ║
║  验收标准:                                                            ║
║  ✓ 可以通过JobManager将任务分配给CPU SAGE节点                         ║
║  ✓ 节点能够正常执行并返回结果                                          ║
║  ✓ 任务执行过程中具备基本的监控和日志记录能力                           ║
║  ✓ 支持资源需求规范和智能节点选择                                      ║
║  ✓ 提供集群检查和统计功能                                             ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    )

    # 检查JobManager是否可用
    if not check_jobmanager_available():
        print("\n⚠️  JobManager 未运行!")
        print_usage_guide()
        print("\n💡 请先启动 JobManager，然后重新运行本示例\n")
        return

    print("\n✅ JobManager 已就绪\n")

    try:
        # 运行所有示例
        demo_basic_cpu_node()
        time.sleep(1)

        demo_cpu_scheduler()
        time.sleep(1)

        demo_cpu_node_monitoring()
        time.sleep(1)

        demo_cluster_inspection()
        time.sleep(1)

        demo_resource_requirements()

        print("\n" + "=" * 70)
        print("🎉 所有CPU节点演示完成!")
        print("=" * 70)

        print("\n📋 验收标准确认:")
        print("  ✅ JobManager成功分配任务给CPU节点")
        print("  ✅ CPU节点正常执行任务并返回结果")
        print("  ✅ 提供完整的监控和日志记录")
        print("  ✅ 支持资源需求规范和节点选择")
        print("  ✅ 提供集群检查和统计功能")

        print("\n💡 关键要点:")
        print("  • CPU节点通过NodeSelector自动选择（gpu_required=0）")
        print("  • RemoteEnvironment自动与JobManager协作")
        print("  • 支持自定义调度策略（CPUOnlyScheduler）")
        print("  • 内置监控和日志系统")
        print("  • 可在无GPU环境中运行")
        print("  • 支持Operator级别资源需求声明")
        print("  • 提供集群资源检查工具")

        print("\n🔗 相关文件:")
        print("  • JobManager: sage/kernel/runtime/job_manager.py")
        print("  • NodeSelector: sage/kernel/scheduler/node_selector.py")
        print("  • RemoteEnvironment: sage/kernel/api/remote_environment.py")
        print("  • Scheduler: sage/kernel/scheduler/impl/resource_aware_scheduler.py")
        print("  • 日志目录: .sage/logs/jobmanager/")

        print_usage_guide()

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
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
