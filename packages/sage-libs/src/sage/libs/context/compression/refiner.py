"""
Refiner基础接口定义
==================

定义统一的Refiner接口，所有压缩算法都需要实现此接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RefinerMetrics:
    """Refiner性能指标"""

    # 时间指标
    refine_time: float = 0.0  # 精炼耗时（秒）
    total_time: float = 0.0  # 总耗时（秒）

    # Token指标
    original_tokens: int = 0  # 原始token数
    refined_tokens: int = 0  # 精炼后token数
    compression_rate: float = 0.0  # 压缩率

    # 质量指标
    relevance_score: float = 0.0  # 相关性得分
    coherence_score: float = 0.0  # 连贯性得分

    # 其他元数据
    algorithm: str = ""  # 使用的算法
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "refine_time": self.refine_time,
            "total_time": self.total_time,
            "original_tokens": self.original_tokens,
            "refined_tokens": self.refined_tokens,
            "compression_rate": self.compression_rate,
            "relevance_score": self.relevance_score,
            "coherence_score": self.coherence_score,
            "algorithm": self.algorithm,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class RefineResult:
    """Refiner精炼结果"""

    refined_content: str | list[str]  # 精炼后的内容
    metrics: RefinerMetrics  # 性能指标
    # Allow original content to preserve the input format (str/dict)
    original_content: str | list[str] | list[str | dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "refined_content": self.refined_content,
            "metrics": self.metrics.to_dict(),
            "original_content": self.original_content,
        }


class BaseRefiner(ABC):
    """
    Refiner基础接口

    所有压缩算法都需要继承此类并实现核心方法。
    这个接口设计遵循SAGE的BaseFunction模式，可以无缝集成。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化Refiner

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    def initialize(self) -> None:
        """
        初始化算法（加载模型、准备资源等）

        这个方法在首次使用前调用，用于延迟加载重量级资源。
        """
        pass

    @abstractmethod
    def refine(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        **kwargs,
    ) -> RefineResult:
        """
        精炼文档内容

        Args:
            query: 用户查询
            documents: 文档列表，可以是字符串或包含'contents'/'text'的字典
            budget: token预算（可选，覆盖配置中的budget）
            **kwargs: 其他参数

        Returns:
            RefineResult: 精炼结果，包含压缩后的内容和性能指标
        """
        pass

    @abstractmethod
    def refine_batch(
        self,
        queries: list[str],
        documents_list: list[list[str | dict[str, Any]]],
        budget: int | None = None,
        **kwargs,
    ) -> list[RefineResult]:
        """
        批量精炼文档内容

        Args:
            queries: 查询列表
            documents_list: 文档列表的列表
            budget: token预算
            **kwargs: 其他参数

        Returns:
            List[RefineResult]: 精炼结果列表
        """
        pass

    def refine_streaming(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        **kwargs,
    ):
        """
        流式精炼（可选实现）

        Args:
            query: 用户查询
            documents: 文档列表
            budget: token预算
            **kwargs: 其他参数

        Yields:
            精炼后的内容片段
        """
        # 默认实现：一次性返回完整结果
        result = self.refine(query, documents, budget, **kwargs)
        yield result.refined_content

    def shutdown(self) -> None:
        """
        关闭并释放资源

        清理模型、释放GPU内存等。
        """
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    @property
    def name(self) -> str:
        """算法名称"""
        return self.__class__.__name__

    def get_info(self) -> dict[str, Any]:
        """获取算法信息"""
        return {
            "name": self.name,
            "initialized": self.is_initialized,
            "config": self.config,
        }
