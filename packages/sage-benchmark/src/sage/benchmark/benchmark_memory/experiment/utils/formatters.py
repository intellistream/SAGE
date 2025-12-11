"""格式化工具函数

提供简单的数据格式化功能：
- format_dialogue(): 格式化对话列表为字符串
- build_prompt(): 构建 Prompt
"""

from __future__ import annotations

from typing import Any


def format_dialogue(dialogs: list[dict]) -> str:
    """格式化对话列表为字符串

    Args:
        dialogs: 对话列表，每个元素是包含 speaker、text 的字典，
                 可选 date_time 字段

    Returns:
        格式化后的对话字符串，每行格式为：
        - "(date_time)speaker: text" （有 date_time 时）
        - "speaker: text" （无 date_time 时）

    Examples:
        >>> dialogs = [
        ...     {"speaker": "Alice", "text": "Hello", "date_time": "2023-01-01 10:00"},
        ...     {"speaker": "Bob", "text": "Hi there"}
        ... ]
        >>> format_dialogue(dialogs)
        '(2023-01-01 10:00)Alice: Hello\\nBob: Hi there'
    """
    if not dialogs:
        return ""

    lines = []
    for dialog in dialogs:
        speaker = dialog.get("speaker", "Unknown")
        text = dialog.get("text", "")
        date_time = dialog.get("date_time")

        if date_time:
            lines.append(f"({date_time}){speaker}: {text}")
        else:
            lines.append(f"{speaker}: {text}")

    return "\n".join(lines)


def format_dialogue_batch(dialogs_list: list[list[dict]]) -> list[str]:
    """批量格式化多组对话

    Args:
        dialogs_list: 多组对话列表

    Returns:
        格式化后的字符串列表
    """
    return [format_dialogue(dialogs) for dialogs in dialogs_list]


def build_prompt(template: str, **kwargs: Any) -> str:
    """根据模板和参数构建 Prompt

    Args:
        template: Prompt 模板字符串，使用 {key} 作为占位符
        **kwargs: 要填充到模板中的键值对

    Returns:
        构建好的 Prompt 字符串

    Examples:
        >>> template = "问题: {question}\\n历史: {history}\\n请回答:"
        >>> prompt = build_prompt(template, question="你好", history="用户: 早上好")
        >>> print(prompt)
        问题: 你好
        历史: 用户: 早上好
        请回答:
    """
    return template.format(**kwargs)


# =============================================================================
# 向后兼容：DialogueParser 类（已废弃，建议使用 format_dialogue 函数）
# =============================================================================


class DialogueParser:
    """对话解析器（已废弃）

    .. deprecated::
        请使用 format_dialogue() 函数替代。
        此类仅为向后兼容保留。

    Examples:
        # 旧用法（已废弃）
        parser = DialogueParser()
        text = parser.format(dialogs)

        # 新用法（推荐）
        from sage.benchmark.benchmark_memory.experiment.utils import format_dialogue
        text = format_dialogue(dialogs)
    """

    def format(self, dialogs: list[dict]) -> str:
        """格式化对话列表为字符串"""
        return format_dialogue(dialogs)

    def format_batch(self, dialogs_list: list[list[dict]]) -> list[str]:
        """批量格式化多组对话"""
        return format_dialogue_batch(dialogs_list)
