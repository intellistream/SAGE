"""L4 Agentic Operators.

This package exposes ready-to-use operator wrappers (MapOperators) built on
sage.libs.agentic components so Studio and pipeline builders can drag-and-drop
agent runtimes without wiring boilerplate.

Supports engine_type switching for LLM generators:
- sagellm (default): SageLLMGenerator with configurable backend
  - backend_type="auto": Automatically select best available backend
  - backend_type="mock": Mock backend for testing without GPU
  - backend_type="cuda": NVIDIA CUDA backend
  - backend_type="ascend": Huawei Ascend NPU backend
- openai: OpenAIGenerator for OpenAI-compatible APIs
- hf: HFGenerator for HuggingFace models
"""

from .config import (
    AgentRuntimeConfig,
    GeneratorConfig,
    ProfileConfig,
    RuntimeSettings,
)
from .planning_operator import PlanningOperator
from .refined_searcher import RefinedSearcherOperator
from .runtime import AgentRuntimeOperator
from .timing_operator import TimingOperator
from .tool_selection_operator import ToolSelectionOperator

__all__ = [
    # Operators
    "AgentRuntimeOperator",
    "ToolSelectionOperator",
    "PlanningOperator",
    "TimingOperator",
    "RefinedSearcherOperator",
    # Config classes
    "AgentRuntimeConfig",
    "GeneratorConfig",
    "ProfileConfig",
    "RuntimeSettings",
]
