"""
简单Refiner实现
==============

提供基础的截断和摘要功能，不依赖重量级模型。
"""

import time
from typing import Any

from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)


class SimpleRefiner(BaseRefiner):
    """
    简单的上下文压缩实现

    使用简单的策略进行压缩：
    - 头尾截断
    - 按相关性排序（如果有score）
    - Token限制
    """

    def initialize(self) -> None:
        """简单实现不需要初始化"""
        self._initialized = True

    def _count_tokens(self, text: str) -> int:
        """估算token数"""
        return len(text.split())

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """截断文本到指定token数"""
        tokens = text.split()
        if len(tokens) <= max_tokens:
            return text

        # 保留头尾各一半
        half = max_tokens // 2
        return " ".join(tokens[:half] + ["..."] + tokens[-half:])

    def refine(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        **kwargs,
    ) -> RefineResult:
        """简单精炼"""
        if not self._initialized:
            self.initialize()

        start_time = time.time()

        # 使用budget
        use_budget = budget if budget is not None else self.config.get("budget", 2048)

        # 提取文本
        texts = []
        scores = []
        for doc in documents:
            if isinstance(doc, str):
                texts.append(doc)
                scores.append(1.0)
            elif isinstance(doc, dict):
                text = doc.get("contents") or doc.get("text") or doc.get("content") or str(doc)
                texts.append(text)
                scores.append(doc.get("score", 1.0))
            else:
                texts.append(str(doc))
                scores.append(1.0)

        # 计算原始token数
        original_tokens = sum(self._count_tokens(t) for t in texts)

        # 按score排序（如果有的话）
        if any(s != 1.0 for s in scores):
            sorted_items = sorted(
                zip(texts, scores, strict=False), key=lambda x: x[1], reverse=True
            )
            texts = [t for t, _ in sorted_items]

        # 逐个添加文档，直到达到budget
        refined_texts = []
        current_tokens = 0

        for text in texts:
            text_tokens = self._count_tokens(text)

            if current_tokens + text_tokens <= use_budget:
                # 完整添加
                refined_texts.append(text)
                current_tokens += text_tokens
            elif current_tokens < use_budget:
                # 部分添加
                remaining = use_budget - current_tokens
                truncated = self._truncate_text(text, remaining)
                refined_texts.append(truncated)
                current_tokens += self._count_tokens(truncated)
                break
            else:
                break

        total_time = time.time() - start_time
        refined_tokens = sum(self._count_tokens(t) for t in refined_texts)

        metrics = RefinerMetrics(
            refine_time=total_time,
            total_time=total_time,
            original_tokens=original_tokens,
            refined_tokens=refined_tokens,
            compression_rate=(original_tokens / refined_tokens if refined_tokens > 0 else 0.0),
            algorithm=self.name,
            metadata={
                "budget": use_budget,
                "doc_count": len(documents),
                "kept_docs": len(refined_texts),
            },
        )

        return RefineResult(
            refined_content=refined_texts,
            metrics=metrics,
            original_content=documents if kwargs.get("keep_original") else None,
        )

    def refine_batch(
        self,
        queries: list[str],
        documents_list: list[list[str | dict[str, Any]]],
        budget: int | None = None,
        **kwargs,
    ) -> list[RefineResult]:
        """批量精炼（逐个处理）"""
        return [
            self.refine(query, docs, budget, **kwargs)
            for query, docs in zip(queries, documents_list, strict=False)
        ]
