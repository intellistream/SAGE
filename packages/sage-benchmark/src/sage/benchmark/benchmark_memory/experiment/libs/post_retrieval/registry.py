"""PostRetrieval Action 注册表

管理所有 PostRetrieval Action 的注册和获取。
"""

from .augment import AugmentAction
from .base import BasePostRetrievalAction
from .filter.threshold import ThresholdFilterAction
from .filter.token_budget import TokenBudgetFilterAction
from .filter.top_k import TopKFilterAction
from .merge.link_expand import LinkExpandMergeAction
from .merge.multi_query import MultiQueryMergeAction
from .none_action import NoneAction
from .rerank.ppr import PPRRerankAction
from .rerank.semantic import SemanticRerankAction
from .rerank.time_weighted import TimeWeightedRerankAction
from .rerank.weighted import WeightedRerankAction


class PostRetrievalActionRegistry:
    """PostRetrieval Action 注册表

    管理所有 PostRetrieval Action 的注册、查询和验证。

    支持的 Action:
    - none: 透传
    - rerank.semantic: 语义重排序
    - rerank.time_weighted: 时间加权重排序
    - rerank.ppr: PPR 重排序
    - rerank.weighted: 多因子加权重排序
    - filter.token_budget: Token 预算过滤
    - filter.threshold: 阈值过滤
    - filter.top_k: Top-K 过滤
    - merge.link_expand: 链接扩展合并
    - merge.multi_query: 多查询合并
    - augment: 结果增强
    """

    _actions: dict[str, type[BasePostRetrievalAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePostRetrievalAction]) -> None:
        """注册 Action

        Args:
            name: Action 名称（支持点分隔的层级命名，如 "rerank.semantic"）
            action_class: Action 类
        """
        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePostRetrievalAction]:
        """获取 Action 类

        Args:
            name: Action 名称

        Returns:
            Action 类

        Raises:
            ValueError: 如果 Action 不存在
        """
        if name not in cls._actions:
            raise ValueError(
                f"Unknown PostRetrieval action: {name}. "
                f"Available actions: {list(cls._actions.keys())}"
            )
        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """列出所有已注册的 Action

        Returns:
            Action 名称列表
        """
        return list(cls._actions.keys())

    @classmethod
    def has_action(cls, name: str) -> bool:
        """检查 Action 是否存在

        Args:
            name: Action 名称

        Returns:
            是否存在
        """
        return name in cls._actions


# 注册所有内置 Action
PostRetrievalActionRegistry.register("none", NoneAction)

# Rerank Actions
PostRetrievalActionRegistry.register("rerank.semantic", SemanticRerankAction)
PostRetrievalActionRegistry.register("rerank.time_weighted", TimeWeightedRerankAction)
PostRetrievalActionRegistry.register("rerank.ppr", PPRRerankAction)
PostRetrievalActionRegistry.register("rerank.weighted", WeightedRerankAction)

# Filter Actions
PostRetrievalActionRegistry.register("filter.token_budget", TokenBudgetFilterAction)
PostRetrievalActionRegistry.register("filter.threshold", ThresholdFilterAction)
PostRetrievalActionRegistry.register("filter.top_k", TopKFilterAction)

# Merge Actions
PostRetrievalActionRegistry.register("merge.link_expand", LinkExpandMergeAction)
PostRetrievalActionRegistry.register("merge.multi_query", MultiQueryMergeAction)

# Augment Action
PostRetrievalActionRegistry.register("augment", AugmentAction)
