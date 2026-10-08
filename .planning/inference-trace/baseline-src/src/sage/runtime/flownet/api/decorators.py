from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from sage.runtime.flownet.api.declarations import (
    ActorDeclaration,
    FlowDeclaration,
    GroupPolicyDefault,
    ProcessDeclaration,
    ServiceDeclaration,
    ServiceStyle,
    SourceDeclaration,
    StatelessDeclaration,
)

_GROUP_POLICIES = {"automatic", "manual", "mixed"}
_SERVICE_STYLES = {"event_driven", "periodic", "hybrid"}


def _validate_flow_dsl_signature(flow_dsl: Callable[..., Any]) -> None:
    signature = inspect.signature(flow_dsl)
    parameters = list(signature.parameters.values())
    if not parameters:
        raise TypeError("v1.flow DSL must accept at least one parameter: init_stream.")
    first = parameters[0]
    if first.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
        raise TypeError("v1.flow DSL first parameter must be init_stream, not *args/**kwargs.")
    if first.kind is inspect.Parameter.KEYWORD_ONLY:
        raise TypeError("v1.flow DSL first parameter must be positional init_stream.")
    if first.name in {"self", "cls"}:
        raise TypeError(
            "v1.flow does not support class/instance method DSL. "
            "Define DSL as module/static function.",
        )
    if first.name != "init_stream":
        raise TypeError("v1.flow DSL first parameter must be named init_stream.")


def _validate_no_method_style_dsl(name: str, target: Callable[..., Any]) -> None:
    signature = inspect.signature(target)
    parameters = list(signature.parameters.values())
    if not parameters:
        return
    first = parameters[0]
    if first.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
        return
    if first.name in {"self", "cls"}:
        raise TypeError(
            f"v1.{name} does not support class/instance method DSL. "
            "Define DSL as module/static function.",
        )


def _resolve_flow_uri(*, uri: str | None, flow_uri: str | None) -> str | None:
    normalized_uri = _normalize_optional_str("uri", uri)
    normalized_flow_uri = _normalize_optional_str("flow_uri", flow_uri)
    if (
        normalized_uri is not None
        and normalized_flow_uri is not None
        and normalized_uri != normalized_flow_uri
    ):
        raise ValueError("flow uri conflict: provide only one of `uri` or `flow_uri`.")
    return normalized_uri if normalized_uri is not None else normalized_flow_uri


def _normalize_optional_str(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty when provided.")
    return normalized


def _normalize_required_str(name: str, value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty.")
    return normalized


def _normalize_string_sequence(name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{name} must be a sequence of strings, not a single string.")
    normalized: list[str] = []
    for index, raw in enumerate(values):
        if not isinstance(raw, str):
            raise TypeError(f"{name}[{index}] must be str.")
        item = raw.strip()
        if not item:
            raise ValueError(f"{name}[{index}] must not be empty.")
        normalized.append(item)
    return tuple(normalized)


def _normalize_mapping(name: str, value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping when provided.")
    return dict(value)


def _resolve_dsl_name(target: Any) -> str | None:
    return getattr(target, "__qualname__", None) or getattr(target, "__name__", None)


def _normalize_common_declaration_fields(
    *,
    target: Any,
    uri: str | None,
    description: str | None,
    namespace: str | None,
    tags: Sequence[str],
    capabilities: Sequence[str],
    input_schema_ref: str | None,
    output_schema_ref: str | None,
    resources_default: Mapping[str, Any] | None,
    scheduler_default: Mapping[str, Any] | None,
    policies: Mapping[str, Any] | None,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "target": target,
        "uri": _normalize_optional_str("uri", uri),
        "description": _normalize_optional_str("description", description),
        "namespace": _normalize_optional_str("namespace", namespace),
        "tags": _normalize_string_sequence("tags", tags),
        "capabilities": _normalize_string_sequence("capabilities", capabilities),
        "input_schema_ref": _normalize_optional_str("input_schema_ref", input_schema_ref),
        "output_schema_ref": _normalize_optional_str("output_schema_ref", output_schema_ref),
        "resources_default": _normalize_mapping("resources_default", resources_default),
        "scheduler_default": _normalize_mapping("scheduler_default", scheduler_default),
        "policies": _normalize_mapping("policies", policies),
        "metadata": _normalize_mapping("metadata", metadata),
        "dsl_name": _resolve_dsl_name(target),
    }


def flow(
    *,
    uri: str | None = None,
    flow_uri: str | None = None,
    namespace: str | None = None,
    scheduler: Mapping[str, Any] | None = None,
    resources: Mapping[str, Any] | None = None,
    policies: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
):
    """
    v1 flow decorator.

    Decision notes:
    - Compile at definition time for deterministic startup failures and stable
      topology snapshots.
    - Decorator args carry only program-level attributes
      (uri/scheduler/resources/policies).
      Topic input/output binding is intentionally external and happens later.
    - No runtime registration side effects here; this step only builds FlowProgram.
    """

    def _decorate(target: Callable[..., Any]) -> FlowDeclaration:
        _validate_flow_dsl_signature(target)
        resolved_uri = _resolve_flow_uri(uri=uri, flow_uri=flow_uri)
        declaration = FlowDeclaration(
            target=target,
            uri=resolved_uri,
            scheduler=scheduler,
            resources=resources,
            policies=policies,
            metadata=metadata,
            dsl_name=getattr(target, "__qualname__", None) or getattr(target, "__name__", None),
            namespace=_normalize_optional_str("namespace", namespace),
        )
        # Keep definition-time validation so DSL errors fail during import/startup.
        declaration.compile()
        return declaration

    return _decorate


def source(
    *,
    uri: str | None = None,
    description: str | None = None,
    namespace: str | None = None,
    tags: Sequence[str] = (),
    capabilities: Sequence[str] = (),
    input_schema_ref: str | None = None,
    output_schema_ref: str | None = None,
    resources_default: Mapping[str, Any] | None = None,
    scheduler_default: Mapping[str, Any] | None = None,
    policies: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    checkpoint_required: bool = True,
    group_policy_default: GroupPolicyDefault = "automatic",
    cursor_format: str | None = None,
):
    def _decorate(target: Callable[..., Any]) -> SourceDeclaration:
        if not callable(target):
            raise TypeError("v1.source expects a callable target.")
        _validate_no_method_style_dsl("source", target)
        if not isinstance(checkpoint_required, bool):
            raise TypeError("checkpoint_required must be bool.")
        if group_policy_default not in _GROUP_POLICIES:
            raise ValueError(
                "group_policy_default must be one of: automatic, manual, mixed.",
            )
        return SourceDeclaration(
            **_normalize_common_declaration_fields(
                target=target,
                uri=uri,
                description=description,
                namespace=namespace,
                tags=tags,
                capabilities=capabilities,
                input_schema_ref=input_schema_ref,
                output_schema_ref=output_schema_ref,
                resources_default=resources_default,
                scheduler_default=scheduler_default,
                policies=policies,
                metadata=metadata,
            ),
            checkpoint_required=checkpoint_required,
            group_policy_default=group_policy_default,
            cursor_format=_normalize_optional_str("cursor_format", cursor_format),
        )

    return _decorate


def service(
    *,
    uri: str | None = None,
    description: str | None = None,
    namespace: str | None = None,
    tags: Sequence[str] = (),
    capabilities: Sequence[str] = (),
    input_schema_ref: str | None = None,
    output_schema_ref: str | None = None,
    resources_default: Mapping[str, Any] | None = None,
    scheduler_default: Mapping[str, Any] | None = None,
    policies: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    service_style: ServiceStyle = "event_driven",
    heartbeat_default_sec: float | None = None,
):
    def _decorate(target: Callable[..., Any]) -> ServiceDeclaration:
        if not callable(target):
            raise TypeError("v1.service expects a callable target.")
        _validate_no_method_style_dsl("service", target)
        if service_style not in _SERVICE_STYLES:
            raise ValueError(
                "service_style must be one of: event_driven, periodic, hybrid.",
            )
        if heartbeat_default_sec is not None:
            if not isinstance(heartbeat_default_sec, (int, float)):
                raise TypeError("heartbeat_default_sec must be float when provided.")
            if float(heartbeat_default_sec) <= 0:
                raise ValueError("heartbeat_default_sec must be > 0 when provided.")

        return ServiceDeclaration(
            **_normalize_common_declaration_fields(
                target=target,
                uri=uri,
                description=description,
                namespace=namespace,
                tags=tags,
                capabilities=capabilities,
                input_schema_ref=input_schema_ref,
                output_schema_ref=output_schema_ref,
                resources_default=resources_default,
                scheduler_default=scheduler_default,
                policies=policies,
                metadata=metadata,
            ),
            service_style=service_style,
            heartbeat_default_sec=(
                float(heartbeat_default_sec) if heartbeat_default_sec is not None else None
            ),
        )

    return _decorate


def process(
    *,
    kind: str,
    uri: str | None = None,
    description: str | None = None,
    namespace: str | None = None,
    tags: Sequence[str] = (),
    capabilities: Sequence[str] = (),
    input_schema_ref: str | None = None,
    output_schema_ref: str | None = None,
    resources_default: Mapping[str, Any] | None = None,
    scheduler_default: Mapping[str, Any] | None = None,
    policies: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
):
    normalized_kind = _normalize_required_str("kind", kind)

    def _decorate(target: Callable[..., Any] | type[Any]) -> ProcessDeclaration:
        if inspect.isclass(target):
            pass
        elif callable(target):
            _validate_no_method_style_dsl("process", target)
        else:
            raise TypeError("v1.process expects a callable function or class target.")

        return ProcessDeclaration(
            **_normalize_common_declaration_fields(
                target=target,
                uri=uri,
                description=description,
                namespace=namespace,
                tags=tags,
                capabilities=capabilities,
                input_schema_ref=input_schema_ref,
                output_schema_ref=output_schema_ref,
                resources_default=resources_default,
                scheduler_default=scheduler_default,
                policies=policies,
                metadata=metadata,
            ),
            kind=normalized_kind,
        )

    return _decorate


def actor(
    *,
    uri: str | None = None,
    description: str | None = None,
    namespace: str | None = None,
    tags: Sequence[str] = (),
    capabilities: Sequence[str] = (),
    input_schema_ref: str | None = None,
    output_schema_ref: str | None = None,
    resources_default: Mapping[str, Any] | None = None,
    scheduler_default: Mapping[str, Any] | None = None,
    policies: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    mailbox_policy_default: Mapping[str, Any] | None = None,
    execution_policy_default: Mapping[str, Any] | None = None,
    retry_policy_default: Mapping[str, Any] | None = None,
    admission_policy_default: Mapping[str, Any] | None = None,
    drain_policy_default: Mapping[str, Any] | None = None,
):
    def _decorate(target: type[Any]) -> ActorDeclaration:
        if not inspect.isclass(target):
            raise TypeError("v1.actor expects a class target.")
        return ActorDeclaration(
            **_normalize_common_declaration_fields(
                target=target,
                uri=uri,
                description=description,
                namespace=namespace,
                tags=tags,
                capabilities=capabilities,
                input_schema_ref=input_schema_ref,
                output_schema_ref=output_schema_ref,
                resources_default=resources_default,
                scheduler_default=scheduler_default,
                policies=policies,
                metadata=metadata,
            ),
            mailbox_policy_default=_normalize_mapping(
                "mailbox_policy_default",
                mailbox_policy_default,
            ),
            execution_policy_default=_normalize_mapping(
                "execution_policy_default",
                execution_policy_default,
            ),
            retry_policy_default=_normalize_mapping(
                "retry_policy_default",
                retry_policy_default,
            ),
            admission_policy_default=_normalize_mapping(
                "admission_policy_default",
                admission_policy_default,
            ),
            drain_policy_default=_normalize_mapping(
                "drain_policy_default",
                drain_policy_default,
            ),
        )

    return _decorate


def stateless(
    *,
    uri: str | None = None,
    description: str | None = None,
    namespace: str | None = None,
    tags: Sequence[str] = (),
    capabilities: Sequence[str] = (),
    input_schema_ref: str | None = None,
    output_schema_ref: str | None = None,
    resources_default: Mapping[str, Any] | None = None,
    scheduler_default: Mapping[str, Any] | None = None,
    policies: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
):
    def _decorate(target: Callable[..., Any]) -> StatelessDeclaration:
        if not callable(target) or inspect.isclass(target):
            raise TypeError("v1.stateless expects a callable function target.")
        _validate_no_method_style_dsl("stateless", target)
        return StatelessDeclaration(
            **_normalize_common_declaration_fields(
                target=target,
                uri=uri,
                description=description,
                namespace=namespace,
                tags=tags,
                capabilities=capabilities,
                input_schema_ref=input_schema_ref,
                output_schema_ref=output_schema_ref,
                resources_default=resources_default,
                scheduler_default=scheduler_default,
                policies=policies,
                metadata=metadata,
            ),
        )

    return _decorate


__all__ = [
    "actor",
    "flow",
    "process",
    "service",
    "source",
    "stateless",
]
