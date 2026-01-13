"""
SAGE Middleware Operators - 领域算子

这个模块提供面向特定业务领域的算子实现：
- LLM算子: 大语言模型推理 (SageLLMGenerator)
- RAG算子: 检索增强生成算子 (Retriever, Refiner, Reranker, Generator等)
- Tool算子: 工具调用 + 领域特定工具 (arxiv, image_captioner等)
- Filters: 业务过滤器 (tool_filter, evaluate_filter, context source/sink)
- Agentic: Agent runtime operators (requires isage-agentic)

向量数据库集成位于: sage.middleware.components.vector_stores

这些算子继承 sage.kernel.operators 的基础算子，实现具体业务逻辑。

使用方式：
    from sage.middleware.operators import rag, llm, tools, filters

    # 或直接导入
    from sage.middleware.operators.rag import ChromaRetriever
    from sage.middleware.operators.llm import SageLLMGenerator
    from sage.middleware.components.vector_stores import MilvusBackend, ChromaBackend

    # Agentic operators (requires isage-agentic)
    from sage.middleware.operators.agentic import PlanningOperator
"""

# 导出子模块
from . import agentic, filters, llm, rag, tools
from sage.middleware.operators.llm.sagellm_generator import SageLLMGenerator

__all__ = [
    "rag",
    "llm",
    "tools",
    "filters",
    "agentic",
    "SageLLMGenerator",
]
