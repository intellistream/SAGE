"""
SAGE Agentic Workflow Framework

Layer: L3 (Core - Research & Algorithm Library)

This module provides a comprehensive framework for researching and developing
both workflow GENERATION and OPTIMIZATION strategies. It enables students and
researchers to experiment with different approaches in a consistent environment.

Architecture:
    - Base abstractions for workflow representation
    - Workflow GENERATORS: Create workflows from user requirements
      * Rule-based generation (keyword matching)
      * LLM-driven generation (intelligent understanding)
      * Template-based generation
      * Hybrid approaches
    - Workflow OPTIMIZERS: Optimize existing workflows
      * Cost optimization
      * Latency optimization
      * Quality optimization
    - Evaluation metrics and benchmarking tools

Two-Phase Workflow:
    User Input → [GENERATION] → Initial Workflow → [OPTIMIZATION] → Final Workflow

Generation Example:
    >>> from sage.libs.agentic.workflow import GenerationContext
    >>> from sage.libs.agentic.workflow.generators import LLMWorkflowGenerator
    >>>
    >>> # Generate workflow from natural language
    >>> generator = LLMWorkflowGenerator(model="gpt-4")
    >>> context = GenerationContext(
    ...     user_input="Create a RAG pipeline for document Q&A",
    ...     constraints={"max_cost": 100, "max_latency": 5.0}
    ... )
    >>> result = generator.generate(context)
    >>> workflow = result.visual_pipeline

Optimization Example:
    >>> from sage.libs.agentic.workflow import WorkflowGraph
    >>> from sage.libs.agentic.workflow.optimizers import GreedyOptimizer
    >>>
    >>> # Optimize an existing workflow
    >>> workflow = WorkflowGraph()
    >>> workflow.add_node("analyzer", cost=10, quality=0.8)
    >>> workflow.add_node("generator", cost=20, quality=0.9)
    >>> workflow.add_edge("analyzer", "generator")
    >>>
    >>> optimizer = GreedyOptimizer()
    >>> optimized = optimizer.optimize(workflow, constraints={"max_cost": 25})
    >>> print(f"Cost saved: ${workflow.total_cost() - optimized.total_cost()}")
"""

# Optimization (existing)
from .base import (
    BaseOptimizer,
    NodeType,
    OptimizationMetrics,
    OptimizationResult,
    WorkflowGraph,
    WorkflowNode,
)
from .constraints import (
    BudgetConstraint,
    ConstraintChecker,
    LatencyConstraint,
    QualityConstraint,
)
from .evaluator import WorkflowEvaluator

# Generation (new)
from .generators import (
    BaseWorkflowGenerator,
    GenerationContext,
    GenerationResult,
    GenerationStrategy,
    LLMWorkflowGenerator,
    RuleBasedWorkflowGenerator,
)

__all__ = [
    # === Workflow Generation ===
    "BaseWorkflowGenerator",
    "GenerationResult",
    "GenerationContext",
    "GenerationStrategy",
    # Generators
    "RuleBasedWorkflowGenerator",
    "LLMWorkflowGenerator",
    # === Workflow Optimization ===
    # Core abstractions
    "WorkflowGraph",
    "WorkflowNode",
    "NodeType",
    "BaseOptimizer",
    "OptimizationResult",
    "OptimizationMetrics",
    # Constraints
    "ConstraintChecker",
    "BudgetConstraint",
    "LatencyConstraint",
    "QualityConstraint",
    # Evaluation
    "WorkflowEvaluator",
]

# Version info
__version__ = "0.2.0"  # Bumped for generation support
__author__ = "SAGE Team"
