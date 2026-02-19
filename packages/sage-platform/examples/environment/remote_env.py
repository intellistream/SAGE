#!/usr/bin/env python3
"""
FlownetEnvironment 简单示例
演示如何使用 FlownetEnvironment 和调度器

# test_tags: category=environment, timeout=120, requires_daemon=jobmanager
"""

import os
import socket
import time

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.flownet_environment import (
    FlownetEnvironment,  # migrated from RemoteEnvironment (Issue #1443)
)


class SimpleSource(SourceFunction):
    """简单数据源"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0
        self.max_count = 500  # 增加数据量以便观察分布式效果

    def execute(self, data=None):
        if self.count >= self.max_count:
            from sage.kernel.runtime.communication.packet import StopSignal

            return StopSignal("SimpleSource completed")

        data = f"item_{self.count}"
        self.count += 1
        return data


class SimpleProcessor(MapFunction):
    """简单处理器 - 记录运行节点"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import socket as _socket  # 在类内部导入，确保 Ray Actor 可以访问

        self.hostname = _socket.gethostname()
        self.processed_count = 0

    def execute(self, data):
        # 跳过非字符串数据（如 StopSignal）
        if not isinstance(data, str):
            return data
        self.processed_count += 1
        # 在结果中包含处理节点信息
        result = f"{data.upper()} [processed on {self.hostname}]"
        return result


class ConsoleSink(SinkFunction):
    """控制台输出 - 统计节点分布"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.test_mode = (
            os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true"
        )
        self.count = 0
        self.node_stats = {}  # 统计各节点处理数量

    def execute(self, data):
        if data and isinstance(data, str):
            self.count += 1
            # 提取节点信息
            if "[processed on " in data:
                node = data.split("[processed on ")[-1].rstrip("]")
                self.node_stats[node] = self.node_stats.get(node, 0) + 1

            # 测试模式下仅打印前5条
            if not self.test_mode or self.count <= 5:
                print(f"✅ Result: {data}")
            elif self.count == 6:
                print("   ... (remaining output suppressed in test mode)")

            # 每100条打印一次统计
            if self.count % 100 == 0:
                print(f"\n📊 节点分布统计 (已处理 {self.count} 条):")
                for node, cnt in sorted(self.node_stats.items()):
                    print(f"   {node}: {cnt} ({cnt * 100 / self.count:.1f}%)")
                print()


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


def example_default_scheduler():
    """示例 1: 使用分布式调度器 (LoadAware + SPREAD 策略)"""
    print("\n" + "=" * 60)
    print("示例 1: 分布式调度演示")
    print("=" * 60 + "\n")

    # 检查是否在测试模式
    test_mode = os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true"

    # 检查 JobManager 是否可用
    if not check_jobmanager_available():
        if test_mode:
            # 在测试模式下，如果JobManager不可用，跳过测试
            print("⚠️  JobManager daemon 不可用，跳过测试")
            print("   (在生产环境中需要先启动: sage jobmanager start)")
            return
        else:
            print("❌ 错误: JobManager daemon 未运行")
            print("   请先启动: sage jobmanager start")
            return

    # 📊 开始计时
    total_start = time.time()

    # 步骤1: 创建环境 - 使用 load_aware 调度器和 spread 策略
    print("📦 [1/5] 创建 FlownetEnvironment (使用 load_aware 调度器)...")
    step_start = time.time()

    # 使用 LoadAwareScheduler 配置分散策略
    from sage.kernel.scheduler.impl import LoadAwareScheduler

    scheduler = LoadAwareScheduler(
        platform="remote",
        max_concurrent=20,  # 增加并发数
        strategy="spread",  # 使用 SPREAD 策略分散到不同节点
    )

    env = FlownetEnvironment(name="distributed_scheduler_demo", scheduler=scheduler)
    # 设置 JobManager 的可访问主机名（worker 节点通过此地址连接回 JobManager）
    # 注意：JobManager 启动时使用 0.0.0.0 监听，但 worker 需要实际可访问的主机名
    # env.jobmanager_host = "sage-node-1"
    step_duration = time.time() - step_start
    print(f"   ✅ 环境创建完成 (耗时: {step_duration:.3f}秒)")
    print("   📋 调度策略: SPREAD (分散放置到多个节点)\n")

    # 步骤2: 构建数据流 - 增加并行度以利用多节点
    print("🔧 [2/5] 构建数据流 pipeline...")
    step_start = time.time()
    (
        env.from_source(SimpleSource)
        .map(SimpleProcessor, parallelism=8)  # 增加并行度，充分利用集群
        .sink(ConsoleSink)
    )
    step_duration = time.time() - step_start
    print(f"   ✅ Pipeline 构建完成 (耗时: {step_duration:.3f}秒)")
    print("   📋 SimpleProcessor 并行度: 8 (将分布到多个节点)\n")

    # 步骤3: 连接JobManager
    print("🔌 [3/5] 连接到 JobManager...")
    step_start = time.time()
    try:
        # 这里会触发与JobManager的连接
        _ = env.client  # 访问client property确保已创建
        step_duration = time.time() - step_start
        print(f"   ✅ JobManager 连接成功 (耗时: {step_duration:.3f}秒)\n")
    except Exception as e:
        step_duration = time.time() - step_start
        print(f"   ❌ 连接失败 (耗时: {step_duration:.3f}秒)")
        print(f"   错误: {e}\n")
        return

    # 步骤4: 提交任务
    print("🚀 [4/5] 提交任务到 JobManager...")
    step_start = time.time()
    try:
        env.submit(autostop=True)  # 不自动停止,手动控制
        step_duration = time.time() - step_start
        print(f"   ✅ 任务提交成功 (耗时: {step_duration:.3f}秒)\n")
    except Exception as e:
        step_duration = time.time() - step_start
        print(f"   ❌ 任务提交失败 (耗时: {step_duration:.3f}秒)")
        print(f"   错误: {e}\n")
        return

    # 步骤5: 等待执行完成
    print("⏳ [5/5] 等待任务执行...")
    step_start = time.time()
    try:
        # 等待任务执行完成
        env._wait_for_completion()
        step_duration = time.time() - step_start
        print(f"   ✅ 任务执行完成 (耗时: {step_duration:.3f}秒)\n")
    except Exception as e:
        step_duration = time.time() - step_start
        print(f"   ⚠️  任务执行异常 (耗时: {step_duration:.3f}秒)")
        print(f"   错误: {e}\n")

    # 查看调度器指标
    print("📊 获取调度器指标...")
    try:
        metrics = env.get_scheduler_metrics()
        print(f"   调度器指标: {metrics}")

        # 如果使用 LoadAwareScheduler，显示节点使用情况
        if hasattr(scheduler, "node_selector"):
            # 使用 node_task_count 获取节点任务统计
            node_task_count = scheduler.node_selector.node_task_count
            if node_task_count:
                print("\n   📍 节点放置统计:")
                for node_id, count in node_task_count.items():
                    node_info = scheduler.node_selector.get_node(node_id)
                    if node_info:
                        print(f"      {node_info.hostname}: {count} 任务")
                    else:
                        print(f"      {node_id[:12]}...: {count} 任务")
    except Exception as e:
        print(f"   ⚠️  无法获取指标: {e}")
    print()

    # 步骤6: 清理资源（关键步骤）
    print("🧹 [6/6] 清理资源...")
    step_start = time.time()
    try:
        env.close()
        step_duration = time.time() - step_start
        print(f"   ✅ 资源清理完成 (耗时: {step_duration:.3f}秒)\n")
    except Exception as e:
        step_duration = time.time() - step_start
        print(f"   ⚠️  资源清理异常 (耗时: {step_duration:.3f}秒)")
        print(f"   错误: {e}\n")

    # 总体统计
    total_duration = time.time() - total_start
    print("=" * 60)
    print(f"🎉 总耗时: {total_duration:.3f}秒")
    print("=" * 60)


def main():
    """运行所有示例"""
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║        FlownetEnvironment 分布式调度示例                       ║
║                                                              ║
║  演示如何使用 LoadAwareScheduler + SPREAD 策略                 ║
║  将任务分发到集群中的多个节点执行                               ║
╚══════════════════════════════════════════════════════════════╝
    """
    )

    print(
        """
⚠️  注意事项：
  1. 运行前需要启动 JobManager daemon: sage jobmanager start
  2. 确保 Ray 集群已启动: sage cluster start
  3. 如果连接失败，请检查 daemon 和集群状态

📋 分布式调度配置：
  - 调度器: LoadAwareScheduler (负载感知)
  - 策略: SPREAD (分散放置)
  - 并行度: 8 (SimpleProcessor)
  - 数据量: 500 条
    """
    )

    try:
        # 运行示例
        example_default_scheduler()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        print("\n提示: 请确保 JobManager daemon 正在运行")
        print("启动命令: sage jobmanager start")


if __name__ == "__main__":
    main()
