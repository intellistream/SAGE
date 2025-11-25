"""数据解析器 - 负责解析和提取对话数据"""

from __future__ import annotations

from typing import Any


class DataParser:
    """数据解析器

    功能：
    1. 从数据字典中提取原始对话列表（支持配置化）
    2. 解析对话格式
    3. 提供数据验证

    使用示例：
        parser = DataParser(config)
        dialogs = parser.extract(data)
    """

    # 支持的提取方法映射
    EXTRACT_METHODS = {
        "to_dialogs": "_extract_to_dialogs",
        "to_refactor": "_extract_to_refactor",
        # 未来可以添加其他提取方法：
        # "to_messages": "_extract_to_messages",
        # "to_turns": "_extract_to_turns",
    }

    # 支持的格式化方法映射
    FORMAT_METHODS = {
        "none": "_format_none",
        "to_text": "_format_to_text",
        # 未来可以添加其他格式化方法：
        # "to_json": "_format_to_json",
        # "to_markdown": "_format_to_markdown",
    }

    def __init__(self, config=None):
        """初始化数据解析器

        Args:
            config: RuntimeConfig 对象，用于读取提取方法和格式化方法配置
        """
        self.config = config

        # 从配置读取提取方法
        adapter_name = (
            config.get("services.memory_insert_adapter", "to_dialogs") if config else "to_dialogs"
        )

        # 验证提取方法是否支持
        if adapter_name not in self.EXTRACT_METHODS:
            supported = ", ".join(self.EXTRACT_METHODS.keys())
            raise ValueError(f"不支持的提取方法: {adapter_name}。支持的方法: {supported}")

        # 获取对应的提取方法
        method_name = self.EXTRACT_METHODS[adapter_name]
        self.extract_method = getattr(self, method_name)

        # 从配置读取格式化方法
        formatter_name = (
            config.get("services.memory_retrieval_adapter", "to_text") if config else "to_text"
        )

        # 验证格式化方法是否支持
        if formatter_name not in self.FORMAT_METHODS:
            supported = ", ".join(self.FORMAT_METHODS.keys())
            raise ValueError(f"不支持的格式化方法: {formatter_name}。支持的方法: {supported}")

        # 获取对应的格式化方法
        format_method_name = self.FORMAT_METHODS[formatter_name]
        self.format_method = getattr(self, format_method_name)

    def extract(self, data: dict[str, Any] | None) -> str:
        """从数据中提取内容（入口方法）

        Args:
            data: 数据字典

        Returns:
            根据配置的 adapter 返回字符串：
            - to_dialogs: str - 格式化后的对话字符串（多条对话用换行合并）
            - to_refactor: str - 重构描述字符串
        """

        # 调用配置的提取方法
        return self.extract_method(data)

    def _extract_to_dialogs(self, data: dict[str, Any]) -> str:
        """提取方法：to_dialogs（默认方法）

        从 'dialogs' 或 'data.dialogs' 字段提取对话列表并格式化为字符串
        
        每个对话字典包含：{"speaker": str, "text": str, "date_time": str (可选)}
        格式化为：
        - 有 date_time: "({date_time}){speaker}: {text}"
        - 无 date_time: "{speaker}: {text}"
        - 多条对话用换行符分隔，合并为一个字符串

        Args:
            data: 数据字典，包含 "dialogs" 或 "data" 字段

        Returns:
            格式化后的对话字符串（多条对话用换行合并）
        """
        # 尝试从 'dialogs' 或 'data.dialogs' 获取对话列表
        dialogs = data.get("dialogs")
        if dialogs is None and "data" in data:
            dialogs = data["data"].get("dialogs")
        
        if not dialogs or not isinstance(dialogs, list):
            return ""
        
        # 格式化每个对话为字符串
        formatted_dialogs = []
        for dialog in dialogs:
            if not isinstance(dialog, dict):
                continue
            
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", "")
            date_time = dialog.get("date_time")
            
            # 根据是否有 date_time 决定格式
            if date_time:
                formatted = f"({date_time}){speaker}: {text}"
            else:
                formatted = f"{speaker}: {text}"
            
            formatted_dialogs.append(formatted)
        
        # 合并为单个字符串（用换行符分隔）
        return "\n".join(formatted_dialogs)

    def _extract_to_refactor(self, data: dict[str, Any]) -> str:
        """提取方法：to_refactor（用于三元组模式）

        从 'refactor' 字段提取重构描述

        Args:
            data: 数据字典，包含 'refactor' 字段

        Returns:
            重构描述字符串，如果不存在则返回空字符串
        """
        return data.get("refactor", "")

    def _format_none(self, memory_data: list[dict[str, Any]], query: Any = None) -> str:
        """格式化方法：none（不做任何处理，返回空字符串）

        Args:
            memory_data: 从记忆服务检索的数据
            query: 查询参数（不使用）

        Returns:
            空字符串
        """
        return ""

    def _format_to_text(self, memory_data: list[dict[str, Any]], query: Any = None) -> str:
        """格式化方法：to_text（转换为文本格式）

        Args:
            memory_data: 从记忆服务检索的数据，格式为 [{"dialog": [...]}]
            query: 查询参数（不使用）

        Returns:
            格式化的历史文本，每行为 "speaker: text"
        """
        history_lines = []
        for entry in memory_data:
            dialog = entry.get("dialog", [])
            for msg in dialog:
                speaker = msg.get("speaker", "Unknown")
                text = msg.get("text", "")
                history_lines.append(f"{speaker}: {text}")

        return "\n".join(history_lines)

    @staticmethod
    def get_raw_dialogs(data: dict[str, Any] | None) -> list[dict[str, str]]:
        """从数据中提取原始对话列表（静态方法，保持向后兼容）

        Args:
            data: 数据字典，可能包含 'dialogs' 或 'dialog' 字段

        Returns:
            对话列表，每个元素为 {"speaker": str, "text": str}
            如果数据为空或不包含对话，返回空列表

        Examples:
            >>> data = {"dialogs": [{"speaker": "user", "text": "hello"}]}
            >>> DataParser.get_raw_dialogs(data)
            [{"speaker": "user", "text": "hello"}]

        注意：推荐使用实例方法 extract()，因为它支持配置化提取
        """
        if not data:
            return []

        # 尝试从 'dialogs' 字段获取（多个对话）
        dialogs = data.get("dialogs")
        if dialogs is not None:
            if isinstance(dialogs, list):
                return dialogs
            # 如果 dialogs 不是列表，尝试包装为列表
            return [dialogs] if dialogs else []

        # 尝试从 'dialog' 字段获取（单个对话）
        dialog = data.get("dialog")
        if dialog is not None:
            if isinstance(dialog, list):
                return dialog
            # 如果 dialog 不是列表，尝试包装为列表
            return [dialog] if dialog else []

        # 都没有，返回空列表
        return []

    @staticmethod
    def validate_dialog(dialog: dict[str, str]) -> bool:
        """验证对话格式是否正确

        Args:
            dialog: 单条对话 {"speaker": str, "text": str}

        Returns:
            True 如果格式正确，False 否则
        """
        if not isinstance(dialog, dict):
            return False

        # 检查必需字段
        if "speaker" not in dialog or "text" not in dialog:
            return False

        # 检查字段类型
        if not isinstance(dialog["speaker"], str) or not isinstance(dialog["text"], str):
            return False

        return True

    @staticmethod
    def validate_dialogs(dialogs: list[dict[str, str]]) -> bool:
        """验证对话列表格式是否正确

        Args:
            dialogs: 对话列表

        Returns:
            True 如果所有对话格式正确，False 否则
        """
        if not isinstance(dialogs, list):
            return False

        if not dialogs:  # 空列表也是合法的
            return True

        return all(DataParser.validate_dialog(d) for d in dialogs)

    @staticmethod
    def format_history(memory_data: list[dict[str, Any]]) -> str:
        """将记忆数据格式化为历史文本（静态方法，保持向后兼容）

        Args:
            memory_data: 从记忆服务检索的数据，格式为 [{"dialog": [...]}]

        Returns:
            格式化的历史文本，每行为 "speaker: text"

        Examples:
            >>> memory_data = [{"dialog": [{"speaker": "user", "text": "hi"}]}]
            >>> DataParser.format_history(memory_data)
            "user: hi"

        注意：推荐使用实例方法 format()，因为它支持配置化格式化
        """
        if not memory_data:
            return ""

        history_lines = []
        for entry in memory_data:
            dialog = entry.get("dialog", [])
            for msg in dialog:
                speaker = msg.get("speaker", "Unknown")
                text = msg.get("text", "")
                history_lines.append(f"{speaker}: {text}")

        return "\n".join(history_lines)
