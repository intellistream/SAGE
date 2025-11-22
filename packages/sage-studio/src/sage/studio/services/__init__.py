"""
Studio Services - Business Logic Layer

提供 Studio 所需的服务，但不包含执行引擎。
所有 Pipeline 执行都委托给 SAGE Engine。
"""

from .node_registry import NodeRegistry
from .pipeline_builder import PipelineBuilder, get_pipeline_builder
from .workflow_generator import (
    WorkflowGenerationRequest,
    WorkflowGenerationResult,
    WorkflowGenerator,
    generate_workflow_from_chat,
)

__all__ = [
    "NodeRegistry",
    "PipelineBuilder",
    "get_pipeline_builder",
    # Workflow Generation
    "WorkflowGenerator",
    "WorkflowGenerationRequest",
    "WorkflowGenerationResult",
    "generate_workflow_from_chat",
]
