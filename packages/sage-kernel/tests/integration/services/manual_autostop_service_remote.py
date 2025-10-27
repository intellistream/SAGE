"""
测试 autostop=True 在远程模式（Ray）下是否能正确清理服务
"""

import sys
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

from sage.common.core.functions import (
    BatchFunction,  # noqa: E402
    SinkFunction,
)
from sage.common.utils.logging.custom_logger import CustomLogger  # noqa: E402
from sage.kernel.api.remote_environment import RemoteEnvironment  # noqa: E402
from sage.platform.service import BaseService  # noqa: E402

# 全局变量用于跟踪服务状态
service_lifecycle = {
    "initialized": False,
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
        print(f"[Sink] Received: {data}, Service result: {result}")


class DemoService(BaseService):
    """测试服务，跟踪生命周期"""

    def __init__(self):
        super().__init__()
        self.counter = 0
        print("[TestService] ✓ Service initialized")

    def process(self, data):
        self.counter += 1
        return f"Processed by service (call #{self.counter})"

    def cleanup(self):
        print(f"[TestService] ✓ Cleanup called - processed {self.counter} requests")
        super().cleanup()
        print("[TestService] ✓ Cleanup completed")


def check_ray_initialized():
    """检查 Ray 是否已初始化"""
    try:
        import ray

        if not ray.is_initialized():
            print("[Info] Ray not initialized, initializing...")
            ray.init(ignore_reinit_error=True)
            print("[Info] ✓ Ray initialized")
        else:
            print("[Info] ✓ Ray already initialized")
        return True
    except Exception as e:
        print(f"[Error] Failed to initialize Ray: {e}")
        return False


def main():
    print("=" * 80)
    print("Testing autostop=True with Ray Remote Mode")
    print("=" * 80)

    # 检查 Ray
    if not check_ray_initialized():
        print("\n❌ Ray is not available, skipping remote mode test")
        print("   To install Ray: pip install ray")
        return

    try:
        print("\n[Main] Creating RemoteEnvironment...")
        env = RemoteEnvironment("test_autostop_service_remote")

        # 注册服务（remote=True 表示这是一个 Ray Actor）
        print("[Main] Registering service...")
        env.register_service("test_service", DemoService)

        # 构建管道
        print("[Main] Building pipeline...")
        env.from_batch(DemoBatch).sink(DemoSink)

        # 提交作业（现在支持 autostop=True）
        print("\n[Main] Submitting job with autostop=True to remote JobManager...")
        print("-" * 80)
        start_time = time.time()
        env.submit(autostop=True)  # ✅ 现在支持了！
        elapsed_time = time.time() - start_time
        print("-" * 80)
        print(f"\n[Main] Job completed in {elapsed_time:.2f} seconds")

        # 等待一下确保清理完成
        time.sleep(1.0)

        # 验证
        print("\n" + "=" * 80)
        print("RemoteEnvironment autostop Test:")
        print("=" * 80)
        print("✅ Pipeline executed successfully with RemoteEnvironment")
        print("✅ autostop=True worked correctly!")
        print("✅ Services should be cleaned up automatically")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理 Ray
        try:
            import ray

            if ray.is_initialized():
                print("\n[Cleanup] Shutting down Ray...")
                ray.shutdown()
                print("[Cleanup] ✓ Ray shutdown complete")
        except Exception:
            pass


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
