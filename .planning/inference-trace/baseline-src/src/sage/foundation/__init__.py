"""SAGE in-tree foundation primitives.

This package is the first step of the main-repo consolidation effort.
It hosts low-churn, high-value building blocks that should remain stable
across runtime, serving, and optional distributed execution modes.
"""

from .config import SagePorts, SageUserPaths, get_user_paths
from .core import (
    BaseCoMapFunction,
    BaseFunction,
    BaseJoinFunction,
    BatchFunction,
    Collector,
    FilterFunction,
    FlatMapFunction,
    FutureFunction,
    KeyByFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
    wrap_lambda,
)
from .debug import PrintSink
from .logging import CustomLogger
from .model_registry import (
    ModelInfo,
    ModelNotFoundError,
    ModelRegistryError,
    delete_model,
    download_model,
    ensure_model_available,
    get_model_path,
    list_models,
    touch_model,
)

__all__ = [
    "SagePorts",
    "SageUserPaths",
    "get_user_paths",
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
    "SinkFunction",
    "SourceFunction",
    "BatchFunction",
    "KeyByFunction",
    "BaseJoinFunction",
    "BaseCoMapFunction",
    "FutureFunction",
    "Collector",
    "wrap_lambda",
    "CustomLogger",
    "PrintSink",
    "ModelInfo",
    "ModelRegistryError",
    "ModelNotFoundError",
    "list_models",
    "download_model",
    "delete_model",
    "get_model_path",
    "touch_model",
    "ensure_model_available",
]
