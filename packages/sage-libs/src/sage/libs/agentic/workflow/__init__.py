"""
SAGE Agentic Workflow Optimizer Framework

Layer: L3 (Core - Research & Algorithm Library)

This module provides a standardized framework for researching and developing
optimization strategies for agentic workflows. It enables students and researchers
to experiment with different optimization approaches in a consistent environment.

Architecture:
    - Base abstractions for workflow representation
    - Pluggable optimizer interface
    - Evaluation metrics and benchmarking tools
    - Example optimizers for reference

Usage Example:
    >>> from sage.libs.agentic.workflow import WorkflowGraph, BaseOptimizer
    >>> from sage.libs.agentic.workflow.optimizers import GreedyOptimizer
    >>>
    >>> # Define your workflow
    >>> workflow = WorkflowGraph()
    >>> workflow.add_agent("analyzer", cost=10, quality=0.8)
    >>> workflow.add_agent("generator", cost=20, quality=0.9)
    >>> workflow.add_dependency("analyzer", "generator")
    >>>
    >>> # Apply optimizer
    >>> optimizer = GreedyOptimizer()
    >>> optimized = optimizer.optimize(workflow, constraints={"max_cost": 50})
    >>>
    >>> # Evaluate results
    >>> metrics = optimizer.evaluate(workflow, optimized)
    >>> print(f"Cost reduction: {metrics.cost_reduction}%")
"""

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

__all__ = [
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
__version__ = "0.1.0"
__author__ = "SAGE Team"
