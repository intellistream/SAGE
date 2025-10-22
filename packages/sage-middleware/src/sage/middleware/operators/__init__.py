"""
SAGE Middleware Operators - 领域算子

这个模块提供面向特定业务领域的算子实现：
- LLM算子: 大语言模型推理
- RAG算子: 检索增强生成
- Tool算子: 工具调用

这些算子继承 sage.kernel.operators 的基础算子，实现具体业务逻辑。

使用方式：
    from sage.middleware.operators import rag, llm, tools
    
    # 或直接导入
    from sage.middleware.operators.rag import OpenAIGenerator
    from sage.middleware.operators.llm import VLLMGenerator
"""

# 导出子模块
from . import llm, rag, tools

__all__ = [
    "rag",
    "llm", 
    "tools",
]
