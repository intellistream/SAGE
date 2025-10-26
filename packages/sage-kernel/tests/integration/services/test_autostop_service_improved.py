"""
改进的测试：验证 autostop=True 能正确清理服务
使用监控线程来跟踪服务状态的变化
"""

import sys
import threading
import time
from pathlib import Path

# 添加 SAGE 包路径
repo_root = Path(__file__).parent
src_paths = [
    repo_root / "packages" / "sage" / "src",
    repo_root / "packages" / "sage-common" / "src",
    repo_root / "packages" / "sage-kernel" / "src",
    repo_root / "packages" / "sage-middleware" / "src",
    repo_root / "packages" / "sage-libs" / "src",
    repo_root / "packages" / "sage-tools" / "src",
]
for p in src_paths:
    sys.path.insert(0, str(p))

from sage.common.core.functions import BatchFunction  # noqa: E402
from sage.common.core.functions import (
    SinkFunction,
)
from sage.common.utils.logging.custom_logger import CustomLogger  # noqa: E402
from sage.kernel.api.local_environment import LocalEnvironment  # noqa: E402
from sage.platform.service import BaseService  # noqa: E402

# 全局变量用于跟踪服务状态
service_lifecycle = {
    "initialized": False,
    "running": False,
    "cleanup_called": False,
    "cleanup_completed": False,
}


class DemoBatch(BatchFunction):
    """简单的批处理函数"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 5

    def execute(self):
        if self.counter >= self.max_count:
            return None
        self.counter += 1
        return f"Message {self.counter}"


class DemoSink(SinkFunction):
    """测试 Sink，会调用服务"""

    def execute(self, data):
        result = self.call_service("test_service", method="process", data=data)
        print(f"Sink received: {data}, Service result: {result}")


class DemoService(BaseService):
    """测试服务，跟踪生命周期"""

    def __init__(self):
        super().__init__()
        self.counter = 0
        service_lifecycle["initialized"] = True
        service_lifecycle["running"] = True
        print("[TestService] ✓ Service initialized")

    def process(self, data):
        self.counter += 1
        return f"Processed by service (call #{self.counter})"

    def cleanup(self):
        print(f"[TestService] ✓ Cleanup called - processed {self.counter} requests")
        service_lifecycle["cleanup_called"] = True
        service_lifecycle["running"] = False
        super().cleanup()
        service_lifecycle["cleanup_completed"] = True
        print("[TestService] ✓ Cleanup completed")


def monitor_dispatcher_state(env, stop_event):
    """监控 dispatcher 状态的线程"""
    env_uuid = None
    while not stop_event.is_set():
        if env_uuid is None and env.env_uuid:
            env_uuid = env.env_uuid

        if env_uuid:
            job_info = env.jobmanager.jobs.get(env_uuid)
            if job_info:
                dispatcher = job_info.dispatcher
                print(
                    f"[Monitor] Tasks: {len(dispatcher.tasks)}, Services: {len(dispatcher.services)}, Running: {dispatcher.is_running}"
                )

        time.sleep(0.5)


def main():
    print("=" * 80)
    print("Improved Test: autostop=True with service lifecycle tracking")
    print("=" * 80)

    env = LocalEnvironment("test_autostop_service_improved")

    # 启动监控线程
    stop_monitor = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_dispatcher_state, args=(env, stop_monitor), daemon=True
    )
    monitor_thread.start()

    # 注册服务
    print("\n[Main] Registering service...")
    env.register_service("test_service", DemoService)

    # 构建管道
    print("[Main] Building pipeline...")
    env.from_batch(DemoBatch).sink(DemoSink)

    # 提交作业
    print("\n[Main] Submitting job with autostop=True...")
    print("-" * 80)
    start_time = time.time()
    env.submit(autostop=True)
    elapsed_time = time.time() - start_time
    print("-" * 80)
    print(f"\n[Main] Job completed in {elapsed_time:.2f} seconds")

    # 停止监控线程
    stop_monitor.set()
    monitor_thread.join(timeout=1.0)

    # 验证服务生命周期
    print("\n" + "=" * 80)
    print("Service Lifecycle Verification:")
    print("=" * 80)
    print(f"  ✓ Initialized:       {service_lifecycle['initialized']}")
    print(
        f"  ✓ Was Running:       {service_lifecycle['initialized']}"
    )  # 如果初始化了就运行过
    print(f"  ✓ Cleanup Called:    {service_lifecycle['cleanup_called']}")
    print(f"  ✓ Cleanup Completed: {service_lifecycle['cleanup_completed']}")
    print(f"  ✓ Currently Running: {service_lifecycle['running']}")

    # 最终验证
    print("\n" + "=" * 80)
    if service_lifecycle["cleanup_completed"] and not service_lifecycle["running"]:
        print("✅ SUCCESS: Service was properly initialized, used, and cleaned up!")
    else:
        print("❌ FAILURE: Service lifecycle incomplete")
        if not service_lifecycle["cleanup_called"]:
            print("  - Cleanup was NOT called")
        if not service_lifecycle["cleanup_completed"]:
            print("  - Cleanup did NOT complete")
        if service_lifecycle["running"]:
            print("  - Service is still marked as running")
    print("=" * 80)


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
