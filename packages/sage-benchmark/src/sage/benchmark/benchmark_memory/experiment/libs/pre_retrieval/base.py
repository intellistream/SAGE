"""PreRetrieval Action 基类和数据模型

定义了PreRetrieval阶段的统一接口和数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PreRetrievalInput:
    """PreRetrieval 统一输入数据模型

    Attributes:
        data: 包含用户查询的原始数据（必须包含 question 字段）
        config: Action 特定配置
    """

    data: dict[str, Any]
    config: dict[str, Any]

    @property
    def question(self) -> str:
        """获取查询文本"""
        return self.data.get("question", "")


@dataclass
class PreRetrievalOutput:
    """PreRetrieval 统一输出数据模型

    Attributes:
        query: 处理后的查询文本
        query_embedding: 查询向量（如果生成）
        metadata: 额外元数据（如关键词、扩展查询等）
        retrieve_mode: 检索模式（passive/active）
        retrieve_params: 检索参数（如过滤条件、权重等）
    """

    query: str
    query_embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retrieve_mode: str = "passive"
    retrieve_params: Optional[dict[str, Any]] = None


class BasePreRetrievalAction(ABC):
    """PreRetrieval Action 基类

    所有PreRetrieval Action必须继承此类并实现execute方法。

    标准化接口确保：
    1. 统一的初始化流程
    2. 统一的输入输出格式
    3. 易于测试和维护
    """

    def __init__(self, config: dict[str, Any]):
        """初始化Action

        Args:
            config: Action配置字典，包含Action特定的参数
        """
        self.config = config
        self._init_action()

    @abstractmethod
    def _init_action(self) -> None:
        """初始化Action特定的配置和工具

        子类必须实现此方法，用于：
        - 验证必需配置
        - 初始化工具（如NLP模型、LLM客户端）
        - 设置默认值
        """
        pass

    @abstractmethod
    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """执行Action逻辑

        Args:
            input_data: 标准化的输入数据

        Returns:
            标准化的输出数据

        Raises:
            ValueError: 输入数据无效
            RuntimeError: Action执行失败
        """
        pass

    def _get_config_value(
        self,
        key: str,
        default: Any = None,
        required: bool = False,
        context: str = "",
    ) -> Any:
        """安全获取配置值

        Args:
            key: 配置键名
            default: 默认值
            required: 是否必需
            context: 上下文描述（用于错误提示）

        Returns:
            配置值

        Raises:
            ValueError: required=True 且配置不存在
        """
        value = self.config.get(key, default)
        if required and value is None:
            ctx = f" ({context})" if context else ""
            raise ValueError(f"Missing required config: {key}{ctx}")
        return value
