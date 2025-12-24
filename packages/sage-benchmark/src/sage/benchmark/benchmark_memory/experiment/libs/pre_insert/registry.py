"""PreInsert Action 注册表

管理所有 PreInsert Action 的注册和获取。
"""

from .base import BasePreInsertAction
from .extract import (
    EntityExtractAction,
    KeywordExtractAction,
    MultiSummaryAction,
    NounExtractAction,
    TripleExtractAction,
)
from .none_action import NoneAction
from .score import HeatScoreAction, ImportanceScoreAction
from .transform import ChunkingAction, SummarizeAction, TopicSegmentAction
from .transform.continuity_check import ContinuityCheckAction


class PreInsertActionRegistry:
    """PreInsert Action 注册表

    使用策略模式管理所有 Action，支持动态注册和获取。
    """

    _actions: dict[str, type[BasePreInsertAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePreInsertAction]) -> None:
        """注册一个 Action

        Args:
            name: Action 名称（支持点分隔的层级名，如 "transform.chunking"）
            action_class: Action 类
        """
        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePreInsertAction]:
        """获取 Action 类

        Args:
            name: Action 名称

        Returns:
            Action 类

        Raises:
            ValueError: 如果 Action 未注册
        """
        if name not in cls._actions:
            raise ValueError(
                f"Unknown PreInsert action: '{name}'. "
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
    def is_registered(cls, name: str) -> bool:
        """检查 Action 是否已注册

        Args:
            name: Action 名称

        Returns:
            是否已注册
        """
        return name in cls._actions


# 注册所有内置 Action
def _register_builtin_actions():
    """注册所有内置 Action"""
    # 透传类
    PreInsertActionRegistry.register("none", NoneAction)

    # Transform 类
    PreInsertActionRegistry.register("transform.chunking", ChunkingAction)
    PreInsertActionRegistry.register("transform.summarize", SummarizeAction)
    PreInsertActionRegistry.register("transform.segment", TopicSegmentAction)
    PreInsertActionRegistry.register("transform.continuity_check", ContinuityCheckAction)

    # Extract 类
    PreInsertActionRegistry.register("extract.keyword", KeywordExtractAction)
    PreInsertActionRegistry.register("extract.entity", EntityExtractAction)
    PreInsertActionRegistry.register("extract.noun", NounExtractAction)
    PreInsertActionRegistry.register("extract.triple", TripleExtractAction)
    PreInsertActionRegistry.register("extract.multi_summary", MultiSummaryAction)

    # Score 类
    PreInsertActionRegistry.register("score.importance", ImportanceScoreAction)
    PreInsertActionRegistry.register("score.heat", HeatScoreAction)

    # 向后兼容别名（已废弃，请使用 extract.triple）
    PreInsertActionRegistry.register("tri_embed", TripleExtractAction)


# 自动注册所有内置 Action
_register_builtin_actions()
