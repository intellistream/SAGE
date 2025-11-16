"""
Refiner算法开发模板
==================

使用此模板快速创建新的Refiner算法。

复制此文件到 algorithms/your_algorithm.py 并修改。
"""

import time
from typing import Any

from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)


class YourRefinerAlgorithm(BaseRefiner):
    """
    [算法名称] - 简短描述

    算法原理:
    - 原理1
    - 原理2
    - ...

    优势:
    - 优势1
    - 优势2

    适用场景:
    - 场景1
    - 场景2

    配置参数:
    - param1 (type): 说明，默认值
    - param2 (type): 说明，默认值

    示例:
        config = {
            "algorithm": "your_algorithm",
            "budget": 2048,
            "param1": value1,
            "param2": value2,
        }

        service = RefinerService(config)
        result = service.refine(query, documents)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化算法"""
        super().__init__(config)

        # 初始化成员变量
        self.model = None
        self.tokenizer = None
        # ... 其他成员变量

    def initialize(self) -> None:
        """
        初始化算法资源

        在首次使用前调用，用于加载模型等耗时操作。
        确保幂等性（多次调用不会重复初始化）。
        """
        if self._initialized:
            return

        try:
            # TODO: 加载模型或初始化资源
            # Issue URL: https://github.com/intellistream/SAGE/issues/983
            # self.model = load_model(self.config.get("model_path"))
            # self.tokenizer = load_tokenizer(...)

            self._initialized = True

        except Exception as e:
            raise RuntimeError(f"Failed to initialize {self.name}: {e}") from e

    def refine(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        **kwargs,
    ) -> RefineResult:
        """
        执行单次压缩

        Args:
            query: 用户查询文本
            documents: 文档列表，可以是:
                - 字符串列表: ["doc1", "doc2", ...]
                - 字典列表: [{"text": "...", "score": 0.9}, ...]
            budget: token预算（覆盖配置中的budget）
            **kwargs: 其他算法特定参数

        Returns:
            RefineResult: 包含压缩后内容和性能指标
        """
        # 确保已初始化
        if not self._initialized:
            self.initialize()

        start_time = time.time()

        # 1. 标准化文档格式
        texts = self._extract_texts(documents)

        # 2. 计算原始token数
        original_tokens = self._count_tokens(texts)

        # 3. 获取budget
        use_budget = budget if budget is not None else self.config.get("budget", 2048)

        # 4. TODO: 执行你的压缩算法
        # Issue URL: https://github.com/intellistream/SAGE/issues/982
        refine_start = time.time()
        compressed_texts = self._compress(query, texts, use_budget, **kwargs)
        refine_time = time.time() - refine_start

        # 5. 计算压缩后token数
        refined_tokens = self._count_tokens(compressed_texts)

        # 6. 计算压缩率
        compression_rate = original_tokens / refined_tokens if refined_tokens > 0 else 0.0

        # 7. 创建性能指标
        metrics = RefinerMetrics(
            refine_time=refine_time,
            total_time=time.time() - start_time,
            original_tokens=original_tokens,
            refined_tokens=refined_tokens,
            compression_rate=compression_rate,
            algorithm=self.name,
            metadata={
                "budget": use_budget,
                "doc_count": len(documents),
                # 添加其他元数据
            },
        )

        # 8. 返回结果
        return RefineResult(
            refined_content=compressed_texts,
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
        """
        批量压缩

        Args:
            queries: 查询列表
            documents_list: 文档列表的列表
            budget: token预算
            **kwargs: 其他参数

        Returns:
            List[RefineResult]: 结果列表
        """
        # 简单实现：逐个调用refine
        # TODO: 如果你的算法支持真正的批处理，可以优化这里
        # Issue URL: https://github.com/intellistream/SAGE/issues/981
        return [
            self.refine(query, docs, budget, **kwargs)
            for query, docs in zip(queries, documents_list, strict=False)
        ]

    def refine_streaming(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        **kwargs,
    ):
        """
        流式压缩（可选实现）

        如果你的算法支持流式输出，实现此方法。

        Yields:
            压缩后的内容片段
        """
        # 默认实现：一次性返回
        result = self.refine(query, documents, budget, **kwargs)
        yield result.refined_content

        # TODO: 如果支持流式，实现类似：
        # Issue URL: https://github.com/intellistream/SAGE/issues/980
        # for chunk in self._compress_streaming(query, documents, budget):
        #     yield chunk

    def shutdown(self) -> None:
        """
        释放资源

        清理模型、释放GPU内存等。
        """
        # TODO: 清理资源
        # Issue URL: https://github.com/intellistream/SAGE/issues/979
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        super().shutdown()

    # ==================== 辅助方法 ====================

    def _extract_texts(self, documents: list[str | dict[str, Any]]) -> list[str]:
        """
        从文档列表中提取文本内容

        处理多种输入格式：字符串、字典等
        """
        texts = []
        for doc in documents:
            if isinstance(doc, str):
                texts.append(doc)
            elif isinstance(doc, dict):
                # 支持多种字段名
                text = doc.get("contents") or doc.get("text") or doc.get("content") or str(doc)
                texts.append(text)
            else:
                texts.append(str(doc))
        return texts

    def _count_tokens(self, texts: str | list[str]) -> int:
        """
        估算token数

        简单实现：按空格分词
        如果有tokenizer，可以用更精确的方法
        """
        if isinstance(texts, str):
            return len(texts.split())
        return sum(len(str(t).split()) for t in texts)

    def _compress(self, query: str, texts: list[str], budget: int, **kwargs) -> list[str]:
        """
        核心压缩逻辑

        TODO: 在这里实现你的压缩算法
        Issue URL: https://github.com/intellistream/SAGE/issues/978

        Args:
            query: 用户查询
            texts: 文档文本列表
            budget: token预算
            **kwargs: 其他参数

        Returns:
            List[str]: 压缩后的文本列表
        """
        # 示例：简单截断
        compressed = []
        current_tokens = 0

        for text in texts:
            text_tokens = self._count_tokens(text)

            if current_tokens + text_tokens <= budget:
                # 完整保留
                compressed.append(text)
                current_tokens += text_tokens
            elif current_tokens < budget:
                # 部分保留
                remaining = budget - current_tokens
                truncated = self._truncate(text, remaining)
                compressed.append(truncated)
                current_tokens += self._count_tokens(truncated)
                break
            else:
                break

        return compressed

    def _truncate(self, text: str, max_tokens: int) -> str:
        """
        截断文本到指定token数

        可以根据需要实现更智能的截断策略
        """
        tokens = text.split()
        if len(tokens) <= max_tokens:
            return text

        # 简单策略：头尾各保留一半
        half = max_tokens // 2
        return " ".join(tokens[:half] + ["..."] + tokens[-half:])


# ==================== 注册算法 ====================

# 1. 在 algorithms/__init__.py 中添加：
# from .your_algorithm import YourRefinerAlgorithm
# __all__.append("YourRefinerAlgorithm")

# 2. 在 config.py 的 RefinerAlgorithm 枚举中添加：
# YOUR_ALGORITHM = "your_algorithm"

# 3. 在 service.py 的 _get_refiner() 中添加：
# elif algorithm == RefinerAlgorithm.YOUR_ALGORITHM:
#     from sage.libs.foundation.context.compression.algorithms.your_algorithm import (
#         YourRefinerAlgorithm,
#     )
#     self.refiner = YourRefinerAlgorithm(self.config.to_dict())
