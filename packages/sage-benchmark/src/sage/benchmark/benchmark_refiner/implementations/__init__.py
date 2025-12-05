"""
Benchmark Refiner Implementations
=================================

包含各种Refiner算法的RAG评测Pipeline实现。

可用Pipeline:
- baseline_rag: 无压缩基线，用于对比实验
- longrefiner_rag: LongRefiner三阶段压缩
- reform_rag: REFORM注意力头驱动压缩
- provence_rag: Provence句子级剪枝
- llmlingua2_rag: LLMLingua-2 BERT token分类压缩 (快速)
- longllmlingua_rag: LongLLMLingua问题感知长文档压缩

运行方式:
    # 直接运行
    python -m sage.benchmark.benchmark_refiner.implementations.pipelines.baseline_rag
    python -m sage.benchmark.benchmark_refiner.implementations.pipelines.longrefiner_rag
    python -m sage.benchmark.benchmark_refiner.implementations.pipelines.reform_rag
    python -m sage.benchmark.benchmark_refiner.implementations.pipelines.provence_rag
    python -m sage.benchmark.benchmark_refiner.implementations.pipelines.llmlingua2_rag
    python -m sage.benchmark.benchmark_refiner.implementations.pipelines.longllmlingua_rag

配置文件:
    各Pipeline对应的配置文件位于 ../config/ 目录
"""

__all__: list[str] = []
