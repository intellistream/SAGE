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

from sage.middleware.operators.rag.arxiv import ArxivPDFDownloader, ArxivPDFParser
from sage.middleware.operators.rag.chunk import (
    CharacterSplitter,
    SentenceTransformersTokenTextSplitter,
)
from sage.middleware.operators.rag.evaluate import (
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
from sage.middleware.operators.rag.generator import HFGenerator, OpenAIGenerator
from sage.middleware.operators.rag.promptor import (
    QAPromptor,
    QueryProfilerPromptor,
    SummarizationPromptor,
)
from sage.middleware.operators.rag.refiner import RefinerOperator
from sage.middleware.operators.rag.reranker import BGEReranker, LLMbased_Reranker
from sage.middleware.operators.rag.retriever import (
    ChromaRetriever,
    MilvusDenseRetriever,
    MilvusSparseRetriever,
    Wiki18FAISSRetriever,
)
from sage.middleware.operators.rag.writer import MemoryWriter

__all__ = [
    # Generators
    "OpenAIGenerator",
    "HFGenerator",
    # Retrievers
    "ChromaRetriever",
    "MilvusDenseRetriever",
    "MilvusSparseRetriever",
    "Wiki18FAISSRetriever",
    # Rerankers
    "BGEReranker",
    "LLMbased_Reranker",
    # Promptors
    "QAPromptor",
    "SummarizationPromptor",
    "QueryProfilerPromptor",
    # Evaluation
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
    # Document Processing
    "CharacterSplitter",
    "SentenceTransformersTokenTextSplitter",
    "RefinerOperator",
    "MemoryWriter",
    # External Data Sources
    "ArxivPDFDownloader",
    "ArxivPDFParser",
]
