from __future__ import annotations

from typing import Any

from sage.runtime.flownet.api.declarations import (
    BoundFlowDeclaration,
    BoundFlowTemplate,
    FlowDeclaration,
    NamedFlowDeclarationRef,
)
from sage.runtime.flownet.compiler.errors import FlowDefinitionError
from sage.runtime.flownet.compiler.exception_scope import flow_program_scope
from sage.runtime.flownet.compiler.streams import ConnectedStreams, DataStream, SinkStream
from sage.runtime.flownet.core import FlowProgram


def compile_flow_program(flow_dsl: Any) -> FlowProgram:
    if isinstance(flow_dsl, FlowProgram):
        return flow_dsl
    if isinstance(flow_dsl, BoundFlowTemplate):
        return flow_dsl.bind().flow_program
    if isinstance(flow_dsl, BoundFlowDeclaration):
        return flow_dsl.flow_program
    if isinstance(flow_dsl, NamedFlowDeclarationRef):
        return flow_dsl.declaration.compile()
    if isinstance(flow_dsl, FlowDeclaration):
        return flow_dsl.compile()
    flowfunction = _resolve_flow_callable(flow_dsl)
    return _compile_program(flowfunction)


def _resolve_flow_callable(flow_dsl: Any) -> Any:
    if callable(flow_dsl):
        return flow_dsl

    raise TypeError(
        "compile_flow_program() expects a callable flow DSL, v1 FlowProgram, "
        "FlowDeclaration, BoundFlowTemplate, BoundFlowDeclaration, or NamedFlowDeclarationRef.",
    )


def _compile_program(flowfunction: Any) -> FlowProgram:
    program = FlowProgram()
    init_stream = DataStream(program, transformation=None, init=True)

    with flow_program_scope(program):
        output = flowfunction(init_stream)

    if output is None:
        program.no_return = True
    elif isinstance(output, SinkStream):
        program.no_return = True
    elif isinstance(output, ConnectedStreams):
        output.set_return()
    elif isinstance(output, DataStream):
        output.set_return()
    else:
        raise FlowDefinitionError(
            f"Flow must return DataStream/ConnectedStreams/SinkStream/None, got {type(output)}"
        )

    return program


__all__ = [
    "compile_flow_program",
]
