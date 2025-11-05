import json
import os

from sage.benchmark.benchmark_memory.data.locomo.locomo_dataloader import LocomoDataLoader
from sage.common.core import BatchFunction, SinkFunction


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
                f"   - 会话 {idx + 1} (session_id={session_id}): {dialog_count} 个对话 (max_dialog_idx={max_dialog_idx})"
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
            self.session_idx += 1
            self.dialog_ptr = 0

            # 检查是否还有更多session
            if self.session_idx >= len(self.turns):
                # 最后一个 session 处理完毕（不再打印）
                return None

            # 更新到新session的信息
            session_id, max_dialog_idx = self.turns[self.session_idx]

        # 获取当前对话
        try:
            dialogs = self.loader.get_dialog(
                self.sample_id, session_x=session_id, dialog_y=self.dialog_ptr
            )

            # 准备返回数据（不再打印）
            result = {
                "sample_id": self.sample_id,
                "session_id": session_id,
                "dialog_idx": self.dialog_ptr,
                "dialogs": dialogs,
            }

            # 移动指针到下一组对话（每次+2，因为一组对话包含问答两轮）
            self.dialog_ptr += 2

            return result

        except Exception as e:
            print(f"❌ 获取对话时出错 session {session_id}, dialog {self.dialog_ptr}: {e}")
            import traceback

            traceback.print_exc()
            # 出错时移动到下一个dialog，返回None让下次execute()调用处理
            self.dialog_ptr += 2
            return None


class LocomoSink(SinkFunction):
    """将接收到的问题和答案写入JSON文件的Sink

    注意：这里只写入问题和答案，不写入对话历史
    """

    def __init__(self, output_name=None):
        self.output_name = output_name

        # 创建输出目录
        self.output_dir = ".benchmarks/benchmark_memory/locomo"
        os.makedirs(self.output_dir, exist_ok=True)

        # 输出文件路径 - 使用output_name或稍后使用self.name
        self.output_file = None  # 延迟初始化，等ctx注入后再设置

        # 初始化数据列表
        self.data_list = []

        # 统计信息
        self.total_answer_count = 0

    def execute(self, data):
        # 延迟初始化输出文件路径（第一次调用时）
        if self.output_file is None:
            # 使用output_name或self.name（由BaseFunction提供）
            file_name = self.output_name if self.output_name else self.name
            self.output_file = os.path.join(self.output_dir, f"{file_name}.json")
            # 不再打印初始化信息

        # 只有当有答案时才保存
        answers = data.get("answers", [])

        if len(answers) > 0:
            # 将数据添加到列表
            self.data_list.append(data)

            # 累计统计
            self.total_answer_count += len(answers)

            # 实时写入文件
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(self.data_list, f, ensure_ascii=False, indent=2)

    @staticmethod
    def query_answers(json_file_path, session_id, dialog_idx):
        """从保存的 JSON 文件中检索指定 session 和 dialog 的所有问答

        Args:
            json_file_path: JSON 文件路径
            session_id: session 号
            dialog_idx: dialog 号

        Returns:
            list: 该轮对话的所有问答，格式为 [{"question": ..., "answer": ..., "evidence": ..., "category": ...}, ...]
                  如果没有找到，返回空列表
        """
        try:
            with open(json_file_path, encoding="utf-8") as f:
                data_list = json.load(f)

            for item in data_list:
                if item["session_id"] == session_id and item["dialog_idx"] == dialog_idx:
                    return item.get("answers", [])

            return []
        except FileNotFoundError:
            print(f"文件不存在: {json_file_path}")
            return []
        except json.JSONDecodeError:
            print(f"文件格式错误: {json_file_path}")
            return []


# ==== 测试代码 ====
if __name__ == "__main__":
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
    env.from_batch(LocomoSource, sample_id=test_sample_id).sink(LocomoSink, output_name="test")
    env.submit(autostop=True)

    print("=" * 60)
    print("✅ 测试完成！请查看输出文件: .benchmarks/benchmark_memory/locomo/test.json")
