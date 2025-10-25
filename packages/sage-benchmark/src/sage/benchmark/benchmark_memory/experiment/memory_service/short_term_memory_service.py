from collections import deque
from typing import Any, Dict, List, Optional

from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import \
    DialogueParser
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.platform.service import BaseService


class ShortTermMemoryService(BaseService):
    def __init__(
        self,
        max_dialogue: Optional[int] = None,
        max_messages: Optional[int] = None,
        **kwargs,
    ):
        super().__init__()

        self._logger = CustomLogger()

        # 参数验证逻辑
        if max_dialogue is not None:
            if max_messages is not None:
                # 如果两个都提供，max_messages 必须是 max_dialogue 的两倍
                if max_messages != max_dialogue * 2:
                    raise ValueError(
                        f"When both max_dialogue and max_messages are provided, "
                        f"max_messages must be exactly twice max_dialogue. "
                        f"Got max_dialogue={max_dialogue}, max_messages={max_messages}"
                    )
                self.max_messages = max_messages
            else:
                # 只提供 max_dialogue，自动设置 max_messages
                self.max_messages = max_dialogue * 2
        elif max_messages is not None:
            # 只提供 max_messages
            self.max_messages = max_messages
        else:
            # 都没提供，抛出错误
            raise ValueError("Either max_dialogue or max_messages must be provided")

        # 使用 deque 作为队列，设置最大长度
        self.message_queue = deque(maxlen=self.max_messages)

        # 初始化对话解析器
        self.dialogue_parser = DialogueParser()

        self._logger.info(
            f"ShortTermMemoryService initialized with max_messages={self.max_messages}"
        )

    def insert(self, dialogs: List[Dict[str, Any]]) -> None:
        """
        插入对话历史到短期记忆中

        Args:
            dialogs: 对话列表，每个对话包含 speaker, text, session_type 等字段

        Raises:
            TypeError: 当输入不是列表或对话不是字典时
            ValueError: 当对话缺少必需字段时
        """
        # 使用对话解析器进行验证（严格模式）
        try:
            validated_dialogs = self.dialogue_parser.parse_and_validate(dialogs, strict_mode=True)
        except (TypeError, ValueError) as e:
            self._logger.error(f"Dialog validation failed: {e}")
            raise

        # 插入验证通过的对话
        for dialog in validated_dialogs:
            # 插入到队列，如果超出最大长度，最旧的会自动被移除
            self.message_queue.append(dialog)

            # 使用解析器提取信息用于日志
            info = self.dialogue_parser.extract_dialog_info(dialog)
            self._logger.debug(f"Inserted message from {info['speaker']}: {info['text_preview']}")

        self._logger.info(
            f"Successfully inserted {len(validated_dialogs)} dialog(s). "
            f"Current queue size: {len(self.message_queue)}/{self.max_messages}"
        )

    def retrieve(self) -> List[Dict[str, Any]]:
        """
        检索所有短期记忆中的对话

        Returns:
            List[Dict[str, Any]]: 对话列表
        """
        result = list(self.message_queue)
        self._logger.info(f"Retrieved {len(result)} messages from short-term memory")
        return result


if __name__ == "__main__":

    def test_short_term_memory():
        print("\n" + "=" * 70)
        print("短期记忆服务测试 - 演示插入和窗口滑动")
        print("=" * 70 + "\n")

        # 创建一个最多保存4条消息的短期记忆服务
        print("📝 初始化短期记忆服务 (最大消息数: 4)")
        memory = ShortTermMemoryService(max_messages=4)
        print(f"   当前队列大小: {len(memory.retrieve())}/{memory.max_messages}\n")

        # 第一次插入
        print("=" * 70)
        print("第1次插入 - 插入2条消息")
        print("=" * 70)
        dialogs_1 = [
            {
                "speaker": "小明",
                "text": "你好，今天天气真不错！",
                "session_type": "text",
            },
            {
                "speaker": "小红",
                "text": "是啊，阳光明媚，心情也很好！",
                "session_type": "text",
            },
        ]
        memory.insert(dialogs_1)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_messages}")
        print("当前记忆内容:")
        for i, msg in enumerate(retrieved, 1):
            print(f"  {i}. [{msg['speaker']}]: {msg['text']}")
        print()

        # 第二次插入
        print("=" * 70)
        print("第2次插入 - 再插入2条消息")
        print("=" * 70)
        dialogs_2 = [
            {
                "speaker": "小明",
                "text": "要不要一起去公园散步？",
                "session_type": "text",
            },
            {
                "speaker": "小红",
                "text": "好啊，我们去湖边走走吧！",
                "session_type": "text",
            },
        ]
        memory.insert(dialogs_2)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_messages} (已达到最大容量)")
        print("当前记忆内容:")
        for i, msg in enumerate(retrieved, 1):
            print(f"  {i}. [{msg['speaker']}]: {msg['text']}")
        print()

        # 第三次插入 - 触发窗口滑动
        print("=" * 70)
        print("第3次插入 - 插入1条新消息 (触发窗口滑动)")
        print("=" * 70)
        dialogs_3 = [{"speaker": "小明", "text": "那里的风景一定很美！", "session_type": "text"}]
        memory.insert(dialogs_3)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_messages}")
        print("⚠️  最旧的1条消息被移除，保留最新的4条")
        print("当前记忆内容:")
        for i, msg in enumerate(retrieved, 1):
            print(f"  {i}. [{msg['speaker']}]: {msg['text']}")
        print()

        # 第四次插入 - 继续滑动
        print("=" * 70)
        print("第4次插入 - 再插入2条消息 (继续窗口滑动)")
        print("=" * 70)
        dialogs_4 = [
            {"speaker": "小红", "text": "我们可以带相机拍照！", "session_type": "text"},
            {
                "speaker": "小明",
                "text": "太好了，我正想记录这美好的一天！",
                "session_type": "text",
            },
        ]
        memory.insert(dialogs_4)

        retrieved = memory.retrieve()
        print(f"当前队列大小: {len(retrieved)}/{memory.max_messages}")
        print("⚠️  又有2条旧消息被移除，保留最新的4条")
        print("当前记忆内容:")
        for i, msg in enumerate(retrieved, 1):
            print(f"  {i}. [{msg['speaker']}]: {msg['text']}")

        print("\n" + "=" * 70)
        print("✅ 测试完成！短期记忆服务采用队列方式管理，自动丢弃最旧的消息。")
        print("=" * 70 + "\n")

    CustomLogger.disable_global_console_debug()
    test_short_term_memory()
