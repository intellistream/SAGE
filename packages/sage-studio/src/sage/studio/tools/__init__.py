"""
Studio Tools Package - 工具层

Layer: L6 (sage-studio)

提供 Multi-Agent 系统所需的工具基础设施和具体工具实现。

Exports:
    Base Classes:
    - BaseTool: 工具基类
    - ToolRegistry: 工具注册表
    - get_tool_registry: 获取全局注册表
    - reset_tool_registry: 重置全局注册表（测试用）

    Tools:
    - KnowledgeSearchTool: 知识库检索工具
    - KnowledgeSearchInput: 知识库检索工具的输入参数模型
    - APIDocsTool: API 文档查询工具
    - ArxivSearchTool: Arxiv 论文搜索工具

    Helper Functions:
    - get_all_tools: 获取所有可用工具实例
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sage.studio.tools.api_docs import APIDocsTool
from sage.studio.tools.arxiv_search import ArxivSearchTool
from sage.studio.tools.base import (
    BaseTool,
    ToolRegistry,
    get_tool_registry,
    reset_tool_registry,
)
from sage.studio.tools.knowledge_search import (
    KnowledgeSearchInput,
    KnowledgeSearchTool,
)

if TYPE_CHECKING:
    from sage.studio.services.knowledge_manager import KnowledgeManager

__all__ = [
    # Base classes
    "BaseTool",
    "ToolRegistry",
    "get_tool_registry",
    "reset_tool_registry",
    # Tools
    "KnowledgeSearchTool",
    "KnowledgeSearchInput",
    "APIDocsTool",
    "ArxivSearchTool",
    # Helper functions
    "get_all_tools",
]


def get_all_tools(knowledge_manager: KnowledgeManager | None = None) -> list[BaseTool]:
    """获取所有可用的工具实例

    这是一个便捷函数，用于快速获取所有 Studio 工具的实例列表。
    返回的工具列表可以直接传递给 AgentOrchestrator 或 ToolRegistry。

    Args:
        knowledge_manager: KnowledgeManager 实例，用于 KnowledgeSearchTool。
                          如果为 None，则不包含 KnowledgeSearchTool。

    Returns:
        工具实例列表

    Example:
        >>> from sage.studio.services.knowledge_manager import KnowledgeManager
        >>> from sage.studio.tools import get_all_tools, get_tool_registry
        >>>
        >>> km = KnowledgeManager()
        >>> tools = get_all_tools(km)
        >>>
        >>> # 注册到全局注册表
        >>> registry = get_tool_registry()
        >>> for tool in tools:
        ...     registry.register(tool)
    """
    tools: list[BaseTool] = [
        APIDocsTool(),
        ArxivSearchTool(),
    ]

    # KnowledgeSearchTool 需要 KnowledgeManager
    if knowledge_manager is not None:
        tools.insert(0, KnowledgeSearchTool(knowledge_manager))

    return tools
