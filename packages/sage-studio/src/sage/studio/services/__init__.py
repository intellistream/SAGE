"""
Studio Services - Business Logic Layer

提供 Studio 所需的服务，但不包含执行引擎。
所有 Pipeline 执行都委托给 SAGE Engine。
"""

from .document_loader import DocumentLoader, load_documents
from .intent_classifier import (
    IntentResult,
    KnowledgeDomain,
    UserIntent,
    get_domain_display_name,
    get_intent_display_name,
)
from .node_registry import NodeRegistry
from .pipeline_builder import PipelineBuilder, get_pipeline_builder
from .vector_store import (
    DocumentChunk,
    SearchResult,
    VectorStore,
    create_vector_store,
)
from .workflow_generator import (
    WorkflowGenerationRequest,
    WorkflowGenerationResult,
    WorkflowGenerator,
    generate_workflow_from_chat,
)

__all__ = [
    # Document Loading
    "DocumentLoader",
    "load_documents",
    # Intent Classification
    "IntentResult",
    "KnowledgeDomain",
    "UserIntent",
    "get_domain_display_name",
    "get_intent_display_name",
    # Node & Pipeline
    "NodeRegistry",
    "PipelineBuilder",
    "get_pipeline_builder",
    # Workflow Generation
    "WorkflowGenerator",
    "WorkflowGenerationRequest",
    "WorkflowGenerationResult",
    "generate_workflow_from_chat",
    # Vector Store
    "DocumentChunk",
    "SearchResult",
    "VectorStore",
    "create_vector_store",
]
