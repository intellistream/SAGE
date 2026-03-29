from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sage.runtime.flownet.compiler.errors import FlowDefinitionError
from sage.runtime.flownet.compiler.targets import (
    coerce_actor_symbol_target,
    coerce_flow_program_ref_target,
    coerce_flow_symbol_target,
    coerce_stateless_symbol_target,
    is_actor_symbol_target,
    is_actor_target,
    is_flow_symbol_target,
    is_stateless_symbol_target,
    is_stateless_target,
)

if TYPE_CHECKING:
    from sage.runtime.flownet.core.flow_program import FlowProgram


class Transformation:
    def __init__(
        self,
        flow_program: FlowProgram,
        target: Any,
        type: str = "map",
        *,
        operator_key: str | None = None,
        operator_config: dict[str, Any] | None = None,
    ):
        self.trans_id = uuid.uuid4().hex
        self.flow_program: FlowProgram = flow_program
        self.type = str(type)
        self.operator_key: str | None = operator_key
        self.operator_config: dict[str, Any] | None = operator_config
        self.target = target

        self.upstreams: list[Transformation] = []
        self.downstreams: list[Transformation] = []
        self.is_sink: bool = False
        self.is_return: bool = False
        self.pipe_flow: Any | None = None
        self.exception_handler_stack: list[Any | None] = []

        self._validate_target()
        self._validate_operator_key()
        self._validate_operator_config()

    def _validate_target(self) -> None:
        if is_actor_target(self.target) or is_stateless_target(self.target):
            return
        if is_actor_symbol_target(self.target):
            normalized_actor_symbol = coerce_actor_symbol_target(self.target)
            if normalized_actor_symbol is None:
                raise FlowDefinitionError("actor symbol target normalization failed.")
            self.target = normalized_actor_symbol
            return
        if is_stateless_symbol_target(self.target):
            normalized_stateless_symbol = coerce_stateless_symbol_target(self.target)
            if normalized_stateless_symbol is None:
                raise FlowDefinitionError("stateless symbol target normalization failed.")
            self.target = normalized_stateless_symbol
            return
        if is_flow_symbol_target(self.target):
            normalized_flow_symbol = coerce_flow_symbol_target(self.target)
            if normalized_flow_symbol is None:
                raise FlowDefinitionError("flow symbol target normalization failed.")
            self.target = normalized_flow_symbol
            return
        normalized_program_ref = coerce_flow_program_ref_target(self.target)
        if normalized_program_ref is not None:
            # Canonicalize legacy flow_uri/version style refs on compile boundary.
            self.target = normalized_program_ref
            return
        raise FlowDefinitionError(
            "Flow graph accepts actor/stateless/symbolic actor|stateless|flow targets or canonical flow-program refs.",
        )

    def _validate_operator_key(self) -> None:
        if self.operator_key is None:
            return
        if not isinstance(self.operator_key, str) or not self.operator_key.strip():
            raise ValueError("operator_key must be a non-empty string when provided.")

    def _validate_operator_config(self) -> None:
        if self.operator_config is None:
            return
        if not isinstance(self.operator_config, dict):
            raise ValueError("operator_config must be a dict when provided.")

    def add_upstream(self, upstream_trans: Transformation) -> None:
        self.upstreams.append(upstream_trans)
        upstream_trans.downstreams.append(self)


__all__ = [
    "Transformation",
]
