from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import EventCursor, FlowProgramRef
from sage.runtime.flownet.runtime.flowengine.exception_decision import (
    ExceptionDecisionEnvelope,
    normalize_exception_decision,
)
from sage.runtime.flownet.runtime.flowengine.scope_resolver import CompiledExceptionScopes


@dataclass(frozen=True)
class ExceptionResolutionResult:
    handled: bool
    decision: ExceptionDecisionEnvelope | None
    resolved_scope_id: str | None
    resolved_frame_depth: int | None
    resolved_program_ref: FlowProgramRef | None
    resolved_pc_node_id: str | None


async def resolve_exception_for_cursor(
    *,
    cursor: EventCursor,
    event: dict[str, Any],
    resolve_scopes: Callable[[FlowProgramRef], CompiledExceptionScopes],
    invoke_handler: Callable[[Any, dict[str, Any]], Any | Awaitable[Any]],
) -> ExceptionResolutionResult:
    frame_contexts: list[tuple[int, FlowProgramRef, str]] = [
        (0, cursor.flow_program_ref, cursor.pc_node_id),
    ]
    for depth, frame in enumerate(reversed(cursor.flow_stack), start=1):
        frame_contexts.append((depth, frame.resume_flow_program_ref, frame.callsite_pc_node_id))

    for frame_depth, program_ref, pc_node_id in frame_contexts:
        scopes = resolve_scopes(program_ref)
        start_scope_id = scopes.scope_id_for_node(pc_node_id)

        for scope_id in scopes.iter_scope_chain(start_scope_id):
            handler_target = scopes.handler_target(scope_id)
            if handler_target is None:
                continue

            raw_decision = invoke_handler(handler_target, event)
            if inspect.isawaitable(raw_decision):
                raw_decision = await raw_decision

            decision = normalize_exception_decision(raw_decision)

            if decision is None or decision.action == "propagate":
                continue

            return ExceptionResolutionResult(
                handled=True,
                decision=decision,
                resolved_scope_id=scope_id,
                resolved_frame_depth=frame_depth,
                resolved_program_ref=program_ref,
                resolved_pc_node_id=pc_node_id,
            )

    return ExceptionResolutionResult(
        handled=False,
        decision=None,
        resolved_scope_id=None,
        resolved_frame_depth=None,
        resolved_program_ref=None,
        resolved_pc_node_id=None,
    )


def resolve_exception_for_cursor_sync(
    *,
    cursor: EventCursor,
    event: dict[str, Any],
    resolve_scopes: Callable[[FlowProgramRef], CompiledExceptionScopes],
    invoke_handler: Callable[[Any, dict[str, Any]], Any],
) -> ExceptionResolutionResult:
    frame_contexts: list[tuple[int, FlowProgramRef, str]] = [
        (0, cursor.flow_program_ref, cursor.pc_node_id),
    ]
    for depth, frame in enumerate(reversed(cursor.flow_stack), start=1):
        frame_contexts.append((depth, frame.resume_flow_program_ref, frame.callsite_pc_node_id))

    for frame_depth, program_ref, pc_node_id in frame_contexts:
        scopes = resolve_scopes(program_ref)
        start_scope_id = scopes.scope_id_for_node(pc_node_id)

        for scope_id in scopes.iter_scope_chain(start_scope_id):
            handler_target = scopes.handler_target(scope_id)
            if handler_target is None:
                continue

            raw_decision = invoke_handler(handler_target, event)
            if inspect.isawaitable(raw_decision):
                raise TypeError(
                    "sync_exception_handler_must_not_return_awaitable",
                )

            decision = normalize_exception_decision(raw_decision)

            if decision is None or decision.action == "propagate":
                continue

            return ExceptionResolutionResult(
                handled=True,
                decision=decision,
                resolved_scope_id=scope_id,
                resolved_frame_depth=frame_depth,
                resolved_program_ref=program_ref,
                resolved_pc_node_id=pc_node_id,
            )

    return ExceptionResolutionResult(
        handled=False,
        decision=None,
        resolved_scope_id=None,
        resolved_frame_depth=None,
        resolved_program_ref=None,
        resolved_pc_node_id=None,
    )


__all__ = [
    "ExceptionResolutionResult",
    "resolve_exception_for_cursor",
    "resolve_exception_for_cursor_sync",
]
