"""Runtime-first public API for SAGE.

SAGE is stream-first, but environments and job orchestration remain the
execution surface that turns declarative flow definitions into runnable jobs.

This package provides the preferred main-repo import path while implementation
ownership is migrated inward in stages.
"""

from __future__ import annotations

from typing import Any

from sage.stream._runtime_kernel_types import Packet, StopSignal

from .backend import get_runtime_backend
from .environments import FlowNetEnvironment, LocalEnvironment
from .job_manager import JobManager
from .pipeline_compiler import CompiledActorGraph, PipelineCompiler
from .scheduler import (
    BaseScheduler,
    FIFOScheduler,
    LoadAwareScheduler,
    NodeSelector,
    PlacementDecision,
)
from .service import BaseService

__all__ = [
    "LocalEnvironment",
    "FlowNetEnvironment",
    "BaseScheduler",
    "FIFOScheduler",
    "LoadAwareScheduler",
    "NodeSelector",
    "PlacementDecision",
    "BaseService",
    "StopSignal",
    "Packet",
    "JobManager",
    "get_runtime_backend",
    "PipelineCompiler",
    "CompiledActorGraph",
]


def __getattr__(name: str) -> Any:
    if name == "BaseService":
        return BaseService
    if name == "BaseScheduler":
        return BaseScheduler
    if name == "FIFOScheduler":
        return FIFOScheduler
    if name == "LoadAwareScheduler":
        return LoadAwareScheduler
    if name == "NodeSelector":
        return NodeSelector
    if name == "PlacementDecision":
        return PlacementDecision
    if name == "StopSignal":
        return StopSignal
    if name == "Packet":
        return Packet
    if name == "JobManager":
        return JobManager
    if name == "PipelineCompiler":
        return PipelineCompiler
    if name == "CompiledActorGraph":
        return CompiledActorGraph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
