"""
LongRefiner算法实现
==================

基于LongRefiner的上下文压缩算法。

LongRefiner采用三阶段压缩策略：
1. Query Analysis: 分析用户查询意图，提取关键信息需求
2. Document Structuring: 结构化提取文档关键信息
3. Global Selection: 基于预算全局选择最相关内容

参考论文: LongRefiner - Enhancing Long-Context RAG via Retrieval-Aware Compression
"""

import time
from typing import Any

from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)


class LongRefinerAlgorithm(BaseRefiner):
    """
    LongRefiner算法实现

    这是一个SOTA的上下文压缩算法，使用LoRA微调的多模块协同工作。

    核心组件：
    - Query Analysis Module: 理解查询意图
    - Document Structuring Module: 提取文档结构化信息
    - Global Selection Module: 全局内容选择
    - Score Model: 评估内容相关性

    配置要求：
    - base_model_path: 基础LLM路径
    - query_analysis_module_lora_path: 查询分析LoRA权重
    - doc_structuring_module_lora_path: 文档结构化LoRA权重
    - global_selection_module_lora_path: 全局选择LoRA权重
    - score_model_path: 评分模型路径
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.refiner = None

    def initialize(self) -> None:
        """初始化LongRefiner模型"""
        if self._initialized:
            return

        try:
            # 从本地实现导入，不再依赖sage-libs
            from sage.libs.foundation.context.compression.algorithms.long_refiner_impl.refiner import (
                LongRefiner,
            )

            # 准备配置
            required_fields = [
                "base_model_path",
                "query_analysis_module_lora_path",
                "doc_structuring_module_lora_path",
                "global_selection_module_lora_path",
                "score_model_name",
                "score_model_path",
                "max_model_len",
            ]

            missing = [f for f in required_fields if not self.config.get(f)]
            if missing:
                raise ValueError(f"Missing required config fields: {missing}")

            # 创建LongRefiner实例
            self.refiner = LongRefiner(
                base_model_path=self.config["base_model_path"],
                query_analysis_module_lora_path=self.config["query_analysis_module_lora_path"],
                doc_structuring_module_lora_path=self.config["doc_structuring_module_lora_path"],
                global_selection_module_lora_path=self.config["global_selection_module_lora_path"],
                score_model_name=self.config["score_model_name"],
                score_model_path=self.config["score_model_path"],
                max_model_len=self.config.get("max_model_len", 25000),
                gpu_device=self.config.get("gpu_device", 0),
                score_gpu_device=self.config.get("score_gpu_device"),
                gpu_memory_utilization=self.config.get("gpu_memory_utilization", 0.7),
            )

            self._initialized = True

        except ImportError as e:
            raise ImportError(
                "LongRefiner not available. Please ensure sage-libs is installed "
                "with LongRefiner dependencies."
            ) from e

    def _normalize_documents(self, documents: list[str | dict[str, Any]]) -> list[dict[str, str]]:
        """标准化文档格式"""
        normalized = []
        for doc in documents:
            if isinstance(doc, str):
                normalized.append({"contents": doc})
            elif isinstance(doc, dict):
                # 支持多种字段名
                content = doc.get("contents") or doc.get("text") or doc.get("content") or str(doc)
                normalized.append({"contents": content})
            else:
                normalized.append({"contents": str(doc)})
        return normalized

    def _count_tokens(self, texts: str | list[str]) -> int:
        """估算token数（简单方法：按空格分词）"""
        if isinstance(texts, str):
            return len(texts.split())
        return sum(len(str(t).split()) for t in texts)

    def refine(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        **kwargs,
    ) -> RefineResult:
        """精炼文档"""
        if not self._initialized:
            self.initialize()

        start_time = time.time()

        # 标准化文档格式
        normalized_docs = self._normalize_documents(documents)

        # 计算原始token数
        original_tokens = self._count_tokens([d["contents"] for d in normalized_docs])

        # 使用配置中的budget或传入的budget
        use_budget = budget if budget is not None else self.config.get("budget", 2048)

        # 确保refiner已初始化
        if self.refiner is None:
            raise RuntimeError("LongRefiner not initialized. Call initialize() before using run().")

        # 执行精炼
        refine_start = time.time()
        refined_items = self.refiner.run(
            question=query,
            document_list=normalized_docs,
            budget=use_budget,
            ratio=kwargs.get("ratio"),
        )
        refine_time = time.time() - refine_start

        # 处理结果
        if not refined_items:
            refined_content = []
            refined_tokens = 0
        elif isinstance(refined_items, list):
            refined_content = refined_items
            refined_tokens = self._count_tokens(refined_items)
        else:
            refined_content = [str(refined_items)]
            refined_tokens = self._count_tokens(str(refined_items))

        total_time = time.time() - start_time

        # 计算压缩率
        compression_rate = original_tokens / refined_tokens if refined_tokens > 0 else 0.0

        # 创建指标
        metrics = RefinerMetrics(
            refine_time=refine_time,
            total_time=total_time,
            original_tokens=original_tokens,
            refined_tokens=refined_tokens,
            compression_rate=compression_rate,
            algorithm=self.name,
            metadata={
                "budget": use_budget,
                "doc_count": len(documents),
            },
        )

        return RefineResult(
            refined_content=refined_content,
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
        """批量精炼"""
        if not self._initialized:
            self.initialize()

        start_time = time.time()

        # 标准化所有文档
        normalized_docs_list = [self._normalize_documents(docs) for docs in documents_list]

        # 计算原始token数
        original_tokens_list = [
            self._count_tokens([d["contents"] for d in docs]) for docs in normalized_docs_list
        ]

        # 使用配置中的budget或传入的budget
        use_budget = budget if budget is not None else self.config.get("budget", 2048)

        # 确保refiner已初始化
        if self.refiner is None:
            raise RuntimeError(
                "LongRefiner not initialized. Call initialize() before using batch_run()."
            )

        # 批量执行
        refine_start = time.time()
        refined_items_list = self.refiner.batch_run(
            question_list=queries,
            document_list=normalized_docs_list,
            budget=use_budget,
            ratio=kwargs.get("ratio"),
        )
        refine_time = time.time() - refine_start

        # 处理结果
        results = []
        for i, refined_items in enumerate(refined_items_list):
            if not refined_items:
                refined_content = []
                refined_tokens = 0
            elif isinstance(refined_items, list):
                refined_content = refined_items
                refined_tokens = self._count_tokens(refined_items)
            else:
                refined_content = [str(refined_items)]
                refined_tokens = self._count_tokens(str(refined_items))

            compression_rate = (
                original_tokens_list[i] / refined_tokens if refined_tokens > 0 else 0.0
            )

            metrics = RefinerMetrics(
                refine_time=refine_time / len(queries),  # 平均时间
                total_time=(time.time() - start_time) / len(queries),
                original_tokens=original_tokens_list[i],
                refined_tokens=refined_tokens,
                compression_rate=compression_rate,
                algorithm=self.name,
                metadata={
                    "budget": use_budget,
                    "doc_count": len(documents_list[i]),
                    "batch_index": i,
                },
            )

            results.append(
                RefineResult(
                    refined_content=refined_content,
                    metrics=metrics,
                    original_content=(documents_list[i] if kwargs.get("keep_original") else None),
                )
            )

        return results

    def shutdown(self) -> None:
        """释放资源"""
        if self.refiner is not None:
            # LongRefiner没有显式的清理方法，依赖Python GC
            self.refiner = None
        super().shutdown()
