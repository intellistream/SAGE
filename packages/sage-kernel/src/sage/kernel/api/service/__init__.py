"""
SAGE Kernel API - Service Layer

Base service interface and Pipeline-as-Service infrastructure.
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
    "PipelineServiceSource",
    "PipelineServiceSink",
]
