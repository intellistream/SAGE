"""
SAGE Kernel API - Service Layer

Base service interface and implementations.
"""

from .base_service import BaseService
from .pipeline_service import (
    PipelineBridge,
    PipelineRequest,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
)

__all__ = [
    "BaseService",
    "PipelineBridge",
    "PipelineRequest",
    "PipelineService",
    "PipelineServiceSink",
    "PipelineServiceSource",
]
