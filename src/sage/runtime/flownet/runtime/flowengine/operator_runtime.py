"""Compatibility facade for flowengine operator runtime exports.

The implementation has moved to ``flownet.runtime.operator_runtime``.
This module remains as a thin routing layer to preserve existing import paths.
"""

from __future__ import annotations

from sage.runtime.flownet.runtime.operator_runtime import (
    CollectiveContractError,
    CollectiveRuntime,
    FlatMapContinuationRuntime,
    FlatMapContractError,
    JoinContractError,
    JoinReducerRuntime,
    LoopGateEvaluation,
    LoopOperatorContractError,
    LoopStepEvaluation,
    MergeReducerContractError,
    MergeReducerRuntime,
    OperatorEvaluation,
    OperatorExecutionError,
    ProcessTargetResolutionError,
    ReducerContractError,
    ReducerRuntime,
    ShuffleOperatorContractError,
    StatefulProcessContractError,
    StatefulProcessRuntime,
    StatefulStateHandle,
    UnsupportedOperatorTypeError,
    evaluate_loop_gate,
    evaluate_loop_step,
    evaluate_loop_step_from_directives,
    evaluate_operator,
    resolve_loop_body_program_ref,
)

__all__ = [
    "OperatorEvaluation",
    "LoopStepEvaluation",
    "LoopGateEvaluation",
    "OperatorExecutionError",
    "UnsupportedOperatorTypeError",
    "ProcessTargetResolutionError",
    "FlatMapContractError",
    "ReducerContractError",
    "JoinContractError",
    "MergeReducerContractError",
    "CollectiveContractError",
    "ReducerRuntime",
    "JoinReducerRuntime",
    "MergeReducerRuntime",
    "CollectiveRuntime",
    "LoopOperatorContractError",
    "ShuffleOperatorContractError",
    "StatefulProcessContractError",
    "StatefulProcessRuntime",
    "FlatMapContinuationRuntime",
    "StatefulStateHandle",
    "evaluate_loop_step",
    "evaluate_loop_gate",
    "evaluate_loop_step_from_directives",
    "resolve_loop_body_program_ref",
    "evaluate_operator",
]
