"""
Knowledge Search Tool - 知识库检索工具

Layer: L6 (sage-studio)

This tool provides knowledge base search capabilities for the Multi-Agent system,
wrapping the KnowledgeManager's retrieval functionality.

Supported knowledge sources:
- sage_docs: SAGE official documentation
- examples: Code examples and tutorials
- user_uploads: User uploaded documents
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from sage.studio.services.knowledge_manager import KnowledgeManager
from sage.studio.tools.base import BaseTool

logger = logging.getLogger(__name__)


# 定义知识源类型
KnowledgeSourceType = Literal["sage_docs", "examples", "user_uploads"]


class KnowledgeSearchInput(BaseModel):
    """知识库检索工具的输入参数

    Attributes:
        query: 搜索查询内容
        sources: 要搜索的知识源列表，默认搜索 sage_docs 和 examples
        top_k: 返回结果数量，默认 5
        score_threshold: 最低相似度阈值，默认 0.5
    """

    query: str = Field(
        ...,
        description="搜索查询内容，描述你想要查找的信息",
        min_length=1,
        max_length=1000,
    )
    sources: list[KnowledgeSourceType] | None = Field(
        default=None,
        description="要搜索的知识源列表。可选值: sage_docs (SAGE文档), examples (代码示例), user_uploads (用户上传)。不指定则搜索所有默认源。",
    )
    top_k: int = Field(
        default=5,
        description="返回结果的最大数量",
        ge=1,
        le=20,
    )
    score_threshold: float = Field(
        default=0.5,
        description="最低相似度分数阈值 (0-1)，低于此阈值的结果将被过滤",
        ge=0.0,
        le=1.0,
    )


class KnowledgeSearchTool(BaseTool):
    """知识库检索工具

    封装 KnowledgeManager 的检索功能，为 Multi-Agent 系统提供
    知识库搜索能力。支持搜索 SAGE 文档、代码示例和用户上传的资料。

    Example:
        >>> from sage.studio.services.knowledge_manager import KnowledgeManager
        >>>
        >>> km = KnowledgeManager()
        >>> tool = KnowledgeSearchTool(km)
        >>> result = await tool.run(query="如何使用 Pipeline")
        >>> print(result["status"])
        'success'
        >>> for doc in result["result"]:
        ...     print(doc["content"][:100])
    """

    name: ClassVar[str] = "knowledge_search"
    description: ClassVar[str] = (
        "搜索 SAGE 知识库，获取相关文档、代码示例和技术资料。"
        "当需要了解 SAGE 框架的使用方法、API 文档、最佳实践或示例代码时使用此工具。"
    )
    args_schema: ClassVar[type[BaseModel]] = KnowledgeSearchInput

    # 默认搜索的知识源
    DEFAULT_SOURCES: ClassVar[list[str]] = ["sage_docs", "examples"]

    def __init__(self, knowledge_manager: KnowledgeManager) -> None:
        """初始化知识库检索工具

        Args:
            knowledge_manager: KnowledgeManager 实例，用于执行实际的检索操作
        """
        super().__init__()
        self._km = knowledge_manager

    @property
    def knowledge_manager(self) -> KnowledgeManager:
        """获取 KnowledgeManager 实例"""
        return self._km

    async def _run(
        self,
        query: str,
        sources: list[str] | None = None,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """执行知识库检索

        Args:
            query: 搜索查询内容
            sources: 要搜索的知识源列表
            top_k: 返回结果数量
            score_threshold: 最低相似度阈值

        Returns:
            检索结果列表，每个结果包含:
            - content: 文档内容片段
            - source: 来源知识源
            - score: 相似度分数
            - metadata: 额外元数据（如文件路径、章节等）

        Raises:
            Exception: 检索过程中的任何错误
        """
        # 使用默认源（如果未指定）
        search_sources = sources if sources else self.DEFAULT_SOURCES

        logger.debug(
            f"Searching knowledge base: query='{query[:50]}...', "
            f"sources={search_sources}, top_k={top_k}"
        )

        # 调用 KnowledgeManager 的检索方法
        results = await self._km.search(
            query=query,
            sources=search_sources,
            limit=top_k,
            score_threshold=score_threshold,
        )

        # 转换为统一的输出格式
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "content": result.content,
                    "source": result.source,
                    "score": result.score,
                    "metadata": {
                        "file_path": result.file_path,
                        "chunk_id": result.chunk_id,
                        **result.metadata,
                    },
                }
            )

        logger.info(
            f"Knowledge search completed: found {len(formatted_results)} results "
            f"for query '{query[:30]}...'"
        )

        return formatted_results

    def get_available_sources(self) -> list[dict[str, Any]]:
        """获取所有可用的知识源列表

        Returns:
            知识源信息列表，每个包含 name, description, enabled, loaded 等字段
        """
        return self._km.list_sources()
