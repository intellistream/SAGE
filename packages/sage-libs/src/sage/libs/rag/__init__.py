"""
SAGE - Streaming-Augmented Generative Execution

Note: RAG operators have been moved to sage.middleware.operators.rag
This module provides backward compatibility imports with deprecation warnings.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Backward compatibility imports with deprecation warnings
import warnings


def _deprecated_import(name, new_location):
    """Helper function to show deprecation warning"""
    warnings.warn(
        f"{name} has been moved to {new_location}. "
        f"Please update your imports to use 'from {new_location} import {name}'. "
        f"This compatibility import will be removed in a future version.",
        DeprecationWarning,
        stacklevel=3,
    )


# Re-export operators from middleware with deprecation warnings
def __getattr__(name):
    # Generators
    if name in ["OpenAIGenerator", "HFGenerator"]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import HFGenerator, OpenAIGenerator

        return OpenAIGenerator if name == "OpenAIGenerator" else HFGenerator

    # Retrievers
    if name in [
        "ChromaRetriever",
        "MilvusDenseRetriever",
        "MilvusSparseRetriever",
        "Wiki18FAISSRetriever",
    ]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import (
            ChromaRetriever,
            MilvusDenseRetriever,
            MilvusSparseRetriever,
            Wiki18FAISSRetriever,
        )

        return {
            "ChromaRetriever": ChromaRetriever,
            "MilvusDenseRetriever": MilvusDenseRetriever,
            "MilvusSparseRetriever": MilvusSparseRetriever,
            "Wiki18FAISSRetriever": Wiki18FAISSRetriever,
        }[name]

    # Rerankers
    if name in ["BGEReranker", "LLMbased_Reranker"]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import BGEReranker, LLMbased_Reranker

        return BGEReranker if name == "BGEReranker" else LLMbased_Reranker

    # Promptors
    if name in ["QAPromptor", "SummarizationPromptor", "QueryProfilerPromptor"]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import (
            QAPromptor,
            QueryProfilerPromptor,
            SummarizationPromptor,
        )

        return {
            "QAPromptor": QAPromptor,
            "SummarizationPromptor": SummarizationPromptor,
            "QueryProfilerPromptor": QueryProfilerPromptor,
        }[name]

    # Evaluation operators
    if name in [
        "F1Evaluate",
        "RecallEvaluate",
        "BertRecallEvaluate",
        "RougeLEvaluate",
        "BRSEvaluate",
        "AccuracyEvaluate",
        "TokenCountEvaluate",
        "LatencyEvaluate",
        "ContextRecallEvaluate",
        "CompressionRateEvaluate",
    ]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import (
            AccuracyEvaluate,
            BertRecallEvaluate,
            BRSEvaluate,
            CompressionRateEvaluate,
            ContextRecallEvaluate,
            F1Evaluate,
            LatencyEvaluate,
            RecallEvaluate,
            RougeLEvaluate,
            TokenCountEvaluate,
        )

        return {
            "F1Evaluate": F1Evaluate,
            "RecallEvaluate": RecallEvaluate,
            "BertRecallEvaluate": BertRecallEvaluate,
            "RougeLEvaluate": RougeLEvaluate,
            "BRSEvaluate": BRSEvaluate,
            "AccuracyEvaluate": AccuracyEvaluate,
            "TokenCountEvaluate": TokenCountEvaluate,
            "LatencyEvaluate": LatencyEvaluate,
            "ContextRecallEvaluate": ContextRecallEvaluate,
            "CompressionRateEvaluate": CompressionRateEvaluate,
        }[name]

    # Document processing operators
    if name in [
        "CharacterSplitter",
        "SentenceTransformersTokenTextSplitter",
        "RefinerOperator",
        "MemoryWriter",
    ]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import (
            CharacterSplitter,
            MemoryWriter,
            RefinerOperator,
            SentenceTransformersTokenTextSplitter,
        )

        return {
            "CharacterSplitter": CharacterSplitter,
            "SentenceTransformersTokenTextSplitter": SentenceTransformersTokenTextSplitter,
            "RefinerOperator": RefinerOperator,
            "MemoryWriter": MemoryWriter,
        }[name]

    # External data source operators
    if name in ["ArxivPDFDownloader", "ArxivPDFParser"]:
        _deprecated_import(name, "sage.middleware.operators.rag")
        from sage.middleware.operators.rag import ArxivPDFDownloader, ArxivPDFParser

        return ArxivPDFDownloader if name == "ArxivPDFDownloader" else ArxivPDFParser

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

