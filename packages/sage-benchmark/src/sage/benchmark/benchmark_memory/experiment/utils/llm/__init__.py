"""LLM 调用层工具

提供统一的大模型调用接口：
- LLMGenerator: LLM 文本生成，内置 JSON/三元组解析
- EmbeddingGenerator: Embedding 生成
"""

from .embedding_generator import EmbeddingGenerator
from .llm_generator import LLMGenerator

__all__ = [
    "LLMGenerator",
    "EmbeddingGenerator",
]
