"""Pipeline-as-Service 简化示例 - 使用底层封装

这个示例展示如何使用 SAGE Kernel 提供的 Pipeline-as-Service 基础设施。

【关键变化】：
- 不再需要手动实现 PipelineBridge
- 不再需要手动实现 PipelineServiceSource
- 不再需要手动实现 PipelineServiceSink
- 不再需要手动实现 PipelineService

【简化后的代码】：
只需要关注业务逻辑（Map 算子）！

运行: python examples/tutorials/L4-middleware/memory_service/simple_pipeline_service_demo.py
"""

from __future__ import annotations

from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
)


# ============================================================
# 业务逻辑：只需要实现自定义的 Map 算子
# ============================================================


class SimpleProcessor(MapFunction):
    """简单的处理器 - 这是唯一需要自定义的部分"""

    def execute(self, data):
        if not data:
            return None

        # 从请求中提取数据
        payload = data.payload if hasattr(data, "payload") else data["payload"]
        number = payload.get("number", 0)

        # 业务逻辑：计算平方
        result = number**2

        # 返回结果（带上 response_queue）
        resp_q = (
            data.response_queue
            if hasattr(data, "response_queue")
            else data["response_queue"]
        )
        return {
            "payload": {"result": result, "original": number},
            "response_queue": resp_q,
        }


# ============================================================
# 主 Pipeline 的算子
# ============================================================


class NumberBatch(BatchFunction):
    """批量数字源"""

    def __init__(self, numbers):
        super().__init__()
        self.numbers = list(numbers)
        # 添加 shutdown 命令
        self.numbers.append({"command": "shutdown"})
        self.index = 0

    def execute(self):
        if self.index >= len(self.numbers):
            return None

        item = self.numbers[self.index]
        self.index += 1

        if isinstance(item, dict) and item.get("command") == "shutdown":
            return item

        return {"number": item}


class CallProcessor(MapFunction):
    """调用处理服务"""

    def execute(self, data):
        if not data:
            return None

        # 处理 shutdown
        if data.get("command") == "shutdown":
            print("\n[Main] 发送 shutdown 命令")
            return self.call_service("processor", data)

        # 正常处理
        number = data["number"]
        print(f"\n[Main] 处理数字: {number}")
        result = self.call_service("processor", data)
        return result


class DisplayResult(SinkFunction):
    """显示结果"""

    def execute(self, data):
        if not data:
            return

        if isinstance(data, dict):
            if data.get("status") == "shutdown_ack":
                print("[Main] ✅ 服务已关闭\n")
                return

            result = data.get("result")
            original = data.get("original")
            if result is not None:
                print(f"[Main] 结果: {original}² = {result}")


# ============================================================
# 主函数
# ============================================================


def main():
    print("=" * 60)
    print("Pipeline-as-Service 简化示例")
    print("使用 SAGE Kernel 底层封装")
    print("=" * 60 + "\n")

    CustomLogger.disable_global_console_debug()

    # 测试数据
    numbers = [1, 2, 3, 4, 5]

    # 创建环境
    env = LocalEnvironment("simple_demo")

    # ====================================
    # 关键：只需要 3 行代码！
    # ====================================

    # 1. 创建 Bridge
    bridge = PipelineBridge()

    # 2. 注册服务（使用通用的 PipelineService）
    env.register_service("processor", PipelineService, bridge)

    # 3. 创建服务 Pipeline（使用通用的 Source 和 Sink）
    env.from_source(PipelineServiceSource, bridge).map(SimpleProcessor).sink(
        PipelineServiceSink
    )

    # ====================================
    # 主 Pipeline（正常创建）
    # ====================================
    env.from_batch(NumberBatch, numbers).map(CallProcessor).sink(DisplayResult)

    print("🚀 启动 Pipeline...\n")
    env.submit(autostop=True)

    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)
    print("\n总结：")
    print("  • Bridge、Source、Sink、Service 都使用底层封装")
    print("  • 只需要实现业务逻辑（Map 算子）")
    print("  • 代码量大幅减少，复用性大幅提高\n")


if __name__ == "__main__":
    main()
