"""
Core workflow runtime: state management and stage execution.

This module provides the core workflow execution components:
- WorkflowExecutor: Dynamic stage-based workflow execution engine
- State: Workflow state and action tracking
- Operator: Base class for workflow operators
- InstructExecutorOperator: LLM-based instruction execution

Layer: L3 (Core Library)
"""

from .operator import ExecuteSignal, InstructExecutorOperator, Operator
from .state import State
from .workflow import WorkflowExecutor

__all__ = [
    "WorkflowExecutor",
    "State",
    "Operator",
    "InstructExecutorOperator",
    "ExecuteSignal",
]
