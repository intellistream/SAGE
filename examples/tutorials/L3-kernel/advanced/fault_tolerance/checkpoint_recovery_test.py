#!/usr/bin/env python3
"""
Checkpoint 容错机制测试

测试任务在失败后能否从 checkpoint 恢复
"""

import time

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.local_environment import LocalEnvironment


class TestSource(SourceFunction):
    """测试数据源 - 会在第 5 次迭代时模拟失败"""

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.logger.info("TestSource initialized")

    def execute(self, data=None):
        self.counter += 1
        self.logger.info(f"TestSource: generating data #{self.counter}")

        if self.counter > 10:
            self.logger.info("TestSource: finished")
            from sage.kernel.runtime.communication.packet import StopSignal

            return StopSignal("TestSource-completed")

        # 模拟第 5 个数据处理时失败（只失败一次）
        if self.counter == 5 and not hasattr(self, "_failed_once"):
            self._failed_once = True
            self.logger.error("TestSource: simulating failure at counter=5")
            raise RuntimeError("Simulated failure at counter=5")

        # 添加延迟以便观察 checkpoint
        time.sleep(0.5)
        self.logger.debug(f"TestSource: emitting data #{self.counter}")
        return {"id": self.counter, "value": f"data_{self.counter}"}

    def get_state(self):
        """保存状态到 checkpoint"""
        state = {
            "counter": self.counter,
            "_failed_once": getattr(self, "_failed_once", False),
        }
        self.logger.debug(f"TestSource: saving state: {state}")
        return state

    def restore_state(self, state):
        """从 checkpoint 恢复状态"""
        self.counter = state.get("counter", 0)
        if state.get("_failed_once"):
            self._failed_once = True
        self.logger.info(f"TestSource: restored state, counter={self.counter}")


class TestProcessor(MapFunction):
    """测试处理器"""

    def execute(self, data):
        if data is None:
            return None

        self.logger.info(f"TestProcessor: processing {data}")
        return {"id": data["id"], "processed": data["value"].upper()}


class TestSink(SinkFunction):
    """测试输出"""

    def __init__(self):
        super().__init__()
        self.results = []

    def execute(self, data):
        if data is None:
            return None

        self.logger.info(f"TestSink: received {data}")
        self.results.append(data)
        print(f"✅ Processed: ID={data['id']}, Value={data['processed']}")
        return data


def test_checkpoint_recovery():
    """测试 checkpoint 容错恢复"""
    print("\n" + "=" * 60)
    print("Testing Checkpoint-Based Fault Tolerance")
    print("=" * 60 + "\n")

    env = LocalEnvironment(
        "checkpoint_test",
        config={
            "fault_tolerance": {
                "strategy": "checkpoint",
                "checkpoint_interval": 2.0,  # 每 2 秒保存一次
                "max_recovery_attempts": 3,
                "checkpoint_dir": ".sage/test_checkpoints",
            }
        },
    )

    # 启用详细日志
    env.set_console_log_level("INFO")

    print("📝 Configuration:")
    print("  - Strategy: checkpoint")
    print("  - Checkpoint Interval: 2.0s")
    print("  - Max Recovery Attempts: 3")
    print("  - Checkpoint Directory: .sage/test_checkpoints")
    print()

    # 构建管道
    print("🔨 Building pipeline...")
    env.from_source(TestSource).map(TestProcessor).sink(TestSink)
    print("✅ Pipeline built\n")

    # 提交执行
    print("🚀 Submitting pipeline...")
    try:
        env.submit(autostop=True)
        print("\n✅ Pipeline completed successfully")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test Completed")
    print("=" * 60)


def test_restart_recovery():
    """测试重启容错恢复"""
    print("\n" + "=" * 60)
    print("Testing Restart-Based Fault Tolerance")
    print("=" * 60 + "\n")

    env = LocalEnvironment(
        "restart_test",
        config={
            "fault_tolerance": {
                "strategy": "restart",
                "restart_strategy": "exponential",
                "initial_delay": 1.0,
                "max_delay": 5.0,
                "multiplier": 2.0,
                "max_attempts": 3,
            }
        },
    )

    env.set_console_log_level("INFO")

    print("📝 Configuration:")
    print("  - Strategy: restart")
    print("  - Restart Strategy: exponential backoff")
    print("  - Initial Delay: 1.0s")
    print("  - Max Attempts: 3")
    print()

    # 构建管道
    print("🔨 Building pipeline...")
    env.from_source(TestSource).map(TestProcessor).sink(TestSink)
    print("✅ Pipeline built\n")

    # 提交执行
    print("🚀 Submitting pipeline...")
    try:
        env.submit(autostop=True)
        print("\n✅ Pipeline completed successfully")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test Completed")
    print("=" * 60)


if __name__ == "__main__":
    test_checkpoint_recovery()

    print("\n✨ All tests completed!\n")
