from __future__ import annotations


class OperatorExecutionError(RuntimeError):
    """Raised when operator runtime semantics cannot be evaluated."""


class UnsupportedOperatorTypeError(OperatorExecutionError):
    """Raised when operator type is not supported by the v1 runtime slice."""


class ProcessTargetResolutionError(OperatorExecutionError):
    """Raised when process operator cannot resolve a child FlowProgramRef."""


class StatefulProcessContractError(OperatorExecutionError):
    """Raised when sys/stateful-process violates the minimal runtime contract."""


class ShuffleOperatorContractError(OperatorExecutionError):
    """Raised when sys/shuffle violates the minimal runtime contract."""


class LoopOperatorContractError(OperatorExecutionError):
    """Raised when sys/loop violates the minimal runtime contract."""


class FlatMapContractError(OperatorExecutionError):
    """Raised when flatmap violates the frozen v1 incremental contract."""


class ReducerContractError(OperatorExecutionError):
    """Raised when sys/reducer violates the frozen v1 reducer contract."""


class JoinContractError(ReducerContractError):
    """Raised when join/join-reducer violates the frozen v1 join contract."""


class MergeReducerContractError(ReducerContractError):
    """Raised when sys/merge-reducer violates the frozen v1 merge contract."""


class CollectiveContractError(OperatorExecutionError):
    """Raised when sys/collective violates the frozen v1 collective contract."""


__all__ = [
    "OperatorExecutionError",
    "UnsupportedOperatorTypeError",
    "ProcessTargetResolutionError",
    "StatefulProcessContractError",
    "ShuffleOperatorContractError",
    "LoopOperatorContractError",
    "FlatMapContractError",
    "ReducerContractError",
    "JoinContractError",
    "MergeReducerContractError",
    "CollectiveContractError",
]
