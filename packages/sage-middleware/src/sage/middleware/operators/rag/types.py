"""
RAG Operators 统一数据结构

定义 RAG pipeline 中各个算子之间传递的标准数据格式。
"""

from typing import Any, Dict, List, Optional, TypedDict


class RAGDocument(TypedDict, total=False):
    """RAG 文档标准格式"""
    text: str  # 文档文本内容（必需）
    title: Optional[str]  # 文档标题
    contents: Optional[str]  # 文档内容（别名）
    relevance_score: Optional[float]  # 相关性分数
    metadata: Optional[Dict[str, Any]]  # 元数据


class RAGQuery(TypedDict, total=False):
    """RAG 查询标准格式"""
    query: str  # 查询文本（必需）
    results: List[Any]  # 检索/处理结果
    context: Optional[List[str]]  # 上下文
    external_corpus: Optional[str]  # 外部语料
    references: Optional[List[str]]  # 参考答案
    generated: Optional[str]  # 生成的回答
    refined_docs: Optional[List[str]]  # 精炼后的文档
    prompt: Optional[Any]  # 提示词
    refine_metrics: Optional[Dict[str, Any]]  # 精炼指标
    generate_time: Optional[float]  # 生成时间


class RAGResponse(TypedDict):
    """RAG 响应标准格式（最小必需字段）"""
    query: str  # 原始查询
    results: List[Any]  # 处理结果（文档列表、生成结果等）


# 类型别名，用于更清晰的类型注解
RAGInput = RAGQuery | RAGResponse | Dict[str, Any] | tuple[str, List[Any]] | list
RAGOutput = RAGResponse | Dict[str, Any]


def ensure_rag_response(data: Any, default_query: str = "") -> RAGResponse:
    """
    确保数据符合 RAGResponse 格式
    
    Args:
        data: 输入数据，可以是各种格式
        default_query: 当无法提取 query 时的默认值
        
    Returns:
        RAGResponse: 标准化的响应格式
    """
    if isinstance(data, dict):
        return {
            "query": data.get("query", default_query),
            "results": data.get("results", [])
        }
    elif isinstance(data, (tuple, list)) and len(data) >= 2:
        return {
            "query": str(data[0]) if data[0] is not None else default_query,
            "results": data[1] if isinstance(data[1], list) else [data[1]]
        }
    else:
        return {
            "query": default_query,
            "results": []
        }


def extract_query(data: Any) -> str:
    """从各种数据格式中提取查询文本"""
    if isinstance(data, dict):
        return data.get("query", "")
    elif isinstance(data, (tuple, list)) and len(data) >= 1:
        return str(data[0]) if data[0] is not None else ""
    else:
        return str(data)


def extract_results(data: Any) -> List[Any]:
    """从各种数据格式中提取结果列表"""
    if isinstance(data, dict):
        return data.get("results", [])
    elif isinstance(data, (tuple, list)) and len(data) >= 2:
        results = data[1]
        return results if isinstance(results, list) else [results]
    else:
        return []


def create_rag_response(query: str, results: List[Any], **kwargs) -> RAGResponse:
    """
    创建标准的 RAG 响应
    
    Args:
        query: 查询文本
        results: 结果列表
        **kwargs: 其他可选字段
        
    Returns:
        RAGResponse: 标准响应格式
    """
    response: RAGResponse = {
        "query": query,
        "results": results
    }
    # 添加其他字段
    response.update(kwargs)  # type: ignore
    return response
