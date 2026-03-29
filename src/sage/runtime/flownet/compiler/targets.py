from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.api.declarations import (
    ActorDeclaration,
    ActorMethodSymbolRef,
    BoundActorDeclaration,
    BoundFlowDeclaration,
    BoundFlowTemplate,
    FlowDeclaration,
    NamedFlowDeclarationRef,
    StatelessDeclaration,
)
from sage.runtime.flownet.compiler.errors import FlowDefinitionError
from sage.runtime.flownet.core import FlowProgram


@dataclass(frozen=True)
class SystemTargetRef:
    address: str = "__local__"
    actor_id: str = "__system__"
    method: str = "noop"


def system_target() -> SystemTargetRef:
    return SystemTargetRef()


def ensure_flow_target(
    target: Any,
    op: str,
    *,
    allow_flow_program_ref: bool = False,
    require_bound_flow_ref: bool = False,
) -> Any:
    normalized_actor_symbol = coerce_actor_symbol_target(target)
    if normalized_actor_symbol is not None:
        return normalized_actor_symbol
    normalized_stateless_symbol = coerce_stateless_symbol_target(target)
    if normalized_stateless_symbol is not None:
        return normalized_stateless_symbol
    if is_actor_target(target) or is_stateless_target(target):
        return target
    if allow_flow_program_ref:
        normalized_flow_symbol = coerce_flow_symbol_target(target)
        if normalized_flow_symbol is not None:
            if require_bound_flow_ref and normalized_flow_symbol.get("binding_mode") == "unbound":
                raise FlowDefinitionError(
                    f"{op}() requires a bound flow reference (FlowDecl(...)(...) or FlowDecl(...).bind(...)) "
                    "or a named flow reference (FlowDecl.find/locate). "
                    "Unbound flow template/program is not allowed.",
                )
            return normalized_flow_symbol
        normalized_program_ref = coerce_flow_program_ref_target(target)
        if normalized_program_ref is not None:
            return normalized_program_ref

    raise FlowDefinitionError(
        f"{op}() expects actor/stateless target or symbolic actor/stateless target"
        + (" or flow-program/symbolic-flow reference target." if allow_flow_program_ref else ".")
        + " Actor-like target must provide address/actor_id/method, or use bound/named actor symbol refs."
    )


def coerce_actor_symbol_target(target: Any) -> dict[str, Any] | None:
    if isinstance(target, ActorMethodSymbolRef):
        if str(getattr(target, "origin", "")).strip().lower() == "unbound":
            raise FlowDefinitionError(
                "unbound actor declaration method reference is not allowed in flow targets."
                " Use ActorDeclaration(...).method (for example `_Worker().advance`) or named refs (`find/locate`).",
            )
        return _coerce_declaration_symbol_ref(
            declaration=target.declaration,
            method=target.method,
            bind_args=target.bind_args,
            bind_kwargs=target.bind_kwargs,
            name=target.name,
            namespace=target.namespace,
            selector=target.selector,
            materialization_policy_override=target.materialization_policy_override,
        )
    if isinstance(target, ActorDeclaration):
        raise FlowDefinitionError(
            "unbound actor declaration is not allowed in flow targets."
            " Use ActorDeclaration() default method binding (for example `_Worker()`)"
            " or explicit ActorDeclaration(...).method (for example `_Worker().advance`).",
        )
    if isinstance(target, BoundActorDeclaration):
        try:
            default_method_name = target.declaration.default_method_name()
        except Exception as exc:
            raise FlowDefinitionError(str(exc)) from exc
        return _coerce_declaration_symbol_ref(
            declaration=target.declaration,
            method=default_method_name,
            bind_args=target.bind_args,
            bind_kwargs=target.bind_kwargs,
            name=target.name,
            namespace=target.namespace,
            selector=target.selector,
            materialization_policy_override=target.materialization_policy_override,
        )
    kind = _non_empty_str(_field(target, "kind"))
    if kind != "actor_symbol_ref":
        return None
    actor_uri = _non_empty_str(_field(target, "actor_uri"))
    method = _non_empty_str(_field(target, "method"))
    if actor_uri is None or method is None:
        raise FlowDefinitionError(
            "actor symbol target requires non-empty kind/actor_uri/method fields.",
        )
    declaration = _field(target, "declaration")
    if declaration is not None and not isinstance(declaration, ActorDeclaration):
        raise FlowDefinitionError(
            "actor symbol target declaration must be ActorDeclaration when provided."
        )
    normalized: dict[str, Any] = {
        "kind": "actor_symbol_ref",
        "actor_uri": actor_uri,
        "method": method,
    }
    bind_value = _field(target, "bind")
    if bind_value is not None:
        normalized["bind"] = bind_value
    for passthrough in ("name", "namespace", "selector"):
        value = _field(target, passthrough)
        if value is not None:
            normalized[passthrough] = value
    materialization_policy_override = _field(target, "materialization_policy_override")
    if materialization_policy_override is not None:
        if not isinstance(materialization_policy_override, Mapping):
            raise FlowDefinitionError(
                "actor symbol target materialization_policy_override must be a mapping."
            )
        normalized["materialization_policy_override"] = dict(materialization_policy_override)
    if declaration is not None:
        normalized["declaration"] = declaration
    return normalized


def _coerce_declaration_symbol_ref(
    *,
    declaration: ActorDeclaration,
    method: str,
    bind_args: tuple[Any, ...] = (),
    bind_kwargs: Mapping[str, Any] | None = None,
    name: str | None = None,
    namespace: str | None = None,
    selector: str | None = None,
    materialization_policy_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    actor_uri = _non_empty_str(getattr(declaration, "uri", None))
    if actor_uri is None:
        raise FlowDefinitionError("actor symbol target requires actor declaration uri.")
    normalized_method = _non_empty_str(method)
    if normalized_method is None:
        raise FlowDefinitionError("actor symbol target requires non-empty method.")
    normalized: dict[str, Any] = {
        "kind": "actor_symbol_ref",
        "actor_uri": actor_uri,
        "method": normalized_method,
        "declaration": declaration,
    }
    if bind_args or bind_kwargs or (name is None and selector is None):
        normalized["bind"] = {
            "args": list(bind_args),
            "kwargs": dict(bind_kwargs or {}),
        }
    if name is not None:
        normalized["name"] = str(name).strip()
    if namespace is not None:
        normalized["namespace"] = str(namespace).strip()
    if selector is not None:
        normalized["selector"] = str(selector).strip()
    if materialization_policy_override:
        normalized["materialization_policy_override"] = dict(materialization_policy_override)
    return normalized


def coerce_flow_program_ref_target(target: Any) -> dict[str, str] | None:
    program_uri = _non_empty_str(_field(target, "program_uri"))
    program_rev = _non_empty_str(_field(target, "program_rev"))
    if program_uri is not None and program_rev is not None:
        return {
            "program_uri": program_uri,
            "program_rev": program_rev,
        }

    # Temporary compatibility bridge: normalize legacy names when provided.
    flow_uri = _non_empty_str(_field(target, "flow_uri"))
    version = _non_empty_str(_field(target, "version"))
    if flow_uri is not None and version is not None:
        return {
            "program_uri": flow_uri,
            "program_rev": version,
        }
    return None


def coerce_stateless_symbol_target(target: Any) -> dict[str, Any] | None:
    if isinstance(target, StatelessDeclaration):
        return _coerce_stateless_declaration_symbol_ref(declaration=target)

    kind = _non_empty_str(_field(target, "kind"))
    if kind != "stateless_symbol_ref":
        return None

    op_uri = _non_empty_str(_field(target, "op_uri"))
    if op_uri is None:
        raise FlowDefinitionError("stateless symbol target requires non-empty kind/op_uri fields.")

    scope = _non_empty_str(_field(target, "scope")) or "global"
    declaration = _field(target, "declaration")
    if declaration is not None and not isinstance(declaration, StatelessDeclaration):
        raise FlowDefinitionError(
            "stateless symbol target declaration must be StatelessDeclaration when provided.",
        )

    normalized: dict[str, Any] = {
        "kind": "stateless_symbol_ref",
        "op_uri": op_uri,
        "scope": scope,
    }
    if declaration is not None:
        normalized["declaration"] = declaration
    return normalized


def _coerce_stateless_declaration_symbol_ref(
    *,
    declaration: StatelessDeclaration,
) -> dict[str, Any]:
    op_uri = _non_empty_str(getattr(declaration, "uri", None))
    if op_uri is None:
        raise FlowDefinitionError("stateless symbol target requires declaration uri.")
    return {
        "kind": "stateless_symbol_ref",
        "op_uri": op_uri,
        "scope": "global",
        "declaration": declaration,
    }


def coerce_flow_symbol_target(target: Any) -> dict[str, Any] | None:
    if isinstance(target, BoundFlowTemplate):
        return target.bind().to_symbol_ref()
    if isinstance(target, BoundFlowDeclaration):
        return target.to_symbol_ref()
    if isinstance(target, NamedFlowDeclarationRef):
        return target.to_symbol_ref()
    if isinstance(target, FlowDeclaration):
        return _coerce_flow_declaration_symbol_ref(target)
    if isinstance(target, FlowProgram):
        return _coerce_flow_program_symbol_ref(target)

    kind = _non_empty_str(_field(target, "kind"))
    if kind != "flow_symbol_ref":
        return None

    flow_uri = _non_empty_str(_field(target, "flow_uri"))
    program_rev = _non_empty_str(_field(target, "program_rev"))
    binding_mode = _non_empty_str(_field(target, "binding_mode")) or "unbound"
    declaration = _field(target, "declaration")
    if declaration is not None and not _is_flow_declaration_like(declaration):
        raise FlowDefinitionError(
            "flow symbol target declaration must be FlowProgram/FlowDeclaration when provided.",
        )
    if flow_uri is None and declaration is None:
        raise FlowDefinitionError(
            "flow symbol target requires flow_uri when declaration is not provided.",
        )

    materialization_policy = _coerce_flow_symbol_materialization_policy(
        _field(target, "materialization_policy"),
    )

    normalized: dict[str, Any] = {
        "kind": "flow_symbol_ref",
        "binding_mode": binding_mode,
    }
    if flow_uri is not None:
        normalized["flow_uri"] = flow_uri
    if program_rev is not None:
        normalized["program_rev"] = program_rev
    if declaration is not None:
        normalized["declaration"] = declaration
    if materialization_policy is not None:
        normalized["materialization_policy"] = materialization_policy
    for passthrough in (
        "bind",
        "io_bind",
        "name",
        "namespace",
        "selector",
        "declaration_id",
        "definition_hash",
    ):
        value = _field(target, passthrough)
        if value is not None:
            normalized[passthrough] = value
    return normalized


def _coerce_flow_program_symbol_ref(program: FlowProgram) -> dict[str, Any]:
    flow_uri = _non_empty_str(getattr(program, "flow_uri", None))

    normalized: dict[str, Any] = {
        "kind": "flow_symbol_ref",
        "binding_mode": "unbound",
        "declaration": program,
    }
    if flow_uri is not None:
        normalized["flow_uri"] = flow_uri
    metadata = getattr(program, "metadata", None)
    if isinstance(metadata, Mapping):
        for key in ("flow_program_rev", "program_rev", "version"):
            program_rev = _non_empty_str(metadata.get(key))
            if program_rev is not None:
                normalized["program_rev"] = program_rev
                break
    policies = getattr(program, "policies", None)
    if isinstance(policies, Mapping):
        materialization_policy = _coerce_flow_symbol_materialization_policy(
            policies.get("subflow_materialization"),
        )
        if materialization_policy is not None:
            normalized["materialization_policy"] = materialization_policy
    if flow_uri is None and "materialization_policy" not in normalized:
        normalized["materialization_policy"] = {"mode": "caller_owned"}
    return normalized


def _coerce_flow_declaration_symbol_ref(declaration: FlowDeclaration) -> dict[str, Any]:
    flow_uri = _non_empty_str(getattr(declaration, "flow_uri", None))
    namespace = _non_empty_str(getattr(declaration, "namespace", None))
    declaration_id = _non_empty_str(getattr(declaration, "declaration_id", None))
    definition_hash = _non_empty_str(getattr(declaration, "definition_hash", None))
    normalized: dict[str, Any] = {
        "kind": "flow_symbol_ref",
        "binding_mode": "unbound",
        "declaration": declaration.compile(),
    }
    if flow_uri is not None:
        normalized["flow_uri"] = flow_uri
    if namespace is not None:
        normalized["namespace"] = namespace
    if declaration_id is not None:
        normalized["declaration_id"] = declaration_id
    if definition_hash is not None:
        normalized["definition_hash"] = definition_hash
    return normalized


def _coerce_flow_symbol_materialization_policy(raw_policy: Any) -> dict[str, Any] | None:
    if raw_policy is None:
        return None
    if isinstance(raw_policy, str):
        normalized_mode = raw_policy.strip()
        if not normalized_mode:
            raise FlowDefinitionError(
                "flow symbol materialization policy mode must be non-empty when provided.",
            )
        return {"mode": normalized_mode}
    if not isinstance(raw_policy, Mapping):
        raise FlowDefinitionError(
            "flow symbol materialization policy must be mapping or string when provided.",
        )
    normalized: dict[str, Any] = {}
    mode = _non_empty_str(raw_policy.get("mode"))
    if mode is not None:
        normalized["mode"] = mode
    namespace = _non_empty_str(raw_policy.get("namespace"))
    if namespace is not None:
        normalized["namespace"] = namespace
    if not normalized:
        return None
    return normalized


def is_actor_target(target: Any) -> bool:
    return (
        _non_empty_str(_field(target, "address")) is not None
        and _non_empty_str(_field(target, "actor_id")) is not None
        and _non_empty_str(_field(target, "method")) is not None
    )


def is_stateless_target(target: Any) -> bool:
    return (
        _non_empty_str(_field(target, "op_id")) is not None
        and _non_empty_str(_field(target, "scope")) is not None
    )


def is_actor_symbol_target(target: Any) -> bool:
    try:
        return coerce_actor_symbol_target(target) is not None
    except Exception:
        return False


def is_stateless_symbol_target(target: Any) -> bool:
    try:
        return coerce_stateless_symbol_target(target) is not None
    except Exception:
        return False


def is_flow_symbol_target(target: Any) -> bool:
    try:
        return coerce_flow_symbol_target(target) is not None
    except Exception:
        return False


def _field(target: Any, name: str) -> Any:
    if isinstance(target, Mapping):
        return target.get(name)
    return getattr(target, name, None)


def _non_empty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _is_flow_declaration_like(value: Any) -> bool:
    return isinstance(value, (FlowProgram, FlowDeclaration))


__all__ = [
    "SystemTargetRef",
    "system_target",
    "ensure_flow_target",
    "coerce_actor_symbol_target",
    "coerce_stateless_symbol_target",
    "coerce_flow_symbol_target",
    "coerce_flow_program_ref_target",
    "is_actor_target",
    "is_actor_symbol_target",
    "is_stateless_symbol_target",
    "is_flow_symbol_target",
    "is_stateless_target",
]
