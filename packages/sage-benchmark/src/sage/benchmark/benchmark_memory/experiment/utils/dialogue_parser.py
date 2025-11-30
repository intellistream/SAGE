"""对话解析器 - 将对话列表格式化为字符串

可被多个模块复用，如 PreInsert、检索模块等。
"""

from __future__ import annotations


class DialogueParser:
    """对话解析器

    功能：
    - 将对话列表格式化为可读的字符串

    使用示例：
        parser = DialogueParser()
        dialogue_str = parser.format(dialogs)
    """

    def format(self, dialogs: list[dict]) -> str:
        """格式化对话列表为字符串

        Args:
            dialogs: 对话列表，包含 1 或 2 个字典，格式为：
                [
                    {"speaker": "xxx", "text": "xxx", "date_time": "xxx"},  # date_time 可选
                    {"speaker": "xxx", "text": "xxx"}  # 可能只有 1 条
                ]

        Returns:
            格式化后的对话字符串，每行格式为：
            - "(date_time)speaker: text" （有 date_time 时）
            - "speaker: text" （无 date_time 时）

        Examples:
            >>> dialogs = [
            ...     {"speaker": "Alice", "text": "Hello", "date_time": "2023-01-01 10:00"},
            ...     {"speaker": "Bob", "text": "Hi there"}
            ... ]
            >>> parser = DialogueParser()
            >>> parser.format(dialogs)
            '(2023-01-01 10:00)Alice: Hello\\nBob: Hi there'
        """
        if not dialogs:
            return ""

        lines = []
        for dialog in dialogs:
            line = self._format_single(dialog)
            if line:
                lines.append(line)

        return "\n".join(lines)

    def _format_single(self, dialog: dict) -> str:
        """格式化单条对话

        Args:
            dialog: 单条对话字典，包含 speaker、text，可选 date_time

        Returns:
            格式化后的单行字符串
        """
        speaker = dialog.get("speaker", "Unknown")
        text = dialog.get("text", "")
        date_time = dialog.get("date_time")

        if date_time:
            return f"({date_time}){speaker}: {text}"
        else:
            return f"{speaker}: {text}"

    def format_batch(self, dialogs_list: list[list[dict]]) -> list[str]:
        """批量格式化多组对话

        Args:
            dialogs_list: 多组对话列表

        Returns:
            格式化后的字符串列表
        """
        return [self.format(dialogs) for dialogs in dialogs_list]
