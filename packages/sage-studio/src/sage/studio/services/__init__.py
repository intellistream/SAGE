"""
Studio Services - Business Logic Layer

提供 Studio 所需的服务，但不包含执行引擎。
所有 Pipeline 执行都委托给 SAGE Engine。
"""

from .chat_pipeline_recommender import generate_pipeline_recommendation
from .node_registry import NodeRegistry
from .pipeline_builder import PipelineBuilder, get_pipeline_builder

__all__ = [
    "NodeRegistry",
    "PipelineBuilder",
    "get_pipeline_builder",
    "generate_pipeline_recommendation",
]
