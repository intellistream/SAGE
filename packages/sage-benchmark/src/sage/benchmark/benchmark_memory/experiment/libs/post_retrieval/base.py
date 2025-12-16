"""PostRetrieval Action 基类和数据模型

定义 PostRetrieval 所有 Action 的统一接口和数据流。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional


@dataclass
class MemoryItem:
    """标准化记忆条目

    封装 memory_service 返回的单条结果，统一各 Action 的数据处理。
    """

    text: str
    score: Optional[float]
    metadata: dict[str, Any]
    original_index: int

    def get_timestamp(self, field: str = "timestamp") -> Optional[datetime]:
        """解析时间戳字段

        Args:
            field: 时间戳字段名，默认 "timestamp"

        Returns:
            datetime 对象，如果解析失败返回 None
        """
        value = self.metadata.get(field)
        if value is None:
            return None

        # 已经是 datetime
        if isinstance(value, datetime):
            return value

        # 常见字符串格式
        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(value, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    return dt
                except Exception:  # noqa: BLE001
                    continue

        # 时间戳（秒）
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=UTC)
            except Exception:  # noqa: BLE001
                return None

        return None


@dataclass
class PostRetrievalInput:
    """PostRetrieval 统一输入

    Attributes:
        data: 包含 memory_data 和 question 的原始数据
        config: Action 配置字典
        service_name: 记忆服务名称（用于多次查询）
    """

    data: dict[str, Any]
    config: dict[str, Any]
    service_name: str


@dataclass
class PostRetrievalOutput:
    """PostRetrieval 统一输出

    Attributes:
        memory_items: 处理后的记忆条目列表
        metadata: 额外元数据（如 rerank_method, filter_count 等）
    """

    memory_items: list[MemoryItem]
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePostRetrievalAction(ABC):
    """PostRetrieval Action 基类

    所有 PostRetrieval Action 必须继承此类并实现 execute 方法。

    职责边界：
    - 对检索结果进行后处理（rerank, filter, merge, augment 等）
    - 可以多次调用记忆服务进行查询拼接
    - 不负责生成 embedding（由服务完成）
    - 不从 data 读取多个记忆源（只与单一服务交互）
    """

    def __init__(self, config: dict[str, Any]):
        """初始化 Action

        Args:
            config: Action 配置字典
        """
        self.config = config
        self._init_action()

    @abstractmethod
    def _init_action(self) -> None:
        """初始化 Action 特定配置和工具

        子类在此方法中初始化所需的工具（如 LLM、Embedding、Tokenizer 等）。
        """
        pass

    @abstractmethod
    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """执行 Action 逻辑

        Args:
            input_data: 输入数据
            service: 记忆服务实例（用于多次查询）
            llm: LLM 实例（用于语义处理）
            embedding: Embedding 实例（用于向量计算）

        Returns:
            PostRetrievalOutput: 处理后的输出

        Raises:
            ValueError: 当输入数据不合法时
        """
        pass

    def _convert_to_items(self, memory_data: list[dict[str, Any]]) -> list[MemoryItem]:
        """将原始记忆数据转换为 MemoryItem 列表

        Args:
            memory_data: 原始记忆数据列表

        Returns:
            MemoryItem 列表
        """
        items = []
        for idx, item in enumerate(memory_data):
            items.append(
                MemoryItem(
                    text=item.get("text", ""),
                    score=item.get("score"),
                    metadata=item.get("metadata", {}),
                    original_index=idx,
                )
            )
        return items

    def _items_to_dicts(self, items: list[MemoryItem]) -> list[dict[str, Any]]:
        """将 MemoryItem 列表转换回字典格式

        Args:
            items: MemoryItem 列表

        Returns:
            字典格式的记忆数据列表
        """
        return [
            {"text": item.text, "score": item.score, "metadata": item.metadata} for item in items
        ]
