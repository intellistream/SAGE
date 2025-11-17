"""
RAG Pipeline - RAG 系统的核心管道组件

Layer: L4 (Middleware - Orchestration)
This module orchestrates multiple RAG components (retriever, reranker, refiner, generator)
into a cohesive pipeline. Pipeline/orchestration belongs in middleware, not libs.
"""

from typing import Any


class RAGPipeline:
    """RAG 管道主类 - 编排多个RAG组件"""

    def __init__(self, retriever=None, generator=None, reranker=None, refiner=None):
        self.retriever = retriever
        self.generator = generator
        self.reranker = reranker
        self.refiner = refiner

    def run(self, query: str, **kwargs) -> dict[str, Any]:
        """运行 RAG 管道"""
        # 1. 检索相关文档
        if self.retriever:
            documents = self.retriever.retrieve(query, **kwargs)
        else:
            documents = []

        # 2. 重排序（可选）
        if self.reranker and documents:
            documents = self.reranker.rerank(query, documents, **kwargs)

        # 3. 精化查询或文档（可选）
        if self.refiner:
            query, documents = self.refiner.refine(query, documents, **kwargs)

        # 4. 生成回答
        if self.generator:
            response = self.generator.generate(query, documents, **kwargs)
        else:
            response = "No generator configured"

        return {"query": query, "documents": documents, "response": response}


__all__ = ["RAGPipeline"]
