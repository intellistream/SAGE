"""PreRetrieval Action 注册表

管理所有PreRetrieval Action的注册和获取。

支持的Actions：
- none: 透传查询（Mem0, Mem0ᵍ）
- embedding: 查询向量化（TiM, MemoryBank, A-Mem, MemoryOS, HippoRAG2, SeCom）
- optimize.keyword_extract: 关键词提取（LD-Agent, HippoRAG）
- optimize.expand: 查询扩展（MemGPT）
- optimize.rewrite: 查询改写（MemGPT）
- validate: 查询验证（SCM）
"""

from .base import BasePreRetrievalAction
from .embedding import EmbeddingAction
from .none_action import NoneAction
from .optimize.expand import ExpandAction
from .optimize.keyword_extract import KeywordExtractAction
from .optimize.rewrite import RewriteAction
from .validate import ValidateAction


class PreRetrievalActionRegistry:
    """PreRetrieval Action 注册表

    提供Action的注册、获取和查询功能。
    """

    _actions: dict[str, type[BasePreRetrievalAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePreRetrievalAction]) -> None:
        """注册Action

        Args:
            name: Action名称（支持点号分隔的子类型，如 "optimize.keyword_extract"）
            action_class: Action类

        Raises:
            ValueError: Action名称已存在
        """
        if name in cls._actions:
            raise ValueError(f"Action '{name}' is already registered")
        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePreRetrievalAction]:
        """获取Action类

        Args:
            name: Action名称

        Returns:
            Action类

        Raises:
            ValueError: Action不存在
        """
        if name not in cls._actions:
            raise ValueError(
                f"Unknown action: {name}. Available actions: {', '.join(cls._actions.keys())}"
            )
        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """列出所有已注册的Action名称

        Returns:
            Action名称列表
        """
        return list(cls._actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查Action是否已注册

        Args:
            name: Action名称

        Returns:
            是否已注册
        """
        return name in cls._actions


# ==================== 注册所有Action ====================

# 基础Actions
PreRetrievalActionRegistry.register("none", NoneAction)
PreRetrievalActionRegistry.register("embedding", EmbeddingAction)
PreRetrievalActionRegistry.register("validate", ValidateAction)

# Optimize子类型Actions
PreRetrievalActionRegistry.register("optimize.keyword_extract", KeywordExtractAction)
PreRetrievalActionRegistry.register("optimize.expand", ExpandAction)
PreRetrievalActionRegistry.register("optimize.rewrite", RewriteAction)


# ==================== 12个记忆体使用情况说明 ====================
"""
记忆体使用映射：

1. TiM: embedding
   - vector_hash_memory，使用embedding进行相似度检索

2. MemoryBank: embedding
   - hierarchical_memory，使用embedding检索各层记忆

3. MemGPT: optimize.expand / optimize.rewrite
   - hierarchical_memory，通过查询优化提高检索准确性

4. A-Mem: embedding
   - graph_memory，使用embedding进行图检索

5. MemoryOS: embedding
   - hierarchical_memory，使用embedding检索层级记忆

6. HippoRAG: optimize.keyword_extract
   - graph_memory，提取实体作为查询

7. HippoRAG2: embedding
   - graph_memory，使用embedding进行图检索

8. LD-Agent: optimize.keyword_extract
   - hierarchical_memory，提取关键词用于检索

9. SCM: validate
   - short_term_memory，验证查询是否需要激活记忆

10. Mem0: none
    - hybrid_memory，直接使用原始查询

11. Mem0ᵍ: none
    - graph_memory，直接使用原始查询

12. SeCom: embedding
    - neuromem_vdb，使用embedding检索语义记忆
"""
