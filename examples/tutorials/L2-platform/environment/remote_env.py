#!/usr/bin/env python3
"""
RemoteEnvironment 简单示例
演示如何使用 RemoteEnvironment 和调度器

# test_tags: category=environment, timeout=120, requires_daemon=jobmanager
"""

import os
import time

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.remote_environment import RemoteEnvironment


class SimpleSource(SourceFunction):
    """简单数据源"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0
        # 在测试模式下减少数据量，加快测试速度
        test_mode = (
            os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true"
        )
        self.max_count = 100 if test_mode else 10000

    def execute(self, data=None):
        if self.count >= self.max_count:
            from sage.kernel.runtime.communication.packet import StopSignal

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 在测试模式下限制输出
        self.test_mode = (
            os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true"
        )
        self.count = 0

    def execute(self, data):
        if data:
            self.count += 1
            # 测试模式下仅打印前5条和最后的统计
            if not self.test_mode or self.count <= 5:
                print(f"✅ Result: {data}")
            elif self.count == 6:
                print("   ... (remaining output suppressed in test mode)")


def check_jobmanager_available():
    """检查 JobManager 是否可用"""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 19001))
        sock.close()
        return result == 0
    except Exception:
        return False


def example_default_scheduler():
    """示例 1: 使用默认调度器 (FIFO)"""
    print("\n" + "=" * 60)
    print("示例 1: 使用默认调度器")
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

    # 步骤1: 创建环境
    print("📦 [1/5] 创建 RemoteEnvironment...")
    step_start = time.time()
    env = RemoteEnvironment(name="default_scheduler_demo")
    step_duration = time.time() - step_start
    print(f"   ✅ 环境创建完成 (耗时: {step_duration:.3f}秒)\n")

    # 步骤2: 构建数据流
    print("🔧 [2/5] 构建数据流 pipeline...")
    step_start = time.time()
    (
        env.from_source(SimpleSource)
        .map(SimpleProcessor, parallelism=2)  # 并行度在 operator 级别指定
        .sink(ConsoleSink)
    )
    step_duration = time.time() - step_start
    print(f"   ✅ Pipeline 构建完成 (耗时: {step_duration:.3f}秒)\n")

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
        env.submit(autostop=False)  # 不自动停止,手动控制
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
        print(f"   调度器指标: {metrics}\n")
    except Exception as e:
        print(f"   ⚠️  无法获取指标: {e}\n")

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
║        RemoteEnvironment 调度器使用示例                        ║
║                                                              ║
║  演示如何在 RemoteEnvironment 中配置和使用调度器                ║
║  增加了详细的时间追踪和进度输出                                 ║
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
