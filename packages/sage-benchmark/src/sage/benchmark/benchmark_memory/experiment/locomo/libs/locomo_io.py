import json
import os

from sage.benchmark.benchmark_memory.data.locomo.locomo_dataloader import (
    LocomoDataLoader,
)
from sage.kernel.api.function.batch_function import BatchFunction
from sage.kernel.api.function.sink_function import SinkFunction


class LocomoSource(BatchFunction):
    """从Locomo数据集中逐个读取对话轮次的Source"""

    def __init__(self, sample_id):
        self.sample_id = sample_id
        self.loader = LocomoDataLoader()

        # 获取所有session和对话轮数
        self.turns = self.loader.get_turn(sample_id)

        # 统计总的dialog数量
        total_dialogs = sum((max_dialog_idx + 1) for _, max_dialog_idx in self.turns)
        print(f"📊 样本 {sample_id} 统计信息:")
        print(f"   - 总会话数: {len(self.turns)}")
        print(f"   - 总对话数: {total_dialogs}")
        for idx, (session_id, max_dialog_idx) in enumerate(self.turns):
            dialog_count = max_dialog_idx + 1
            print(
                f"   - 会话 {idx+1} (session_id={session_id}): {dialog_count} 个对话 (max_dialog_idx={max_dialog_idx})"
            )

        # 初始化指针
        self.session_idx = 0  # 当前session在turns列表中的索引
        self.dialog_ptr = 0  # 当前dialog指针（偶数）

    def execute(self):
        # 检查是否已经遍历完所有session
        if self.session_idx >= len(self.turns):
            print(f"🏁 LocomoSource 已完成：所有 {len(self.turns)} 个会话已处理完毕")
            return None

        # 获取当前session信息
        session_id, max_dialog_idx = self.turns[self.session_idx]

        # 检查当前session是否已经遍历完
        if self.dialog_ptr > max_dialog_idx:
            # 移动到下一个session
            print(
                f"➡️  会话 {session_id} 已完成 (dialog_ptr={self.dialog_ptr} > max={max_dialog_idx})，移动到下一个会话"
            )
            self.session_idx += 1
            self.dialog_ptr = 0

            # 检查是否还有更多session
            if self.session_idx >= len(self.turns):
                print(
                    f"🏁 LocomoSource 已完成：所有 {len(self.turns)} 个会话已处理完毕"
                )
                return None

            # 更新到新session的信息
            session_id, max_dialog_idx = self.turns[self.session_idx]
            print(
                f"🆕 移动到新会话：session_id={session_id}, max_dialog_idx={max_dialog_idx}"
            )

        # 打印当前执行信息
        print(
            f"📊 LocomoSource.execute()：session_idx={self.session_idx}/{len(self.turns)}, session={session_id}, dialog={self.dialog_ptr}, max={max_dialog_idx}"
        )

        # 获取当前对话
        try:
            print(f"📖 正在获取对话：session={session_id}, dialog={self.dialog_ptr}")
            dialogs = self.loader.get_dialog(
                self.sample_id, session_x=session_id, dialog_y=self.dialog_ptr
            )

            # 准备返回数据
            result = {
                "sample_id": self.sample_id,
                "session_id": session_id,
                "dialog_idx": self.dialog_ptr,
                "dialogs": dialogs,
            }

            # 移动指针到下一组对话（每次+2，因为一组对话包含问答两轮）
            self.dialog_ptr += 2
            print(
                f"⚡ LocomoSource 返回数据：session={session_id}, dialog={self.dialog_ptr-2}"
            )

            return result

        except Exception as e:
            print(
                f"❌ 获取对话时出错 session {session_id}, dialog {self.dialog_ptr}: {e}"
            )
            import traceback

            traceback.print_exc()
            # 出错时移动到下一个dialog，返回None让下次execute()调用处理
            self.dialog_ptr += 2
            return None


class LocomoSink(SinkFunction):
    """将接收到的对话数据写入JSON文件的Sink"""

    def __init__(self, output_name=None):
        self.output_name = output_name

        # 创建输出目录
        self.output_dir = ".benchmarks/benchmark_memory/locomo"
        os.makedirs(self.output_dir, exist_ok=True)

        # 输出文件路径 - 使用output_name或稍后使用self.name
        self.output_file = None  # 延迟初始化，等ctx注入后再设置

        # 初始化数据列表
        self.data_list = []

        # 统计实际处理的dialog数量
        self.total_dialog_count = 0

    def execute(self, data):
        import time

        time.sleep(0.1)  # 模拟处理延迟
        # 延迟初始化输出文件路径（第一次调用时）
        if self.output_file is None:
            # 使用output_name或self.name（由BaseFunction提供）
            file_name = self.output_name if self.output_name else self.name
            self.output_file = os.path.join(self.output_dir, f"{file_name}.json")
            print(f"📁 LocomoSink 已初始化：输出文件={self.output_file}")

        # 打印接收信息
        session_id = data.get("session_id")
        dialog_idx = data.get("dialog_idx")
        dialogs = data.get("dialogs", [])
        dialog_count = len(dialogs)
        print(
            f"📥 LocomoSink 已接收：会话 {session_id}, 对话 {dialog_idx} ({dialog_count} 轮)"
        )

        # 将数据添加到列表
        self.data_list.append(data)

        # 累计实际的dialog数量
        self.total_dialog_count += dialog_count

        # 实时写入文件
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.data_list, f, ensure_ascii=False, indent=2)

        # 打印保存成功信息
        print(
            f"✅ LocomoSink 已保存：会话 {session_id}, 对话 {dialog_idx} (总对话数: {self.total_dialog_count}, 总记录数: {len(self.data_list)})"
        )


# ==== 测试代码 ====
if __name__ == "__main__":
    import time

    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.api.local_environment import LocalEnvironment

    # 禁用debug日志
    CustomLogger.disable_global_console_debug()

    # 获取第一个sample_id进行测试
    loader = LocomoDataLoader()
    sample_ids = loader.get_sample_id()
    test_sample_id = sample_ids[0]

    print(f"🧪 使用样本 ID 进行测试: {test_sample_id}")
    print("=" * 60)

    # 创建环境和pipeline
    env = LocalEnvironment("Test_Locomo_IO")
    env.from_batch(LocomoSource, sample_id=test_sample_id).sink(
        LocomoSink, output_name="test"
    )
    env.submit(autostop=True)

    print("=" * 60)
    print("✅ 测试完成！请查看输出文件: .benchmarks/benchmark_memory/locomo/test.json")
