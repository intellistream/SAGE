"""
RAG (Retrieval-Augmented Generation) Operators

This module contains domain-specific operators for RAG applications:
- Pipeline (RAG orchestration and workflow)
- Profiler (Query profiling and analysis)
- Document Loaders (Document loading utilities)
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

# Export types for easier access
from sage.libs.rag.types import (
    RAGDocument,
    RAGInput,
    RAGOutput,
    RAGQuery,
    RAGResponse,
    create_rag_response,
    ensure_rag_response,
    extract_query,
    extract_results,
)

# Lazy imports to avoid optional dependency issues
_IMPORTS = {
    # Pipeline and Profiler
    # RAGPipeline lives in the middleware layer (L4) as orchestration/pipeline code.
    # It previously pointed to sage.libs.rag.pipeline (L3) which was deleted during
    # the libs -> middleware refactor. Update to the new location.
    "RAGPipeline": ("sage.middleware.operators.rag.pipeline", "RAGPipeline"),
    "Query_Profiler": ("sage.middleware.operators.rag.profiler", "Query_Profiler"),
    "QueryProfilerResult": ("sage.middleware.operators.rag.profiler", "QueryProfilerResult"),
    # Document Loaders
    "TextLoader": ("sage.libs.rag.document_loaders", "TextLoader"),
    "PDFLoader": ("sage.libs.rag.document_loaders", "PDFLoader"),
    "DocxLoader": ("sage.libs.rag.document_loaders", "DocxLoader"),
    "DocLoader": ("sage.libs.rag.document_loaders", "DocLoader"),
    "MarkdownLoader": ("sage.libs.rag.document_loaders", "MarkdownLoader"),
    "LoaderFactory": ("sage.libs.rag.document_loaders", "LoaderFactory"),
    # Generators
    "OpenAIGenerator": ("sage.middleware.operators.rag.generator", "OpenAIGenerator"),
    "HFGenerator": ("sage.middleware.operators.rag.generator", "HFGenerator"),
    # Retrievers
    "ChromaRetriever": ("sage.middleware.operators.rag.retriever", "ChromaRetriever"),
    "MilvusDenseRetriever": (
        "sage.middleware.operators.rag.retriever",
        "MilvusDenseRetriever",
    ),
    "MilvusSparseRetriever": (
        "sage.middleware.operators.rag.retriever",
        "MilvusSparseRetriever",
    ),
    "Wiki18FAISSRetriever": (
        "sage.middleware.operators.rag.retriever",
        "Wiki18FAISSRetriever",
    ),
    # Rerankers
    "BGEReranker": ("sage.middleware.operators.rag.reranker", "BGEReranker"),
    "LLMbased_Reranker": (
        "sage.middleware.operators.rag.reranker",
        "LLMbased_Reranker",
    ),
    # Promptors
    "QAPromptor": ("sage.middleware.operators.rag.promptor", "QAPromptor"),
    "SummarizationPromptor": (
        "sage.middleware.operators.rag.promptor",
        "SummarizationPromptor",
    ),
    "QueryProfilerPromptor": (
        "sage.middleware.operators.rag.promptor",
        "QueryProfilerPromptor",
    ),
    # Evaluation
    "F1Evaluate": ("sage.middleware.operators.rag.evaluate", "F1Evaluate"),
    "EMEvaluate": ("sage.middleware.operators.rag.evaluate", "EMEvaluate"),
    "RecallEvaluate": ("sage.middleware.operators.rag.evaluate", "RecallEvaluate"),
    "BertRecallEvaluate": (
        "sage.middleware.operators.rag.evaluate",
        "BertRecallEvaluate",
    ),
    "RougeLEvaluate": ("sage.middleware.operators.rag.evaluate", "RougeLEvaluate"),
    "BRSEvaluate": ("sage.middleware.operators.rag.evaluate", "BRSEvaluate"),
    "AccuracyEvaluate": ("sage.middleware.operators.rag.evaluate", "AccuracyEvaluate"),
    "TokenCountEvaluate": (
        "sage.middleware.operators.rag.evaluate",
        "TokenCountEvaluate",
    ),
    "LatencyEvaluate": ("sage.middleware.operators.rag.evaluate", "LatencyEvaluate"),
    "ContextRecallEvaluate": (
        "sage.middleware.operators.rag.evaluate",
        "ContextRecallEvaluate",
    ),
    "CompressionRateEvaluate": (
        "sage.middleware.operators.rag.evaluate",
        "CompressionRateEvaluate",
    ),
    # Document Processing
    "CharacterSplitter": ("sage.libs.rag.chunk", "CharacterSplitter"),
    "SentenceTransformersTokenTextSplitter": (
        "sage.libs.rag.chunk",
        "SentenceTransformersTokenTextSplitter",
    ),
    "RefinerOperator": ("sage.middleware.operators.rag.refiner", "RefinerOperator"),
    "MemoryWriter": ("sage.middleware.operators.rag.writer", "MemoryWriter"),
    # External Data Sources (may require optional dependencies)
    "ArxivPDFDownloader": ("sage.middleware.operators.rag.arxiv", "ArxivPDFDownloader"),
    "ArxivPDFParser": ("sage.middleware.operators.rag.arxiv", "ArxivPDFParser"),
    # Web Search
    "BochaWebSearch": ("sage.middleware.operators.rag.searcher", "BochaWebSearch"),
}

# Export all operator names and type utilities
__all__ = [  # type: ignore[misc]
    # Types
    "RAGDocument",
    "RAGQuery",
    "RAGResponse",
    "RAGInput",
    "RAGOutput",
    "ensure_rag_response",
    "extract_query",
    "extract_results",
    "create_rag_response",
    # Operators (lazy loaded)
    *list(_IMPORTS.keys()),
]


def __getattr__(name: str):
    """Lazy import to avoid optional dependency issues at import time."""
    if name in _IMPORTS:
        module_name, attr_name = _IMPORTS[name]
        import importlib

        module = importlib.import_module(module_name)
        return getattr(module, attr_name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
