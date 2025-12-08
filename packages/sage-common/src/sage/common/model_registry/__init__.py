"""Model registry helpers for SAGE components.

Layer: L1 (Foundation - Common Model Registry)

This module provides model management utilities for ML models used in SAGE,
particularly for vLLM model registry and management.

Architecture:
    This is a L1 foundation component providing model registry services.
    Used by components like sage_llm for model lifecycle management.
"""

from .recommended import fetch_recommended_models
from .vllm_registry import (
    ModelInfo,
    delete_model,
    download_model,
    ensure_model_available,
    get_model_path,
    list_models,
    touch_model,
)

__all__ = [
    "ModelInfo",
    "list_models",
    "download_model",
    "delete_model",
    "get_model_path",
    "touch_model",
    "ensure_model_available",
    "fetch_recommended_models",
]
