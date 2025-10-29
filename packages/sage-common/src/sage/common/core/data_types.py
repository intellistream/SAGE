"""
通用数据类型定义

定义了 SAGE 系统中算子之间传递的标准化数据结构。
这些类型是框架级别的基础类型，可以被各种专门的算子（RAG、搜索、多模态等）继承和扩展。

设计原则：
1. 通用性：适用于多种场景（检索、生成、搜索、分析等）
2. 可扩展：使用 TypedDict(total=False) 允许添加自定义字段
3. 类型安全：提供完整的类型注解，支持 IDE 和 Pylance 检查
4. 向后兼容：支持多种输入格式（dict、tuple、list）
"""

from typing import Any, TypedDict

# ============================================================================
# 基础文档类型
# ============================================================================


class BaseDocument(TypedDict, total=False):
    """
    基础文档结构 - 表示一个文本片段或检索到的内容

    这是最基础的文档表示，所有领域特定的文档类型都应该继承这个类型。

    必需字段：
        text: 文档的主要文本内容

    可选字段：
        id: 文档的唯一标识符
        title: 文档标题
        source: 文档来源（URL、文件路径、数据库名等）
        score: 相关性分数或置信度 (0.0-1.0)
        rank: 排序位置（从0开始）
        metadata: 任意额外元数据

    示例：
        >>> doc: BaseDocument = {
        ...     "text": "Python是一种编程语言",
        ...     "title": "Python简介",
        ...     "source": "textbook.pdf",
        ...     "score": 0.95
        ... }
    """

    text: str  # 必需：文档文本内容
    id: str | int | None  # 文档唯一标识符
    title: str | None  # 文档标题
    source: str | None  # 文档来源
    score: float | None  # 相关性分数 (0.0-1.0)
    rank: int | None  # 排序位置
    metadata: dict[str, Any] | None  # 额外元数据


# ============================================================================
# 基础查询-结果对类型
# ============================================================================


class BaseQueryResult(TypedDict):
    """
    基础查询-结果对结构 - 表示一个查询及其对应的结果列表

    这是 SAGE 算子之间传递数据的标准格式。
    所有算子都应该能够接受这个格式的输入，并返回这个格式（或其扩展）的输出。

    必需字段：
        query: 用户的查询文本
        results: 结果列表（可以是任何类型）

    可选字段：
        None（子类可以添加）

    示例：
        >>> data: BaseQueryResult = {
        ...     "query": "什么是机器学习",
        ...     "results": ["结果1", "结果2", "结果3"]
        ... }
    """

    query: str  # 必需：用户查询
    results: list[Any]  # 必需：结果列表


class ExtendedQueryResult(BaseQueryResult, total=False):
    """
    扩展查询-结果结构 - 添加了常用的额外字段

    继承 BaseQueryResult，添加了在实际应用中常用的字段。

    额外可选字段：
        query_id: 查询的唯一标识符
        timestamp: 查询时间戳
        total_count: 结果总数（可能大于 results 列表长度）
        execution_time: 执行时间（秒）
        context: 额外的上下文信息
        metadata: 任意元数据

    示例：
        >>> data: ExtendedQueryResult = {
        ...     "query": "Python教程",
        ...     "results": [...],
        ...     "query_id": "q_12345",
        ...     "execution_time": 0.152,
        ...     "total_count": 100
        ... }
    """

    query_id: str | None  # 查询ID
    timestamp: int | float | None  # 时间戳
    total_count: int | None  # 结果总数
    execution_time: float | None  # 执行时间（秒）
    context: str | list[str] | dict[str, Any] | None  # 上下文信息
    metadata: dict[str, Any] | None  # 额外元数据


# ============================================================================
# 类型别名 - 灵活的输入格式
# ============================================================================


# 支持的输入格式：
# 1. 标准字典格式：{"query": "...", "results": [...]}
# 2. 扩展字典格式：包含额外字段的字典
# 3. 元组格式（向后兼容）：("query", ["result1", "result2"])
# 4. 列表格式（向后兼容）：["query", ["result1", "result2"]]
QueryResultInput = BaseQueryResult | ExtendedQueryResult | dict[str, Any] | tuple | list

# 输出格式：应该是标准的字典格式
QueryResultOutput = BaseQueryResult | ExtendedQueryResult | dict[str, Any]


# ============================================================================
# 辅助函数 - 格式转换和提取
# ============================================================================


def ensure_query_result(data: QueryResultInput, default_query: str = "") -> BaseQueryResult:
    """
    确保数据符合 BaseQueryResult 格式

    将各种输入格式统一转换为标准的 BaseQueryResult 格式。

    Args:
        data: 输入数据（可以是字典、元组、列表等）
        default_query: 当无法提取查询时使用的默认值

    Returns:
        BaseQueryResult: 标准化的查询-结果对

    示例：
        >>> ensure_query_result(("query", ["a", "b"]))
        {'query': 'query', 'results': ['a', 'b']}

        >>> ensure_query_result({"question": "...", "docs": [...]})
        {'query': '...', 'results': [...]}
    """
    if isinstance(data, dict):
        query = data.get("query") or data.get("question") or data.get("q") or default_query
        results = (
            data.get("results")
            or data.get("documents")
            or data.get("docs")
            or data.get("items")
            or []
        )
        # Ensure results is a list
        if not isinstance(results, list):
            results = (
                list(results)
                if hasattr(results, "__iter__") and not isinstance(results, str)
                else [results]
            )
        return {"query": str(query), "results": results}

    if isinstance(data, tuple | list) and len(data) >= 2:
        query = str(data[0]) if data[0] is not None else default_query
        results = list(data[1]) if isinstance(data[1], list | tuple) else [data[1]]
        return {"query": query, "results": results}

    # 无法解析，返回空结果
    return {"query": default_query, "results": []}


def extract_query(data: QueryResultInput, default: str = "") -> str:
    """
    从任意格式中提取查询字符串

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
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        return str(
            data.get("query")
            or data.get("question")
            or data.get("q")
            or data.get("text")
            or default
        )

    if isinstance(data, tuple | list) and len(data) > 0:
        return str(data[0]) if data[0] is not None else default

    return default


def extract_results(data: QueryResultInput, default: list[Any] | None = None) -> list[Any]:
    """
    从任意格式中提取结果列表

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
    if default is None:
        default = []

    if isinstance(data, dict):
        results = (
            data.get("results")
            or data.get("documents")
            or data.get("docs")
            or data.get("items")
            or data.get("data")
        )
        if results is not None:
            return list(results) if isinstance(results, list | tuple) else [results]
        return default

    if isinstance(data, tuple | list) and len(data) >= 2:
        results = data[1]
        return list(results) if isinstance(results, list | tuple) else [results]

    if isinstance(data, list | tuple):
        return list(data)

    return default


def create_query_result(query: str, results: list[Any], **kwargs) -> ExtendedQueryResult:
    """
    创建标准的 ExtendedQueryResult 对象

    Args:
        query: 查询字符串
        results: 结果列表
        **kwargs: 额外的字段（如 execution_time, metadata 等）

    Returns:
        ExtendedQueryResult: 标准化的查询结果对象

    示例:
        >>> create_query_result(
        ...     query="test",
        ...     results=["a", "b"],
        ...     execution_time=0.5,
        ...     total_count=2
        ... )
        {'query': 'test', 'results': ['a', 'b'], 'execution_time': 0.5, 'total_count': 2}
    """
    result: ExtendedQueryResult = {
        "query": query,
        "results": results,
    }

    # 添加额外字段
    for key, value in kwargs.items():
        if value is not None:
            result[key] = value  # type: ignore

    return result


# ============================================================================
# 导出
# ============================================================================


__all__ = [
    # 基础类型
    "BaseDocument",
    "BaseQueryResult",
    "ExtendedQueryResult",
    # 类型别名
    "QueryResultInput",
    "QueryResultOutput",
    # 辅助函数
    "ensure_query_result",
    "extract_query",
    "extract_results",
    "create_query_result",
]
