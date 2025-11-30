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

    def insert(self, entry: str, vector=None, metadata: dict | None = None) -> None:
        """
        插入一条对话记录到短期记忆中

        Args:
            entry: 对话文本字符串（已格式化，如 "(2023-08-01)Alice: Hello"）
            vector: 向量（为统一接口保留，但 STM 不使用）
            metadata: 元数据（可选）
        """
        if not isinstance(entry, str):
            raise TypeError("entry must be a string")

        # 存储格式统一为 {"text": "...", "metadata": {...}}
        data = {"text": entry}
        if metadata:
            data["metadata"] = metadata

        self.dialog_queue.append(data)

        self._logger.debug(
            f"Inserted dialog text. Current queue size: {len(self.dialog_queue)}/{self.max_dialog}"
        )

    def retrieve(
        self, query: Any = None, vector=None, metadata: dict | None = None
    ) -> list[dict[str, Any]]:
        """
        检索所有短期记忆中的对话

        Args:
            query: 查询参数（对于短期记忆服务，此参数不使用，但保留以统一接口）
            vector: 向量（为统一接口保留，但 STM 不使用）
            metadata: 元数据（为统一接口保留，但 STM 不使用）

        Returns:
            list[dict[str, Any]]: 统一格式 [{"text": "...", "metadata": {...}}, ...]
        """
        result = list(self.dialog_queue)
        self._logger.info(f"Retrieved {len(result)} dialog(s) from short-term memory")
        return result


if __name__ == "__main__":

    def test_short_term_memory():
        print("\n" + "=" * 70)
        print("短期记忆服务测试 - 演示插入和窗口滑动（新接口）")
        print("=" * 70 + "\n")

        # 创建一个最多保存3个对话的短期记忆服务
        print("📝 初始化短期记忆服务 (最大对话数: 3)")
        memory = ShortTermMemoryService(max_dialog=3)
        print(f"   当前队列大小: {len(memory.retrieve())}/{memory.max_dialog}\n")

        # 第1次插入 - 格式化的对话文本
        print("=" * 70)
        print("第1次插入 - 格式化对话文本")
        print("=" * 70)
        text_1 = "(2023-08-01)小明: 你好，今天天气真不错！"
        memory.insert(text_1)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  记忆 {i}: {entry['text']}")
        print()

        # 第2次插入
        print("=" * 70)
        print("第2次插入 - 格式化对话文本")
        print("=" * 70)
        text_2 = "(2023-08-01)小红: 是啊，阳光明媚，心情也很好！"
        memory.insert(text_2)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  记忆 {i}: {entry['text']}")
        print()

        # 第3次插入
        print("=" * 70)
        print("第3次插入 - 格式化对话文本")
        print("=" * 70)
        text_3 = "(2023-08-02)小明: 要不要一起去公园散步？"
        memory.insert(text_3)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog} (已达到最大容量)")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  记忆 {i}: {entry['text']}")
        print()

        # 第4次插入 - 触发窗口滑动
        print("=" * 70)
        print("第4次插入 - 触发窗口滑动")
        print("=" * 70)
        text_4 = "(2023-08-02)小红: 好啊，我们去湖边走走吧！"
        memory.insert(text_4)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("⚠️  最旧的1个对话被移除，保留最新的3个对话")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            print(f"  记忆 {i}: {entry['text']}")
        print()

        # 第5次插入 - 继续滑动
        print("=" * 70)
        print("第5次插入 - 继续窗口滑动")
        print("=" * 70)
        text_5 = "小明: 太好了，我正想记录这美好的一天！"  # 无日期格式
        memory.insert(text_5, metadata={"source": "dialog"})

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_dialog}")
        print("⚠️  又有1个旧对话被移除，保留最新的3个对话")
        print("当前记忆内容:")
        for i, entry in enumerate(retrieved, 1):
            metadata_info = f" [metadata: {entry.get('metadata')}]" if entry.get("metadata") else ""
            print(f"  记忆 {i}: {entry['text']}{metadata_info}")

        print("\n" + "=" * 70)
        print("✅ 测试完成！")
        print(
            "新接口统一格式: insert(text, vector, metadata) / retrieve() -> [{'text': '...', 'metadata': {...}}, ...]"
        )
        print("=" * 70 + "\n")

    CustomLogger.disable_global_console_debug()
    test_short_term_memory()
