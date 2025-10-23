"""
对话解析工具模块
==============

该模块提供对话消息的验证和解析功能，用于各种 MemoryService 的消息处理。
所有 MemoryService 都应该使用这个解析器来统一处理对话消息的验证和解析。

导入方式：
---------
from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import DialogueParser

使用示例：
---------
# 1. 在 MemoryService 中使用
class YourMemoryService(BaseService):
    def __init__(self, ...):
        super().__init__()
        self.dialogue_parser = DialogueParser()

    def insert(self, dialogs):
        # 验证对话格式
        validated_dialogs = self.dialogue_parser.parse_and_validate(dialogs, strict_mode=True)
        for dialog in validated_dialogs:
            # 处理对话...
            info = self.dialogue_parser.extract_dialog_info(dialog)
            self._logger.debug(f"Processing: {info['text_preview']}")

# 2. 使用全局便捷函数（无需实例化）
from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import parse_and_validate_dialogs
validated = parse_and_validate_dialogs(dialogs)

当前支持的消息格式：
-----------------
标准对话格式（必需字段：speaker, text, session_type）：
{
    "speaker": str,       # 说话者名称
    "text": str,          # 对话内容
    "session_type": str   # 会话类型（如 "text"）
}

自定义必需字段：
validated = parser.parse_and_validate(dialogs, required_fields=["speaker", "text", "custom_field"])

未来扩展方向（留给未来的自己）：
============================
如果需要支持新的消息格式，在下面预留的接口位置添加实现：

1. 多模态消息支持（图片、语音、视频等）
   - 添加字段如：{"type": "image", "url": "...", "caption": "..."}
   - 实现 parse_multimodal_message() 方法

2. 群组对话支持（多人对话场景）
   - 添加字段如：{"group_id": "...", "participants": [...]}
   - 实现 parse_group_dialogue() 方法

3. 元数据丰富的消息（时间戳、情感标签等）
   - 添加字段如：{"timestamp": ..., "emotion": "...", "context": {...}}
   - 实现 parse_enriched_message() 方法

4. 自定义格式注册机制
   - 允许外部注册自己的验证器
   - 实现 register_custom_format() 方法

注意事项：
---------
- 严格模式（strict_mode=True）：遇到错误抛出异常，适合插入操作
- 非严格模式（strict_mode=False）：跳过无效对话，适合批量处理
- 线程安全：解析器是无状态的，可以在多线程环境中共享使用
"""

from typing import Any, Dict, List, Optional


class DialogueParser:
    """
    对话解析器 - 用于各种 MemoryService 的通用对话验证和解析工具

    功能：
    1. 验证对话格式是否符合要求
    2. 批量解析和验证对话列表
    3. 提取对话关键信息（用于日志、预览等）

    使用场景：
    - ShortTermMemoryService：验证插入的对话消息
    - LongTermMemoryService：验证长期存储的对话
    - 其他需要处理对话消息的 MemoryService

    典型用法：
        parser = DialogueParser()
        validated = parser.parse_and_validate(dialogs, strict_mode=True)
        info = parser.extract_dialog_info(dialog)
    """

    # 当前支持的标准对话格式必需字段
    # 如果未来需要支持其他格式，可以在 parse_and_validate() 中通过 required_fields 参数指定
    STANDARD_REQUIRED_FIELDS = ["speaker", "text", "session_type"]

    def __init__(self):
        """初始化对话解析器"""
        pass

    def validate_dialog_format(
        self,
        dialog: Dict[str, Any],
        required_fields: Optional[List[str]] = None
    ) -> bool:
        """
        验证单个对话是否符合格式要求

        Args:
            dialog: 待验证的对话字典
            required_fields: 必需字段列表，默认使用标准格式字段

        Returns:
            bool: 是否符合格式要求
        """
        if not isinstance(dialog, dict):
            return False

        if required_fields is None:
            required_fields = self.STANDARD_REQUIRED_FIELDS

        # 检查所有必需字段是否存在
        for field in required_fields:
            if field not in dialog:
                return False

        return True

    def parse_and_validate(
        self,
        dialogs: List[Dict[str, Any]],
        required_fields: Optional[List[str]] = None,
        strict_mode: bool = True
    ) -> List[Dict[str, Any]]:
        """
        解析并验证对话列表（核心方法）

        这是最常用的方法，建议所有 MemoryService 在接收对话时都先调用此方法进行验证。

        Args:
            dialogs: 对话列表，每个元素应该是包含对话信息的字典
            required_fields: 必需字段列表，None 时使用默认的标准字段 ["speaker", "text", "session_type"]
                           如果需要自定义验证，可以传入自己的字段列表，例如：
                           ["speaker", "text", "timestamp"] 用于带时间戳的对话
            strict_mode: 严格模式开关
                        True（推荐用于插入操作）：遇到格式错误立即抛出异常，确保数据完整性
                        False（推荐用于批量处理）：跳过无效对话，只返回有效的对话列表

        Returns:
            List[Dict[str, Any]]: 验证通过的对话列表

        Raises:
            TypeError: 当输入不是列表或对话不是字典时（仅在 strict_mode=True 时）
            ValueError: 当对话缺少必需字段时（仅在 strict_mode=True 时）

        使用建议：
            # 在 insert 操作中使用严格模式
            validated = self.dialogue_parser.parse_and_validate(dialogs, strict_mode=True)

            # 在批量导入或容错场景中使用非严格模式
            validated = self.dialogue_parser.parse_and_validate(dialogs, strict_mode=False)
        """
        if not isinstance(dialogs, list):
            if strict_mode:
                raise TypeError(f"dialogs must be a list, got {type(dialogs)}")
            else:
                return []

        if required_fields is None:
            required_fields = self.STANDARD_REQUIRED_FIELDS

        validated_dialogs = []

        for idx, dialog in enumerate(dialogs):
            if not isinstance(dialog, dict):
                if strict_mode:
                    raise TypeError(
                        f"Dialog at index {idx} must be a dictionary, got {type(dialog)}"
                    )
                else:
                    continue

            # 验证必需字段
            missing_fields = [
                field for field in required_fields if field not in dialog
            ]

            if missing_fields:
                if strict_mode:
                    raise ValueError(
                        f"Dialog at index {idx} missing required fields: {missing_fields}"
                    )
                else:
                    continue

            validated_dialogs.append(dialog)

        return validated_dialogs

    def extract_dialog_info(self, dialog: Dict[str, Any]) -> Dict[str, Any]:
        """
        从对话中提取关键信息（辅助方法）

        用于日志记录、预览显示等场景，避免直接访问字典键。
        自动处理文本过长的情况，生成预览文本。

        Args:
            dialog: 对话字典

        Returns:
            Dict[str, Any]: 包含提取信息的字典，包含以下字段：
                - speaker: 说话者名称（默认 "Unknown"）
                - text: 完整对话文本（默认 ""）
                - session_type: 会话类型（默认 "text"）
                - text_preview: 文本预览（超过50字符会截断并添加 "..."）

        使用示例：
            info = self.dialogue_parser.extract_dialog_info(dialog)
            self._logger.debug(f"Processing message from {info['speaker']}: {info['text_preview']}")
        """
        info = {
            "speaker": dialog.get("speaker", "Unknown"),
            "text": dialog.get("text", ""),
            "session_type": dialog.get("session_type", "text"),
            "text_preview": dialog.get("text", "")[:50] + "..."
                           if len(dialog.get("text", "")) > 50 else dialog.get("text", "")
        }
        return info

    # ==================== 未来扩展预留接口（留给未来的自己） ====================
    #
    # 如果需要支持新的消息格式，请在下面添加对应的方法实现。
    # 建议保持接口设计的一致性，参考现有方法的参数和返回值格式。
    #
    # TODO 1: 多模态消息解析支持
    # Issue URL: https://github.com/intellistream/SAGE/issues/976
    # 使用场景：需要处理包含图片、语音、视频等多媒体内容的消息
    # 参考格式：
    # {
    #     "speaker": "用户",
    #     "content_type": "image",  # 或 "audio", "video"
    #     "url": "https://...",
    #     "caption": "这是一张图片",
    #     "metadata": {"size": 1024, "format": "png"}
    # }
    # def parse_multimodal_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
    #     """解析包含图片、语音、视频等多模态内容的消息"""
    #     pass

    # TODO 2: 群组对话解析支持
    # Issue URL: https://github.com/intellistream/SAGE/issues/975
    # 使用场景：处理多人对话、会议记录等群组对话场景
    # 参考格式：
    # {
    #     "group_id": "group_123",
    #     "participants": ["用户1", "用户2", "用户3"],
    #     "messages": [
    #         {"speaker": "用户1", "text": "...", "timestamp": ...},
    #         {"speaker": "用户2", "text": "...", "timestamp": ...}
    #     ]
    # }
    # def parse_group_dialogue(self, dialogue: Dict[str, Any]) -> Dict[str, Any]:
    #     """解析群组对话，处理多人对话场景"""
    #     pass

    # TODO 3: 带元数据的消息解析
    # Issue URL: https://github.com/intellistream/SAGE/issues/974
    # 使用场景：需要额外的上下文信息，如时间戳、情感标签、地理位置等
    # 参考格式：
    # {
    #     "speaker": "用户",
    #     "text": "今天心情不错",
    #     "timestamp": 1697520000,
    #     "emotion": "happy",
    #     "location": {"lat": 39.9, "lng": 116.4},
    #     "context": {"topic": "心情", "previous_topic": "天气"}
    # }
    # def parse_enriched_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
    #     """解析包含时间戳、情感标签、上下文等元数据的消息"""
    #     pass

    # TODO 4: 自定义格式注册机制
    # Issue URL: https://github.com/intellistream/SAGE/issues/973
    # 使用场景：允许外部模块注册自己的消息格式验证器，增强可扩展性
    # 用法示例：
    # def my_validator(dialog: Dict[str, Any]) -> bool:
    #     return "my_field" in dialog and isinstance(dialog["my_field"], str)
    # parser.register_custom_format("my_format", my_validator)
    # def register_custom_format(self, format_name: str, validator: Callable[[Dict[str, Any]], bool]) -> None:
    #     """注册自定义消息格式的验证器"""
    #     pass


# ==================== 全局便捷函数 ====================
# 提供一个全局单例供快速使用，无需每次都实例化 DialogueParser
# 适合不需要维护状态的快速验证场景
_global_parser = DialogueParser()


def parse_and_validate_dialogs(
    dialogs: List[Dict[str, Any]],
    required_fields: Optional[List[str]] = None,
    strict_mode: bool = True
) -> List[Dict[str, Any]]:
    """
    全局便捷函数：解析并验证对话列表

    无需实例化 DialogueParser，直接调用此函数即可快速验证对话。
    适合临时验证、测试脚本等场景。

    Args:
        dialogs: 对话列表
        required_fields: 必需字段列表，默认使用标准格式字段
        strict_mode: 严格模式

    Returns:
        List[Dict[str, Any]]: 验证通过的对话列表

    使用示例：
        from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import parse_and_validate_dialogs
        validated = parse_and_validate_dialogs(dialogs)
    """
    return _global_parser.parse_and_validate(dialogs, required_fields, strict_mode)


def validate_dialog(
    dialog: Dict[str, Any],
    required_fields: Optional[List[str]] = None
) -> bool:
    """
    全局便捷函数：验证单个对话格式

    无需实例化 DialogueParser，直接调用此函数即可快速验证单个对话。
    返回布尔值，不抛出异常，适合需要判断对话是否有效的场景。

    Args:
        dialog: 待验证的对话字典
        required_fields: 必需字段列表，默认使用标准格式字段

    Returns:
        bool: 是否符合格式要求

    使用示例：
        from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import validate_dialog
        if validate_dialog(dialog):
            # 对话格式正确
            process(dialog)
    """
    return _global_parser.validate_dialog_format(dialog, required_fields)


if __name__ == "__main__":

    def test_dialogue_parser():
        print("\n" + "=" * 70)
        print("对话解析器测试")
        print("=" * 70 + "\n")

        parser = DialogueParser()

        # 测试1: 标准格式对话
        print("测试1: 验证标准格式对话")
        print("-" * 70)
        valid_dialogs = [
            {
                "speaker": "小明",
                "text": "你好，今天天气真不错！",
                "session_type": "text"
            },
            {
                "speaker": "小红",
                "text": "是啊，阳光明媚！",
                "session_type": "text"
            }
        ]

        result = parser.parse_and_validate(valid_dialogs)
        print(f"✓ 输入 {len(valid_dialogs)} 条对话，验证通过 {len(result)} 条\n")

        # 测试2: 缺少必需字段
        print("测试2: 处理缺少必需字段的对话（严格模式）")
        print("-" * 70)
        invalid_dialogs = [
            {
                "speaker": "小明",
                "text": "这条消息缺少 session_type"
            }
        ]

        try:
            parser.parse_and_validate(invalid_dialogs, strict_mode=True)
            print("✗ 应该抛出异常")
        except ValueError as e:
            print(f"✓ 正确捕获异常: {e}\n")

        # 测试3: 非严格模式
        print("测试3: 非严格模式下跳过无效对话")
        print("-" * 70)
        mixed_dialogs = [
            {
                "speaker": "小明",
                "text": "这是有效消息",
                "session_type": "text"
            },
            {
                "speaker": "小红",
                "text": "这条缺少 session_type"  # 缺少字段
            },
            {
                "speaker": "小李",
                "text": "这也是有效消息",
                "session_type": "text"
            }
        ]

        result = parser.parse_and_validate(mixed_dialogs, strict_mode=False)
        print(f"输入 {len(mixed_dialogs)} 条对话（其中1条无效）")
        print(f"✓ 非严格模式下验证通过 {len(result)} 条有效对话\n")

        # 测试4: 提取对话信息
        print("测试4: 提取对话关键信息")
        print("-" * 70)
        dialog = {
            "speaker": "小明",
            "text": "这是一条很长很长很长很长很长很长很长很长很长很长的消息，用于测试文本预览功能",
            "session_type": "text"
        }

        info = parser.extract_dialog_info(dialog)
        print(f"说话者: {info['speaker']}")
        print(f"消息类型: {info['session_type']}")
        print(f"文本预览: {info['text_preview']}")
        print(f"✓ 成功提取对话信息\n")

        # 测试5: 使用全局便捷函数
        print("测试5: 使用全局便捷函数")
        print("-" * 70)
        dialogs = [
            {"speaker": "用户", "text": "测试消息", "session_type": "text"}
        ]
        result = parse_and_validate_dialogs(dialogs)
        print(f"✓ 全局函数验证通过 {len(result)} 条对话")

        is_valid = validate_dialog(dialogs[0])
        print(f"✓ 单个对话验证结果: {is_valid}\n")

        print("=" * 70)
        print("✅ 所有测试通过！对话解析器工作正常。")
        print("=" * 70 + "\n")

    test_dialogue_parser()
