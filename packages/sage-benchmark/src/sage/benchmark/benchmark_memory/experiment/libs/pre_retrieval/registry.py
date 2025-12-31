# PreRetrieval Action 注册表

from .base import BasePreRetrievalAction
from .embedding import EmbeddingAction
from .enhancement.decompose import DecomposeAction
from .enhancement.multi_embed import MultiEmbedAction
from .enhancement.route import RouteAction
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

# Enhancement子类型Actions（查询增强）
PreRetrievalActionRegistry.register("enhancement.decompose", DecomposeAction)
PreRetrievalActionRegistry.register("enhancement.route", RouteAction)
PreRetrievalActionRegistry.register("enhancement.multi_embed", MultiEmbedAction)


# ==================== PreRetrieval Actions 用例说明 ====================
"""
9个PreRetrieval Action的用途和典型用例：

1. none - 透传原始查询
   用途: 不做任何预处理，直接使用原始查询
   用例: "What is Python?" → "What is Python?"
   场景: 简单问答、精确匹配

2. embedding - 查询向量化
   用途: 将查询文本转换为向量表示
   用例: "What is Python?" → [0.12, -0.34, 0.56, ...]
   场景: 向量检索、语义相似度匹配

3. validate - 查询验证
   用途: 验证查询是否需要检索或是否有效
   用例: "Hello" → skip_retrieval=True (闲聊不需要检索)
        "What is Python?" → skip_retrieval=False (需要检索)
   场景: 过滤无效查询、节省检索资源

4. optimize.keyword_extract - 关键词提取
   用途: 从查询中提取关键词/实体
   用例: "Tell me about Python programming language" → ["Python", "programming language"]
   场景: 关键词检索、实体链接、图检索

5. optimize.expand - 查询扩展
   用途: 扩展查询内容，增加相关信息
   用例: "Python" → "Python programming language features syntax"
   场景: 提高召回率、处理简短查询

6. optimize.rewrite - 查询改写
   用途: 改写查询为更易检索的形式
   用例: "How to use it?" → "How to use Python?" (消歧义)
   场景: 消除歧义、规范化查询

7. enhancement.decompose - 复杂查询分解
   用途: 将复杂查询分解为多个子查询
   用例: "What did I eat for breakfast and what was the weather?"
        → ["What did I eat for breakfast?", "What was the weather?"]
   场景: 多步推理、复合问题

8. enhancement.route - 检索路由
   用途: 根据查询类型路由到不同的检索目标
   用例: "What is Python?" → knowledge_base
        "What did I do yesterday?" → long_term_memory
   场景: 多源记忆系统、分类检索

9. enhancement.multi_embed - 多维向量化
   用途: 从多个维度生成查询向量
   用例: "I love Python" → {
            "semantic": [0.12, -0.34, ...],  # 语义维度
            "sentiment": [0.89, 0.02, ...],  # 情感维度
            "entity": [0.45, -0.12, ...]     # 实体维度
        }
   场景: 精细化检索、多模态融合
"""
