from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import FlowProgramRef

SCOPE_ROOT_ID = "scope_root"


@dataclass(frozen=True)
class ExceptionScope:
    scope_id: str
    parent_scope_id: str | None
    handler_target: Any
    depth: int


@dataclass(frozen=True)
class CompiledExceptionScopes:
    root_scope_id: str
    scopes: dict[str, ExceptionScope]
    node_scope_ids: dict[str, str]

    def scope_id_for_node(self, pc_node_id: str) -> str:
        scope_id = self.node_scope_ids.get(pc_node_id)
        if scope_id is None:
            raise KeyError(f"unknown_pc_node_id:{pc_node_id}")
        return scope_id

    def handler_target(self, scope_id: str) -> Any:
        scope = self.scopes.get(scope_id)
        if scope is None:
            raise KeyError(f"unknown_scope_id:{scope_id}")
        return scope.handler_target

    def parent_scope_id(self, scope_id: str) -> str | None:
        scope = self.scopes.get(scope_id)
        if scope is None:
            raise KeyError(f"unknown_scope_id:{scope_id}")
        return scope.parent_scope_id

    def iter_scope_chain(self, start_scope_id: str) -> Iterable[str]:
        seen: set[str] = set()
        scope_id: str | None = start_scope_id
        while scope_id is not None:
            if scope_id in seen:
                raise RuntimeError(f"exception_scope_cycle_detected:{scope_id}")
            seen.add(scope_id)
            yield scope_id
            scope_id = self.parent_scope_id(scope_id)


class ProgramScopeRegistry:
    """Resolve compiled exception scopes by `FlowProgramRef`."""

    def __init__(self):
        self._scopes_by_program_ref: dict[tuple[str, str], CompiledExceptionScopes] = {}

    @staticmethod
    def _key(program_ref: FlowProgramRef) -> tuple[str, str]:
        return (program_ref.program_uri, program_ref.program_rev)

    def register(self, program_ref: FlowProgramRef, scopes: CompiledExceptionScopes) -> None:
        self._scopes_by_program_ref[self._key(program_ref)] = scopes

    def resolve(self, program_ref: FlowProgramRef) -> CompiledExceptionScopes:
        scopes = self._scopes_by_program_ref.get(self._key(program_ref))
        if scopes is None:
            raise KeyError(
                "exception_scopes_not_found:"
                f" program_uri={program_ref.program_uri},"
                f" program_rev={program_ref.program_rev}"
            )
        return scopes


def compile_exception_scopes(flow_program: Any) -> CompiledExceptionScopes:
    transformations = _resolve_transformations(flow_program)
    scopes: dict[str, ExceptionScope] = {
        SCOPE_ROOT_ID: ExceptionScope(
            scope_id=SCOPE_ROOT_ID,
            parent_scope_id=None,
            handler_target=None,
            depth=0,
        )
    }
    node_scope_ids: dict[str, str] = {}
    key_to_scope_id: dict[tuple[str, ...], str] = {(): SCOPE_ROOT_ID}

    for transformation in transformations:
        trans_id = _require_transformation_id(transformation)
        handler_stack = _resolve_handler_stack(transformation)

        current_key: tuple[str, ...] = ()
        current_scope_id = SCOPE_ROOT_ID
        for layer in handler_stack:
            layer_key = _layer_key(layer)
            next_key = current_key + (layer_key,)
            scope_id = key_to_scope_id.get(next_key)
            if scope_id is None:
                scope_id = _scope_id_for_key(next_key)
                scopes[scope_id] = ExceptionScope(
                    scope_id=scope_id,
                    parent_scope_id=current_scope_id,
                    handler_target=layer,
                    depth=len(next_key),
                )
                key_to_scope_id[next_key] = scope_id
            current_scope_id = scope_id
            current_key = next_key

        node_scope_ids[trans_id] = current_scope_id

    return CompiledExceptionScopes(
        root_scope_id=SCOPE_ROOT_ID,
        scopes=scopes,
        node_scope_ids=node_scope_ids,
    )


def _resolve_transformations(flow_program: Any) -> list[Any]:
    transformations_attr = getattr(flow_program, "transformations", None)
    if isinstance(transformations_attr, dict) and transformations_attr:
        return list(transformations_attr.values())

    pipeline_attr = getattr(flow_program, "pipeline", None)
    if isinstance(pipeline_attr, list) and pipeline_attr:
        return list(pipeline_attr)
    return []


def _require_transformation_id(transformation: Any) -> str:
    trans_id = getattr(transformation, "trans_id", None)
    if not isinstance(trans_id, str) or not trans_id.strip():
        raise ValueError("transformation.trans_id must be a non-empty string.")
    return trans_id


def _resolve_handler_stack(transformation: Any) -> list[Any]:
    raw_stack = getattr(transformation, "exception_handler_stack", None)
    if raw_stack is None:
        return []
    if not isinstance(raw_stack, list):
        raise ValueError(
            "transformation.exception_handler_stack must be a list when provided.",
        )
    if raw_stack and raw_stack[0] is None:
        return list(raw_stack[1:])
    return list(raw_stack)


def _scope_id_for_key(key: tuple[str, ...]) -> str:
    digest = hashlib.sha1("||".join(key).encode("utf-8")).hexdigest()
    return f"scope_{digest[:16]}"


def _layer_key(handler: Any) -> str:
    if handler is None:
        return "none"
    if isinstance(handler, dict):
        kind = str(handler.get("kind") or "").strip()
        if kind == "actor_replica_pool_ref":
            symbol_key = str(handler.get("symbol_key") or "").strip()
            method = str(handler.get("method") or "").strip()
            if not symbol_key or not method:
                raise TypeError(
                    "exception handler replica-pool target must provide non-empty symbol_key/method.",
                )
            return f"actor_pool:{symbol_key}:{method}"
        address = handler.get("address")
        actor_id = handler.get("actor_id")
        method = handler.get("method")
        if not all(
            isinstance(value, str) and value.strip() for value in (address, actor_id, method)
        ):
            raise TypeError(
                "exception handler layer must be None, actor dict(address/actor_id/method), "
                "replica-pool target, or object with non-empty address/actor_id/method strings.",
            )
        return f"actor:{address}:{actor_id}:{method}"
    address = getattr(handler, "address", None)
    actor_id = getattr(handler, "actor_id", None)
    method = getattr(handler, "method", None)
    if not all(isinstance(value, str) and value.strip() for value in (address, actor_id, method)):
        raise TypeError(
            "exception handler layer must be None or object with non-empty "
            "address/actor_id/method strings.",
        )
    return f"actor:{address}:{actor_id}:{method}"


__all__ = [
    "SCOPE_ROOT_ID",
    "ExceptionScope",
    "CompiledExceptionScopes",
    "ProgramScopeRegistry",
    "compile_exception_scopes",
]
