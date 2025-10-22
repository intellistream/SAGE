"""
RAG (Retrieval-Augmented Generation) Operators

This module contains domain-specific operators for RAG applications:
- Generator operators (LLM response generation)
- Retriever operators (document/passage retrieval)
- Reranker operators (result reranking)
- Promptor operators (prompt construction)
- Evaluation operators (quality metrics)
- Document processing operators (chunking, refining, writing)
- External data source operators (ArXiv)

These operators inherit from base operator classes in sage.kernel.operators
and implement RAG-specific business logic.
"""

# Lazy imports to avoid optional dependency issues
_IMPORTS = {
    # Generators
    "OpenAIGenerator": ("sage.middleware.operators.rag.generator", "OpenAIGenerator"),
    "HFGenerator": ("sage.middleware.operators.rag.generator", "HFGenerator"),
    # Retrievers
    "ChromaRetriever": ("sage.middleware.operators.rag.retriever", "ChromaRetriever"),
    "MilvusDenseRetriever": ("sage.middleware.operators.rag.retriever", "MilvusDenseRetriever"),
    "MilvusSparseRetriever": ("sage.middleware.operators.rag.retriever", "MilvusSparseRetriever"),
    "Wiki18FAISSRetriever": ("sage.middleware.operators.rag.retriever", "Wiki18FAISSRetriever"),
    # Rerankers
    "BGEReranker": ("sage.middleware.operators.rag.reranker", "BGEReranker"),
    "LLMbased_Reranker": ("sage.middleware.operators.rag.reranker", "LLMbased_Reranker"),
    # Promptors
    "QAPromptor": ("sage.middleware.operators.rag.promptor", "QAPromptor"),
    "SummarizationPromptor": ("sage.middleware.operators.rag.promptor", "SummarizationPromptor"),
    "QueryProfilerPromptor": ("sage.middleware.operators.rag.promptor", "QueryProfilerPromptor"),
    # Evaluation
    "F1Evaluate": ("sage.middleware.operators.rag.evaluate", "F1Evaluate"),
    "RecallEvaluate": ("sage.middleware.operators.rag.evaluate", "RecallEvaluate"),
    "BertRecallEvaluate": ("sage.middleware.operators.rag.evaluate", "BertRecallEvaluate"),
    "RougeLEvaluate": ("sage.middleware.operators.rag.evaluate", "RougeLEvaluate"),
    "BRSEvaluate": ("sage.middleware.operators.rag.evaluate", "BRSEvaluate"),
    "AccuracyEvaluate": ("sage.middleware.operators.rag.evaluate", "AccuracyEvaluate"),
    "TokenCountEvaluate": ("sage.middleware.operators.rag.evaluate", "TokenCountEvaluate"),
    "LatencyEvaluate": ("sage.middleware.operators.rag.evaluate", "LatencyEvaluate"),
    "ContextRecallEvaluate": ("sage.middleware.operators.rag.evaluate", "ContextRecallEvaluate"),
    "CompressionRateEvaluate": ("sage.middleware.operators.rag.evaluate", "CompressionRateEvaluate"),
    # Document Processing
    "CharacterSplitter": ("sage.middleware.operators.rag.chunk", "CharacterSplitter"),
    "SentenceTransformersTokenTextSplitter": ("sage.middleware.operators.rag.chunk", "SentenceTransformersTokenTextSplitter"),
    "RefinerOperator": ("sage.middleware.operators.rag.refiner", "RefinerOperator"),
    "MemoryWriter": ("sage.middleware.operators.rag.writer", "MemoryWriter"),
    # External Data Sources (may require optional dependencies)
    "ArxivPDFDownloader": ("sage.middleware.operators.rag.arxiv", "ArxivPDFDownloader"),
    "ArxivPDFParser": ("sage.middleware.operators.rag.arxiv", "ArxivPDFParser"),
    # Web Search
    "BochaWebSearch": ("sage.middleware.operators.rag.searcher", "BochaWebSearch"),
}

__all__ = list(_IMPORTS.keys())


def __getattr__(name: str):
    """Lazy import to avoid optional dependency issues at import time."""
    if name in _IMPORTS:
        module_name, attr_name = _IMPORTS[name]
        import importlib
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
