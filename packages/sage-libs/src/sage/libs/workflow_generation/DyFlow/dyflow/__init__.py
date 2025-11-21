"""
DyFlow - Dynamic Workflow Generation and Execution

Layer: L3 (Core - Algorithm Library)
Dependencies: sage.common (L1)

DyFlow provides dynamic workflow generation and execution capabilities using LLMs.
It enables AI agents to design and execute multi-stage workflows adaptively based on
problem requirements and execution feedback.

Key Components:
---------------
- WorkflowExecutor: Main workflow execution engine
- State: Workflow state management
- ModelService: LLM integration service
- Operator: Base operator for workflow actions

Architecture:
- Dynamic stage design using Designer LLM
- Flexible operator-based execution
- State management with action tracking
- Multi-model support (OpenAI, Anthropic, Local)

Example:
    >>> from sage.libs.workflow_generation.DyFlow.dyflow import WorkflowExecutor, ModelService
    >>>
    >>> designer = ModelService.create(model='gpt-4o')
    >>> executor = ModelService.create(model='gpt-3.5-turbo')
    >>>
    >>> workflow = WorkflowExecutor(
    ...     problem_description="Solve 2x + 5 = 13",
    ...     designer_service=designer,
    ...     executor_service=executor
    ... )
    >>>
    >>> result = workflow.execute()
    >>> print(result)

Reference:
----------
Based on dynamic workflow generation research and adaptive agent systems.
"""

__layer__ = "L3"

from .core.operator import ExecuteSignal, InstructExecutorOperator, Operator
from .core.state import State
from .core.workflow import WorkflowExecutor
from .llms.clients import ExecutorLLMClient
from .model_service.model_service import ModelService

__all__ = [
    "WorkflowExecutor",
    "State",
    "ModelService",
    "Operator",
    "InstructExecutorOperator",
    "ExecuteSignal",
    "ExecutorLLMClient",
]

__version__ = "0.1.0"
__author__ = "DyFlow Contributors"
