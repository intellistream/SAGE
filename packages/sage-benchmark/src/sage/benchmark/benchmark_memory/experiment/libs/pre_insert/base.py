"""PreInsert Action 基类和数据模型

定义了 PreInsert 阶段的统一接口和数据流规范。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PreInsertInput:
    """PreInsert 统一输入数据结构

    Attributes:
        data: 原始输入数据（包含 dialogs 等字段）
        config: Action 特定的配置参数
        service_name: 记忆服务名称（用于检索操作）
    """

    data: dict[str, Any]
    config: dict[str, Any]
    service_name: str


@dataclass
class PreInsertOutput:
    """PreInsert 统一输出数据结构

    Attributes:
        memory_entries: 处理后的记忆条目列表，每个条目包含：
            - text: 记忆文本
            - embedding: 向量表示（可选）
            - metadata: 元数据
            - insert_mode: 插入模式（passive/active）
            - insert_method: 插入方法（标识使用的策略）
            - insert_params: 插入参数（可选）
        metadata: 额外的元数据（可选）
    """

    memory_entries: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePreInsertAction(ABC):
    """PreInsert Action 基类

    所有 PreInsert Action 必须继承此类并实现 execute 方法。
    采用策略模式，每个 Action 封装一种特定的预处理策略。
    """

    def __init__(self, config: dict[str, Any]):
        """初始化 Action

        Args:
            config: Action 配置参数（从 operators.pre_insert 读取）
        """
        self.config = config
        self._init_action()

    @abstractmethod
    def _init_action(self) -> None:
        """初始化 Action 特定的工具和资源

        子类需要实现此方法来初始化：
        - NLP 工具（spacy, nltk 等）
        - LLM 客户端
        - 其他配置参数
        """
        pass

    @abstractmethod
    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行 Action 的核心逻辑

        Args:
            input_data: 预处理输入

        Returns:
            PreInsertOutput: 处理后的记忆条目
        """
        pass

    def _set_default_fields(self, entry: dict[str, Any]) -> dict[str, Any]:
        """为记忆条目设置默认字段

        Args:
            entry: 记忆条目

        Returns:
            补充了默认字段的记忆条目
        """
        entry.setdefault("insert_mode", "passive")
        entry.setdefault("insert_method", "default")
        entry.setdefault("metadata", {})
        return entry

    def _format_dialogue(self, dialogs: list[dict[str, str]]) -> str:
        """将对话列表格式化为文本

        Args:
            dialogs: 对话列表，每项包含 role/speaker 和 content/text

        Returns:
            格式化后的对话文本
        """
        if not dialogs:
            return ""

        lines = []
        for dialog in dialogs:
            # 兼容两种格式: role/speaker, content/text
            role = dialog.get("role") or dialog.get("speaker", "unknown")
            content = dialog.get("content") or dialog.get("text", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
