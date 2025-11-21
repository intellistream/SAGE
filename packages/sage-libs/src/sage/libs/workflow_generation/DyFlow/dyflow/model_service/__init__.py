"""
Model service: LLM integration and management.

This module provides unified LLM service abstraction supporting:
- OpenAI models (GPT-4, GPT-3.5-turbo, etc.)
- Anthropic models (Claude-3, Claude-2, etc.)
- Local models (via custom endpoints)

Features:
- Shared client management for efficiency
- Token usage and cost tracking
- Async support for concurrent requests
- Unified API across different providers

Layer: L3 (Core Library)
"""

from .config import get_available_models
from .model_service import ModelService

__all__ = [
    "ModelService",
    "get_available_models",
]
