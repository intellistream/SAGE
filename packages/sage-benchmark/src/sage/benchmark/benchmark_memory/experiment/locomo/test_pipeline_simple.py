"""简化的测试版本 - 验证 Pipeline-as-Service 架构是否正常工作"""

from sage.benchmark.benchmark_memory.data.locomo.locomo_dataloader import LocomoDataLoader
from sage.common.core import BatchFunction, MapFunction, SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
)


class SimpleLocomoSource(BatchFunction):
    """简化的 Source - 只处理前3轮对话"""

    def __init__(self, sample_id):
        self.sample_id = sample_id
        self.loader = LocomoDataLoader()
        self.turns = self.loader.get_turn(sample_id)
        self.count = 0
        self.max_count = 3  # 只处理3轮

    def execute(self):
        if self.count >= self.max_count:
            print(f"🏁 SimpleLocomoSource 完成，已发送 {self.count} 轮对话")
            return None

        # 获取第一个 session 的第一轮对话
        session_id, max_dialog_idx = self.turns[0]
        dialog_idx = self.count * 2

        dialogs = self.loader.get_dialog(self.sample_id, session_x=session_id, dialog_y=dialog_idx)

        self.count += 1

        result = {
            "sample_id": self.sample_id,
            "session_id": session_id,
            "dialog_idx": dialog_idx,
            "dialogs": dialogs,
        }

        print(
            f"📤 SimpleLocomoSource 发送: Session {session_id}, Dialog {dialog_idx} ({self.count}/{self.max_count})"
        )
        return result


class SimpleServiceMap(MapFunction):
    """简化的服务 Map - 只累积历史，不调用 LLM"""

    def __init__(self):
        super().__init__()
        self.history_count = 0

    def execute(self, data):
        if not data:
            return None

        # data 是 PipelineRequest 对象
        payload = data.payload
        session_id = payload["session_id"]
        dialog_idx = payload["dialog_idx"]
        dialogs = payload["dialogs"]

        self.history_count += len(dialogs)

        print(
            f"🔧 SimpleServiceMap 处理: Session {session_id}, Dialog {dialog_idx}, 历史累计: {self.history_count}"
        )

        # 简单返回，不生成答案
        result_payload = {
            "session_id": session_id,
            "dialog_idx": dialog_idx,
            "answers": [],  # 空答案列表
            "history_count": self.history_count,
        }

        # 修改 payload 并返回 PipelineRequest 对象
        data.payload = result_payload
        return data


class SimpleControllerMap(MapFunction):
    """简化的 Controller Map"""

    def execute(self, data):
        if not data:
            return None

        print(
            f"📝 SimpleControllerMap: 调用服务处理 Session {data['session_id']}, Dialog {data['dialog_idx']}"
        )

        result = self.call_service("simple_service", data, method="process", timeout=30.0)

        print("✅ SimpleControllerMap: 收到服务响应")
        print(f"   类型: {type(result)}")
        print(f"   内容: {result}")

        # 关键：必须返回结果，才能传递到下游 Sink
        return result


def main():
    print("=" * 60)
    print("简化测试：验证 Pipeline-as-Service 架构")
    print("=" * 60)

    CustomLogger.disable_global_console_debug()

    # 获取测试样本
    loader = LocomoDataLoader()
    sample_ids = loader.get_sample_id()
    test_sample_id = sample_ids[0]

    print(f"\n📊 使用样本: {test_sample_id}")
    print("只处理前 3 轮对话进行测试\n")

    # 创建环境
    env = LocalEnvironment("simple_test")

    # 创建 Bridge 和注册服务
    print("【创建桥梁和服务】")
    bridge = PipelineBridge()
    env.register_service("simple_service", PipelineService, bridge)

    # 创建服务 Pipeline
    print("【创建服务 Pipeline】")
    env.from_source(PipelineServiceSource, bridge).map(SimpleServiceMap).sink(PipelineServiceSink)

    # 创建主 Pipeline
    print("【创建主 Pipeline】")

    class SimpleSink(SinkFunction):
        def execute(self, data):
            print(f"🔍 SimpleSink 收到数据: {data}")
            if data:
                print(
                    f"💾 Sink 接收: Session {data['session_id']}, Dialog {data['dialog_idx']}, 历史数: {data['history_count']}"
                )

    env.from_batch(SimpleLocomoSource, sample_id=test_sample_id).map(SimpleControllerMap).sink(
        SimpleSink
    )

    print("\n" + "=" * 60)
    print("🚀 启动 Pipeline")
    print("=" * 60 + "\n")

    env.submit(autostop=True)

    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
