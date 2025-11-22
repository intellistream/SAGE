"""
Workflow Generators - 工作流生成算法

Layer: L3 (Core - Research & Algorithm Library)

This module provides different strategies for generating workflows from
user requirements. It complements the optimization module by focusing on
the initial workflow creation phase.

Architecture:
    - Base generator interface
    - Multiple generation strategies:
      * Rule-based (simple intent detection)
      * LLM-driven (using language models)
      * Hybrid (combining multiple approaches)
      * Template-based (using predefined patterns)

Research Focus:
    Students can implement and compare different workflow generation
    algorithms, studying trade-offs between:
    - Accuracy of intent understanding
    - Quality of generated workflows
    - Generation speed
    - Resource requirements

Usage Example:
    >>> from sage.libs.agentic.workflow.generators import LLMWorkflowGenerator
    >>>
    >>> # Create generator
    >>> generator = LLMWorkflowGenerator(model="gpt-4")
    >>>
    >>> # Generate workflow from natural language
    >>> result = generator.generate(
    ...     user_input="Create a RAG pipeline for document Q&A",
    ...     context={"domain": "documentation"}
    ... )
    >>>
    >>> # Get workflow graph
    >>> workflow = result.workflow_graph
    >>> visual_config = result.visual_pipeline
"""

from .base import (
    BaseWorkflowGenerator,
    GenerationContext,
    GenerationResult,
    GenerationStrategy,
)
from .llm_generator import LLMWorkflowGenerator
from .rule_based_generator import RuleBasedWorkflowGenerator

__all__ = [
    # Base abstractions
    "BaseWorkflowGenerator",
    "GenerationResult",
    "GenerationContext",
    "GenerationStrategy",
    # Concrete generators
    "RuleBasedWorkflowGenerator",
    "LLMWorkflowGenerator",
]

__version__ = "0.1.0"
