"""
Studio Services - Business Logic Layer

提供 Studio 所需的服务，但不包含执行引擎。
所有 Pipeline 执行都委托给 SAGE Engine。
"""

from .agent_orchestrator import AgentOrchestrator, get_orchestrator
from .document_loader import DocumentLoader, load_documents
from .file_upload_service import FileUploadService, get_file_upload_service
from .memory_integration import MemoryIntegrationService, get_memory_service
from .node_registry import NodeRegistry
from .pipeline_builder import PipelineBuilder, get_pipeline_builder
from .stream_handler import SSEFormatter, StreamHandler, get_stream_handler
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
    # Agent Orchestrator
    "AgentOrchestrator",
    "get_orchestrator",
    # Document Loading
    "DocumentLoader",
    "load_documents",
    # File Upload
    "FileUploadService",
    "get_file_upload_service",
    # Node & Pipeline
    "NodeRegistry",
    "PipelineBuilder",
    "get_pipeline_builder",
    # Stream Handler
    "SSEFormatter",
    "StreamHandler",
    "get_stream_handler",
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
    # Memory Integration
    "MemoryIntegrationService",
    "get_memory_service",
]
