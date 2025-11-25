"""
RAG 专用数据类型定义

基于 sage.common.core.data_types 的基础类型，为 RAG 场景定制的数据结构。

继承关系：
    BaseDocument (通用基础) → RAGDocument (RAG专用)
    BaseQueryResult (通用基础) → RAGQuery/RAGResponse (RAG专用)

设计原则：
1. 继承通用类型，保持与其他算子的兼容性
2. 添加 RAG 特定的字段（如 relevance_score, generated 等）
3. 保持向后兼容，支持多种输入格式
4. 类型安全，支持 IDE 和 Pylance 检查

使用示例：
    >>> from sage.libs.rag.types import RAGResponse, create_rag_response
    >>>
    >>> # 算子输出标准格式
    >>> response = create_rag_response(
    ...     query="什么是机器学习",
    ...     results=["doc1", "doc2"],
    ...     generated="机器学习是...",
    ...     execution_time=1.5
    ... )
"""

from typing import Any, Union

# 导入基础类型
from sage.common.core import (
    BaseDocument,
    BaseQueryResult,
    ExtendedQueryResult,
    QueryResultInput,
)
from sage.common.core import extract_query as base_extract_query
from sage.common.core import extract_results as base_extract_results

# ============================================================================
# RAG 专用文档类型
# ============================================================================


class RAGDocument(BaseDocument, total=False):
    """
    RAG 文档结构 - 扩展基础文档，添加 RAG 特定字段

    继承 BaseDocument 的所有字段，添加了 RAG 场景常用的字段。

    继承的必需字段：
        text: 文档文本内容

    继承的可选字段：
        id, title, source, score, rank, metadata

    新增 RAG 专用字段：
        contents: 原始完整内容（text 可能是摘要）
        relevance_score: RAG 特定的相关性分数
        embedding: 文档的向量嵌入
        chunk_id: 分块ID（用于长文档分块）
        references: 引用的其他文档ID列表

    示例：
        >>> doc: RAGDocument = {
        ...     "text": "Python是一种高级编程语言...",
        ...     "title": "Python入门",
        ...     "relevance_score": 0.92,
        ...     "source": "textbook.pdf",
        ...     "chunk_id": 5
        ... }
    """

    contents: str | None  # 原始完整内容
    relevance_score: float | None  # RAG相关性分数
    embedding: list[float] | None  # 向量嵌入
    chunk_id: int | None  # 分块ID
    references: list[str] | None  # 引用列表


# ============================================================================
# RAG 查询和响应类型
# ============================================================================


class RAGQuery(ExtendedQueryResult, total=False):
    """
    RAG 查询结构 - 扩展基础查询结果，添加 RAG pipeline 相关字段

    继承 ExtendedQueryResult，添加了 RAG pipeline 各阶段可能需要的字段。
    这个类型用于在 RAG pipeline 的各个阶段传递数据。

    继承的必需字段：
        query: 用户查询
        results: 结果列表

    继承的可选字段：
        query_id, timestamp, total_count, execution_time, context, metadata

    新增 RAG 专用字段：
        external_corpus: 外部检索的文档
        references: 引用文档列表
        generated: 生成的文本（答案）
        refined_docs: 精炼后的文档
        reranked: 重排序标记
        prompt: 使用的提示词模板
        refine_metrics: 精炼阶段的指标
        generate_time: 生成阶段耗时

    示例：
        >>> query: RAGQuery = {
        ...     "query": "什么是机器学习",
        ...     "results": ["doc1", "doc2"],
        ...     "context": "检索到的上下文...",
        ...     "generated": "机器学习是...",
        ...     "execution_time": 1.5
        ... }
    """

    external_corpus: list[str | dict[str, Any]] | None  # 外部文档
    references: list[str] | None  # 引用列表
    generated: str | None  # 生成的答案
    refined_docs: list[str] | None  # 精炼后的文档
    reranked: bool | None  # 是否经过重排序
    prompt: str | None  # 使用的提示词
    refine_metrics: dict[str, Any] | None  # 精炼指标
    generate_time: float | None  # 生成耗时


class RAGResponse(BaseQueryResult, total=False):
    """
    RAG 响应结构 - RAG 算子的标准输出格式

    所有 RAG 算子都应该返回这个格式（或其父类型 BaseQueryResult）。
    这确保了 RAG pipeline 各阶段的数据流一致性。

    继承的必需字段：
        query: 原始查询
        results: 处理后的结果列表

    推荐 RAG 专用字段：
        generated: 最终生成的答案（Generator 输出）
        context: 使用的上下文（字符串或列表）
        execution_time: 执行时间
        metadata: 各阶段的元数据

    示例：
        >>> response: RAGResponse = {
        ...     "query": "什么是机器学习",
        ...     "results": ["doc1", "doc2"],
        ...     "generated": "机器学习是...",
        ...     "execution_time": 1.5
        ... }
    """

    generated: str | None  # 生成的答案
    context: str | list[str] | None  # 上下文
    execution_time: float | None  # 执行时间
    metadata: dict[str, Any] | None  # 元数据


# ============================================================================
# 类型别名 - RAG 专用的灵活输入输出
# ============================================================================

# RAG 算子的输入可以是多种格式（向后兼容）
RAGInput = Union[
    RAGQuery,
    RAGResponse,
    QueryResultInput,  # 包含 dict, tuple, list 等
]

# RAG 算子的输出应该是标准格式
RAGOutput = Union[RAGResponse, dict[str, Any]]


# ============================================================================
# 辅助函数 - RAG 专用包装器
# ============================================================================


def ensure_rag_response(data: RAGInput, default_query: str = "") -> RAGResponse:
    """
    确保数据符合 RAGResponse 格式（RAG 专用）

    这是 sage.common.core.data_types.ensure_query_result() 的 RAG 专用版本。

    Args:
        data: 输入数据（可以是字典、元组、列表等）
        default_query: 当无法提取查询时使用的默认值

    Returns:
        RAGResponse: 标准化的 RAG 响应

    示例：
        >>> ensure_rag_response(("query", ["a", "b"]))
        {'query': 'query', 'results': ['a', 'b']}

        >>> ensure_rag_response({"question": "...", "docs": [...]})
        {'query': '...', 'results': [...]}
    """
    # 使用基础函数，然后转换为 RAGResponse
    from sage.common.core import ensure_query_result

    base_result = ensure_query_result(data, default_query)
    rag_response: RAGResponse = {
        "query": base_result["query"],
        "results": base_result["results"],
    }

    # 如果是字典，保留额外的 RAG 字段
    if isinstance(data, dict):
        for key in [
            "generated",
            "context",
            "execution_time",
            "metadata",
            "refine_metrics",
            "generate_time",
        ]:
            if key in data:
                rag_response[key] = data[key]  # type: ignore

    return rag_response


def extract_query(data: RAGInput, default: str = "") -> str:
    """
    从任意格式中提取查询字符串（RAG 专用）

    直接使用基础函数，完全兼容。

    Args:
        data: 输入数据
        default: 默认值

    Returns:
        str: 提取的查询字符串

    示例：
        >>> extract_query({"query": "test"})
        'test'

        >>> extract_query(("my query", ["results"]))
        'my query'
    """
    return base_extract_query(data, default)


def extract_results(data: RAGInput, default: list[Any] | None = None) -> list[Any]:
    """
    从任意格式中提取结果列表（RAG 专用）

    直接使用基础函数，完全兼容。

    Args:
        data: 输入数据
        default: 默认值

    Returns:
        List[Any]: 提取的结果列表

    示例:
        >>> extract_results({"query": "test", "results": ["a", "b"]})
        ['a', 'b']

        >>> extract_results(("query", ["a", "b"]))
        ['a', 'b']
    """
    return base_extract_results(data, default)


def create_rag_response(query: str, results: list[Any], **kwargs) -> RAGResponse:
    """
    创建标准的 RAGResponse 对象

    Args:
        query: 查询字符串
        results: 结果列表
        **kwargs: 额外的 RAG 字段（如 generated, execution_time, metadata 等）

    Returns:
        RAGResponse: 标准化的 RAG 响应对象

    示例:
        >>> create_rag_response(
        ...     query="test",
        ...     results=["a", "b"],
        ...     generated="answer",
        ...     execution_time=0.5,
        ...     metadata={"model": "gpt-4"}
        ... )
        {'query': 'test', 'results': ['a', 'b'], 'generated': 'answer',
         'execution_time': 0.5, 'metadata': {'model': 'gpt-4'}}
    """
    response: RAGResponse = {
        "query": query,
        "results": results,
    }

    # 添加额外的 RAG 字段
    for key, value in kwargs.items():
        if value is not None:
            response[key] = value  # type: ignore

    return response


# ============================================================================
# 导出
# ============================================================================


__all__ = [
    # RAG 专用类型
    "RAGDocument",
    "RAGQuery",
    "RAGResponse",
    # RAG 类型别名
    "RAGInput",
    "RAGOutput",
    # RAG 辅助函数
    "ensure_rag_response",
    "extract_query",
    "extract_results",
    "create_rag_response",
]
