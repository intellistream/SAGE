from collections import deque
from typing import Any

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.platform.service import BaseService


class ShortTermMemoryService(BaseService):
    def __init__(self, max_dialog: int):
        """
        初始化短期记忆服务

        Args:
            max_dialog: 最大对话数量（队列长度）
        """
        super().__init__()

        self._logger = CustomLogger()
        self.max_dialog = max_dialog

        # 使用 deque 作为队列，设置最大长度
        self.dialog_queue: deque[dict[str, Any]] = deque(maxlen=self.max_dialog)

        self._logger.info(f"ShortTermMemoryService initialized with max_dialog={self.max_dialog}")

    def insert(self, dialog: list[dict[str, str]]) -> None:
        """
        插入一个对话到短期记忆中

        Args:
            dialog: 对话列表，每个元素包含 speaker 和 text 字段
                例如: [{"speaker": "user", "text": "hello"}, {"speaker": "assistant", "text": "hi"}]
                或者: [{"speaker": "user", "text": "hello"}]
        """
        if not isinstance(dialog, list):
            raise TypeError("dialog must be a list")

        # 将对话作为一个整体存入队列
        dialog_entry = {"dialog": dialog}
        self.dialog_queue.append(dialog_entry)

        self._logger.debug(
            f"Inserted dialog with {len(dialog)} message(s). "
            f"Current queue size: {len(self.dialog_queue)}/{self.max_dialog}"
        )

    def retrieve(self) -> list[dict[str, Any]]:
        """
        检索所有短期记忆中的对话

        Returns:
            list[dict[str, Any]]: 对话列表，每个元素为 {"dialog": [...]}
        """
        result = list(self.dialog_queue)
        self._logger.info(f"Retrieved {len(result)} dialog(s) from short-term memory")
        return result


if __name__ == "__main__":

    def test_short_term_memory():
        print("\n" + "=" * 70)
        print("短期记忆服务测试 - 演示插入和窗口滑动")
        print("=" * 70 + "\n")

        # 创建一个最多保存3个对话的短期记忆服务
        print("📝 初始化短期记忆服务 (最大对话数: 3)")
        memory = ShortTermMemoryService(max_dialog=3)
        print(f"   当前队列大小: {len(memory.retrieve())}/{memory.max_dialog}\n")

        # 第1次插入 - 一问一答
        print("=" * 70)
        print("第1次插入 - 一问一答")
        print("=" * 70)
        dialog_1 = [
            {"speaker": "小明", "text": "你好，今天天气真不错！"},
            {"speaker": "小红", "text": "是啊，阳光明媚，心情也很好！"},
        ]
        memory.insert(dialog_1)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  对话 {i}:")
            for msg in entry["dialog"]:
                print(f"    [{msg['speaker']}]: {msg['text']}")
        print()

        # 第2次插入 - 只有陈述
        print("=" * 70)
        print("第2次插入 - 只有陈述（单条消息）")
        print("=" * 70)
        dialog_2 = [
            {"speaker": "小明", "text": "要不要一起去公园散步？"},
        ]
        memory.insert(dialog_2)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  对话 {i}:")
            for msg in entry["dialog"]:
                print(f"    [{msg['speaker']}]: {msg['text']}")
        print()

        # 第3次插入 - 一问一答
        print("=" * 70)
        print("第3次插入 - 一问一答")
        print("=" * 70)
        dialog_3 = [
            {"speaker": "小红", "text": "好啊，我们去湖边走走吧！"},
            {"speaker": "小明", "text": "那里的风景一定很美！"},
        ]
        memory.insert(dialog_3)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog} (已达到最大容量)")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  对话 {i}:")
            for msg in entry["dialog"]:
                print(f"    [{msg['speaker']}]: {msg['text']}")
        print()

        # 第4次插入 - 触发窗口滑动
        print("=" * 70)
        print("第4次插入 - 只有陈述（触发窗口滑动）")
        print("=" * 70)
        dialog_4 = [
            {"speaker": "小红", "text": "我们可以带相机拍照！"},
        ]
        memory.insert(dialog_4)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("⚠️  最旧的1个对话被移除，保留最新的3个对话")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  对话 {i}:")
            for msg in entry["dialog"]:
                print(f"    [{msg['speaker']}]: {msg['text']}")
        print()

        # 第5次插入 - 继续滑动
        print("=" * 70)
        print("第5次插入 - 一问一答（继续窗口滑动）")
        print("=" * 70)
        dialog_5 = [
            {"speaker": "小明", "text": "太好了，我正想记录这美好的一天！"},
            {"speaker": "小红", "text": "那我们现在就出发吧！"},
        ]
        memory.insert(dialog_5)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("⚠️  又有1个旧对话被移除，保留最新的3个对话")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  对话 {i}:")
            for msg in entry["dialog"]:
                print(f"    [{msg['speaker']}]: {msg['text']}")

        print("\n" + "=" * 70)
        print("✅ 测试完成！短期记忆服务采用对话队列方式管理，自动丢弃最旧的对话。")
        print("=" * 70 + "\n")

    CustomLogger.disable_global_console_debug()
    test_short_term_memory()
