from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from sage.runtime.flownet.contracts.shared_state_contract import (
    SharedStateServiceDescriptor,
    with_shared_state_binding_metadata,
)

GroupPolicyDefault = Literal["automatic", "manual", "mixed"]
ServiceStyle = Literal["event_driven", "periodic", "hybrid"]


@dataclass(frozen=True)
class Declaration:
    """
    v1 DSL declaration template.

    Declaration objects only carry metadata/defaults and never perform runtime
    registration/deployment side effects.
    """

    target: Any
    uri: str | None = None
    description: str | None = None
    tags: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None
    resources_default: dict[str, Any] = field(default_factory=dict)
    scheduler_default: dict[str, Any] = field(default_factory=dict)
    policies: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    dsl_name: str | None = None
    namespace: str | None = None
    declaration_id: str = ""
    definition_hash: str = ""

    def __post_init__(self) -> None:
        # Freeze mutable defaults to per-instance copies.
        object.__setattr__(self, "resources_default", dict(self.resources_default))
        object.__setattr__(self, "scheduler_default", dict(self.scheduler_default))
        object.__setattr__(self, "policies", dict(self.policies))
        object.__setattr__(self, "metadata", dict(self.metadata))

        resolved_namespace = _resolve_namespace(
            explicit_namespace=self.namespace,
            metadata=self.metadata,
            target=self.target,
        )
        object.__setattr__(self, "namespace", resolved_namespace)

        if not _normalize_optional_text(self.declaration_id):
            object.__setattr__(
                self,
                "declaration_id",
                _build_declaration_id(
                    declaration_kind=type(self).__name__,
                    namespace=resolved_namespace,
                    uri=self.uri,
                    dsl_name=self.dsl_name,
                    target=self.target,
                ),
            )
        if not _normalize_optional_text(self.definition_hash):
            object.__setattr__(
                self,
                "definition_hash",
                _build_definition_hash(
                    declaration_kind=type(self).__name__,
                    target=self.target,
                    uri=self.uri,
                    dsl_name=self.dsl_name,
                    namespace=resolved_namespace,
                    metadata=self.metadata,
                    policies=self.policies,
                ),
            )

    def __get__(self, instance, owner):
        if instance is not None:
            raise TypeError(
                f"v1 {type(self).__name__} does not support class-instance binding. "
                "Define DSL as module/static symbol.",
            )
        return self

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> Declaration:
        return replace(
            self,
            metadata=with_shared_state_binding_metadata(
                self.metadata,
                alias=alias,
                descriptor=descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            definition_hash="",
        )


@dataclass(frozen=True)
class SourceDeclaration(Declaration):
    checkpoint_required: bool = True
    group_policy_default: GroupPolicyDefault = "automatic"
    cursor_format: str | None = None

    def bind(
        self, *, out: Any | None = None, out_topic: Any | None = None
    ) -> BoundSourceDeclaration:
        resolved_out = out if out is not None else out_topic
        return BoundSourceDeclaration(
            declaration=self,
            out_binding=resolved_out,
        )


@dataclass(frozen=True)
class ServiceDeclaration(Declaration):
    service_style: ServiceStyle = "event_driven"
    heartbeat_default_sec: float | None = None

    def bind(
        self,
        *,
        in_: Any | None = None,
        out: Any | None = None,
        in_topic: Any | None = None,
        out_topic: Any | None = None,
    ) -> BoundServiceDeclaration:
        resolved_in = in_ if in_ is not None else in_topic
        resolved_out = out if out is not None else out_topic
        return BoundServiceDeclaration(
            declaration=self,
            in_binding=resolved_in,
            out_binding=resolved_out,
        )


@dataclass(frozen=True)
class ProcessDeclaration(Declaration):
    kind: str = ""


@dataclass(frozen=True)
class ActorDeclaration(Declaration):
    mailbox_policy_default: dict[str, Any] = field(default_factory=dict)
    execution_policy_default: dict[str, Any] = field(default_factory=dict)
    retry_policy_default: dict[str, Any] = field(default_factory=dict)
    admission_policy_default: dict[str, Any] = field(default_factory=dict)
    drain_policy_default: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "mailbox_policy_default", dict(self.mailbox_policy_default))
        object.__setattr__(self, "execution_policy_default", dict(self.execution_policy_default))
        object.__setattr__(self, "retry_policy_default", dict(self.retry_policy_default))
        object.__setattr__(self, "admission_policy_default", dict(self.admission_policy_default))
        object.__setattr__(self, "drain_policy_default", dict(self.drain_policy_default))

    def method_ref(self, method: str) -> ActorMethodSymbolRef:
        normalized_method = _normalize_non_empty_method_name(method)
        target = self.target
        attr = getattr(target, normalized_method, None)
        if not callable(attr):
            target_name = (
                getattr(target, "__qualname__", None)
                or getattr(target, "__name__", None)
                or type(target).__name__
            )
            raise AttributeError(
                f"actor declaration target '{target_name}' has no callable method '{normalized_method}'.",
            )
        return ActorMethodSymbolRef(
            declaration=self,
            method=normalized_method,
            origin="unbound",
        )

    def default_method_name(self) -> str:
        candidate = "advance"
        attr = getattr(self.target, candidate, None)
        if callable(attr):
            return candidate
        target_name = (
            getattr(self.target, "__qualname__", None)
            or getattr(self.target, "__name__", None)
            or type(self.target).__name__
        )
        raise AttributeError(
            f"actor declaration target '{target_name}' has no default callable method "
            "(expected advance).",
        )

    def default_method_ref(self) -> ActorMethodSymbolRef:
        return self.method_ref(self.default_method_name())

    def __getattr__(self, name: str) -> ActorMethodSymbolRef:
        if str(name).startswith("__") and str(name).endswith("__"):
            raise AttributeError(name)
        try:
            return self.method_ref(str(name))
        except AttributeError as exc:
            raise AttributeError(name) from exc

    def __call__(self, *args: Any, **kwargs: Any) -> BoundActorDeclaration:
        return BoundActorDeclaration(
            declaration=self,
            bind_args=tuple(args),
            bind_kwargs=dict(kwargs),
        )

    def find(self, name: str, *, namespace: str | None = None) -> NamedActorDeclarationRef:
        return NamedActorDeclarationRef(
            declaration=self,
            name=_normalize_required_name(name, field_name="name"),
            namespace=_resolve_ref_namespace(namespace=namespace, declaration=self),
            selector="find",
        )

    def locate(self, tag: str, *, namespace: str | None = None) -> NamedActorDeclarationRef:
        return NamedActorDeclarationRef(
            declaration=self,
            name=_normalize_required_name(tag, field_name="tag"),
            namespace=_resolve_ref_namespace(namespace=namespace, declaration=self),
            selector="locate",
        )


@dataclass(frozen=True)
class ActorMethodSymbolRef:
    declaration: ActorDeclaration
    method: str
    bind_args: tuple[Any, ...] = ()
    bind_kwargs: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    namespace: str | None = None
    selector: str | None = None
    materialization_policy_override: dict[str, Any] = field(default_factory=dict)
    origin: str = "unbound"

    def __post_init__(self) -> None:
        _normalize_non_empty_method_name(self.method)
        object.__setattr__(self, "bind_args", tuple(self.bind_args))
        object.__setattr__(self, "bind_kwargs", dict(self.bind_kwargs))
        object.__setattr__(
            self,
            "materialization_policy_override",
            _normalize_optional_mapping(
                self.materialization_policy_override,
                field_name="materialization_policy_override",
            ),
        )
        normalized_origin = str(self.origin or "").strip().lower() or "unbound"
        if normalized_origin not in {"unbound", "bound", "named"}:
            raise ValueError(
                "ActorMethodSymbolRef origin must be one of: unbound, bound, named.",
            )
        object.__setattr__(self, "origin", normalized_origin)
        if self.name is not None:
            object.__setattr__(
                self,
                "name",
                _normalize_required_name(self.name, field_name="name"),
            )
        if self.namespace is not None:
            object.__setattr__(
                self,
                "namespace",
                _normalize_required_name(self.namespace, field_name="namespace"),
            )
        if self.selector is not None:
            object.__setattr__(self, "selector", str(self.selector).strip() or None)

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> ActorMethodSymbolRef:
        return ActorMethodSymbolRef(
            declaration=self.declaration.use_shared_state(
                alias,
                descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            method=self.method,
            bind_args=self.bind_args,
            bind_kwargs=self.bind_kwargs,
            name=self.name,
            namespace=self.namespace,
            selector=self.selector,
            materialization_policy_override=self.materialization_policy_override,
            origin=self.origin,
        )


@dataclass(frozen=True)
class BoundActorDeclaration:
    declaration: ActorDeclaration
    bind_args: tuple[Any, ...] = ()
    bind_kwargs: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    namespace: str | None = None
    selector: str | None = None
    materialization_policy_override: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "bind_args", tuple(self.bind_args))
        object.__setattr__(self, "bind_kwargs", dict(self.bind_kwargs))
        if self.name is not None:
            object.__setattr__(
                self,
                "name",
                _normalize_required_name(self.name, field_name="name"),
            )
        if self.namespace is not None:
            object.__setattr__(
                self,
                "namespace",
                _normalize_required_name(self.namespace, field_name="namespace"),
            )
        if self.selector is not None:
            object.__setattr__(
                self,
                "selector",
                _normalize_selector(self.selector),
            )
        object.__setattr__(
            self,
            "materialization_policy_override",
            _normalize_optional_mapping(
                self.materialization_policy_override,
                field_name="materialization_policy_override",
            ),
        )

    def method_ref(self, method: str) -> ActorMethodSymbolRef:
        base_ref = self.declaration.method_ref(method)
        return ActorMethodSymbolRef(
            declaration=base_ref.declaration,
            method=base_ref.method,
            bind_args=self.bind_args,
            bind_kwargs=self.bind_kwargs,
            name=self.name,
            namespace=self.namespace,
            selector=self.selector,
            materialization_policy_override=self.materialization_policy_override,
            origin="bound",
        )

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> BoundActorDeclaration:
        return BoundActorDeclaration(
            declaration=self.declaration.use_shared_state(
                alias,
                descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            bind_args=self.bind_args,
            bind_kwargs=self.bind_kwargs,
            name=self.name,
            namespace=self.namespace,
            selector=self.selector,
            materialization_policy_override=self.materialization_policy_override,
        )

    def default_method_ref(self) -> ActorMethodSymbolRef:
        return self.method_ref(self.declaration.default_method_name())

    def __getattr__(self, name: str) -> ActorMethodSymbolRef:
        if str(name).startswith("__") and str(name).endswith("__"):
            raise AttributeError(name)
        try:
            return self.method_ref(name)
        except AttributeError as exc:
            raise AttributeError(name) from exc

    def options(
        self,
        *,
        name: str | None = None,
        namespace: str | None = None,
        selector: str | None = None,
        replicas: int | None = None,
        replica_policy: Mapping[str, Any] | None = None,
        materialization_policy_override: Mapping[str, Any] | None = None,
        materialization: Mapping[str, Any] | None = None,
    ) -> BoundActorDeclaration:
        resolved_name = self.name
        if name is not None:
            resolved_name = _normalize_required_name(name, field_name="name")

        resolved_namespace = self.namespace
        if namespace is not None:
            resolved_namespace = _normalize_required_name(namespace, field_name="namespace")

        resolved_selector = self.selector
        if selector is not None:
            resolved_selector = _normalize_selector(selector)

        merged_materialization_override = dict(self.materialization_policy_override)
        if materialization is not None:
            merged_materialization_override = _deep_merge_mapping(
                merged_materialization_override,
                _normalize_optional_mapping(
                    materialization,
                    field_name="materialization",
                ),
            )
        if materialization_policy_override is not None:
            merged_materialization_override = _deep_merge_mapping(
                merged_materialization_override,
                _normalize_optional_mapping(
                    materialization_policy_override,
                    field_name="materialization_policy_override",
                ),
            )
        if replica_policy is not None:
            merged_materialization_override = _deep_merge_mapping(
                merged_materialization_override,
                {
                    "replica_policy": _normalize_optional_mapping(
                        replica_policy,
                        field_name="replica_policy",
                    ),
                },
            )
        if replicas is not None:
            resolved_replicas = int(replicas)
            if resolved_replicas < 1:
                raise ValueError("replicas must be >= 1 when provided.")
            merged_materialization_override = _deep_merge_mapping(
                merged_materialization_override,
                {
                    "replica_policy": {
                        "mode": "fixed",
                        "count": resolved_replicas,
                    },
                },
            )
        return BoundActorDeclaration(
            declaration=self.declaration,
            bind_args=self.bind_args,
            bind_kwargs=self.bind_kwargs,
            name=resolved_name,
            namespace=resolved_namespace,
            selector=resolved_selector,
            materialization_policy_override=merged_materialization_override,
        )

    def remote(
        self,
        *,
        client: Any | None = None,
        name: str | None = None,
        namespace: str | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        **instantiate_kwargs: Any,
    ) -> Any:
        replica_count = _resolve_replica_count(self.materialization_policy_override)
        if replica_count > 1:
            raise RuntimeError(
                "actor_replica_requires_flow_context:"
                " replicas>1 bound actor symbolic references can only be consumed inside flow execution.",
            )
        runtime_client = _resolve_runtime_client(client)
        actor_surface = getattr(runtime_client, "actors", None)
        instantiate = getattr(actor_surface, "instantiate", None)
        if not callable(instantiate):
            raise RuntimeError("v1_runtime_client_missing_actor_surface")
        options = dict(instantiate_kwargs)
        options["ctor_args"] = tuple(self.bind_args)
        options["ctor_kwargs"] = dict(self.bind_kwargs)
        resolved_name = self.name
        if name is not None:
            resolved_name = _normalize_required_name(name, field_name="name")
        resolved_namespace = self.namespace
        if namespace is not None:
            resolved_namespace = _normalize_required_name(namespace, field_name="namespace")
        if resolved_name is not None:
            options["name"] = resolved_name
        if resolved_namespace is not None:
            options["namespace"] = resolved_namespace
        return instantiate(
            self.declaration,
            config=config,
            policies=policies,
            **options,
        )


@dataclass(frozen=True)
class NamedActorDeclarationRef:
    declaration: ActorDeclaration
    name: str
    namespace: str | None = None
    selector: str = "find"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_required_name(self.name, field_name="name"))
        if self.namespace is not None:
            object.__setattr__(
                self,
                "namespace",
                _normalize_required_name(self.namespace, field_name="namespace"),
            )
        selector = str(self.selector or "find").strip() or "find"
        object.__setattr__(self, "selector", selector)

    def method_ref(self, method: str) -> ActorMethodSymbolRef:
        base_ref = self.declaration.method_ref(method)
        return ActorMethodSymbolRef(
            declaration=base_ref.declaration,
            method=base_ref.method,
            name=self.name,
            namespace=self.namespace,
            selector=self.selector,
            origin="named",
        )

    def default_method_ref(self) -> ActorMethodSymbolRef:
        return self.method_ref(self.declaration.default_method_name())

    def __getattr__(self, name: str) -> ActorMethodSymbolRef:
        if str(name).startswith("__") and str(name).endswith("__"):
            raise AttributeError(name)
        try:
            return self.method_ref(name)
        except AttributeError as exc:
            raise AttributeError(name) from exc


@dataclass(frozen=True)
class StatelessDeclaration(Declaration):
    pass


class FlowDeclaration:
    """
    Callable flow declaration template.

    - `FlowDeclaration(...)` binds constructor parameters only (no runtime side effects).
    - `FlowDeclaration(...).bind(...)` returns a bound flow declaration with IO binding.
    """

    def __init__(
        self,
        *,
        target: Callable[..., Any],
        uri: str | None,
        scheduler: Mapping[str, Any] | None,
        resources: Mapping[str, Any] | None,
        policies: Mapping[str, Any] | None,
        metadata: Mapping[str, Any] | None,
        dsl_name: str | None,
        namespace: str | None = None,
    ) -> None:
        self.target = target
        self.uri = _normalize_optional_text(uri)
        self.flow_uri = self.uri
        self.scheduler = dict(scheduler or {})
        self.resources = dict(resources or {})
        self.policies = dict(policies or {})
        self.metadata = dict(metadata or {})
        self.dsl_name = _normalize_optional_text(dsl_name)
        self.namespace = _resolve_namespace(
            explicit_namespace=namespace,
            metadata=self.metadata,
            target=self.target,
        )
        self.declaration_id = _build_declaration_id(
            declaration_kind="FlowDeclaration",
            namespace=self.namespace,
            uri=self.flow_uri,
            dsl_name=self.dsl_name,
            target=self.target,
        )
        self.definition_hash = _build_definition_hash(
            declaration_kind="FlowDeclaration",
            target=self.target,
            uri=self.flow_uri,
            dsl_name=self.dsl_name,
            namespace=self.namespace,
            metadata=self.metadata,
            policies=self.policies,
        )
        self._default_program = None

    def __get__(self, instance, owner):
        if instance is not None:
            raise TypeError(
                "v1 FlowDeclaration does not support class-instance binding. "
                "Define flow DSL as module/static symbol.",
            )
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> BoundFlowTemplate:
        return BoundFlowTemplate(
            declaration=self,
            flow_args=tuple(args),
            flow_kwargs=dict(kwargs),
        )

    def bind(
        self,
        *args: Any,
        in_: Any | None = None,
        out: Any | None = None,
        **kwargs: Any,
    ) -> BoundFlowDeclaration:
        return self().bind(*args, in_=in_, out=out, **kwargs)

    def find(self, name: str, *, namespace: str | None = None) -> NamedFlowDeclarationRef:
        return NamedFlowDeclarationRef(
            declaration=self,
            name=_normalize_required_name(name, field_name="name"),
            namespace=_resolve_ref_namespace(namespace=namespace, declaration=self),
            selector="find",
        )

    def locate(self, tag: str, *, namespace: str | None = None) -> NamedFlowDeclarationRef:
        return NamedFlowDeclarationRef(
            declaration=self,
            name=_normalize_required_name(tag, field_name="tag"),
            namespace=_resolve_ref_namespace(namespace=namespace, declaration=self),
            selector="locate",
        )

    def compile(self, *args: Any, **kwargs: Any):
        if not args and not kwargs and self._default_program is not None:
            return self._default_program

        from sage.runtime.flownet.compiler import compile_flow_program

        if args or kwargs:

            def _bound_dsl(init_stream):
                return self.target(init_stream, *args, **kwargs)

            program = compile_flow_program(_bound_dsl)
        else:
            program = compile_flow_program(self.target)
        metadata = dict(self.metadata)
        metadata.setdefault("namespace", self.namespace)
        metadata.setdefault("declaration_id", self.declaration_id)
        metadata.setdefault("definition_hash", self.definition_hash)
        program.configure(
            flow_uri=self.flow_uri,
            scheduler=self.scheduler,
            resources=self.resources,
            policies=self.policies,
            metadata=metadata,
            dsl_name=self.dsl_name,
        )
        if not args and not kwargs:
            self._default_program = program
        return program

    @property
    def pipeline(self) -> list[Any]:
        return list(self.compile().pipeline)

    def endpoint(self, *, client=None, **kwargs):
        return self.compile().endpoint(client=client, **kwargs)

    def publish(self, *, client=None, **kwargs):
        return self.compile().publish(client=client, **kwargs)

    def find_endpoint(
        self,
        *,
        client=None,
        name: str,
        namespace: str | None = None,
    ):
        resolved_namespace = _resolve_ref_namespace(namespace=namespace, declaration=self)
        return self.compile().find_endpoint(
            client=client,
            name=name,
            namespace=resolved_namespace,
        )

    def inspect_endpoint(
        self,
        *,
        client=None,
        endpoint_id: str | None = None,
        name: str | None = None,
        namespace: str | None = None,
    ):
        resolved_namespace = None
        if namespace is not None:
            resolved_namespace = _resolve_ref_namespace(namespace=namespace, declaration=self)
        elif name is not None:
            resolved_namespace = _resolve_ref_namespace(namespace=None, declaration=self)
        return self.compile().inspect_endpoint(
            client=client,
            endpoint_id=endpoint_id,
            name=name,
            namespace=resolved_namespace,
        )

    def list_endpoints(
        self,
        *,
        client=None,
        namespace: str | None = None,
        include_released: bool = True,
    ):
        resolved_namespace = None
        if namespace is not None:
            resolved_namespace = _resolve_ref_namespace(namespace=namespace, declaration=self)
        return self.compile().list_endpoints(
            client=client,
            namespace=resolved_namespace,
            include_released=include_released,
        )

    def call(self, payload, *, client=None, timeout: float = 5.0, **kwargs):
        return self.compile().call(payload, client=client, timeout=timeout, **kwargs)

    def open_request(
        self,
        *,
        client=None,
        request_id: str | None = None,
        tags: Mapping[str, str] | None = None,
        **kwargs,
    ):
        return self.compile().open_request(
            client=client,
            request_id=request_id,
            tags=tags,
            **kwargs,
        )

    def submit(
        self,
        payload,
        *,
        client=None,
        request_id: str | None = None,
        tags: Mapping[str, str] | None = None,
        **kwargs,
    ):
        return self.compile().submit(
            payload,
            client=client,
            request_id=request_id,
            tags=tags,
            **kwargs,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.compile(), name)

    def __repr__(self) -> str:
        return (
            "FlowDeclaration("
            f"flow_uri={self.flow_uri!r}, dsl_name={self.dsl_name!r}, "
            f"namespace={self.namespace!r})"
        )

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> FlowDeclaration:
        return FlowDeclaration(
            target=self.target,
            uri=self.flow_uri,
            scheduler=self.scheduler,
            resources=self.resources,
            policies=self.policies,
            metadata=with_shared_state_binding_metadata(
                self.metadata,
                alias=alias,
                descriptor=descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            dsl_name=self.dsl_name,
            namespace=self.namespace,
        )


@dataclass(frozen=True)
class BoundFlowTemplate:
    declaration: FlowDeclaration
    flow_args: tuple[Any, ...] = ()
    flow_kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "flow_args", tuple(self.flow_args))
        object.__setattr__(self, "flow_kwargs", dict(self.flow_kwargs))

    def bind(
        self,
        *args: Any,
        in_: Any | None = None,
        out: Any | None = None,
        **kwargs: Any,
    ) -> BoundFlowDeclaration:
        resolved_in = in_
        resolved_out = out
        if args:
            if len(args) > 2:
                raise TypeError("bind() accepts at most two positional arguments: in, out.")
            if len(args) >= 1:
                if resolved_in is not None:
                    raise TypeError("bind() received both positional in and keyword in_.")
                resolved_in = args[0]
            if len(args) == 2:
                if resolved_out is not None:
                    raise TypeError("bind() received both positional out and keyword out.")
                resolved_out = args[1]

        if "in" in kwargs:
            if resolved_in is not None:
                raise TypeError("bind() in binding provided multiple times.")
            resolved_in = kwargs.pop("in")
        if "out" in kwargs:
            if resolved_out is not None:
                raise TypeError("bind() out binding provided multiple times.")
            resolved_out = kwargs.pop("out")
        if "in_topic" in kwargs:
            if resolved_in is not None:
                raise TypeError("bind() in binding provided multiple times.")
            resolved_in = kwargs.pop("in_topic")
        if "out_topic" in kwargs:
            if resolved_out is not None:
                raise TypeError("bind() out binding provided multiple times.")
            resolved_out = kwargs.pop("out_topic")
        if "inputs" in kwargs:
            if resolved_in is not None:
                raise TypeError("bind() in binding provided multiple times.")
            resolved_in = kwargs.pop("inputs")
        if "outputs" in kwargs:
            if resolved_out is not None:
                raise TypeError("bind() out binding provided multiple times.")
            resolved_out = kwargs.pop("outputs")
        if kwargs:
            unknown = ", ".join(sorted(str(key) for key in kwargs))
            raise TypeError(f"bind() got unexpected keyword arguments: {unknown}")

        return BoundFlowDeclaration(
            declaration=self.declaration,
            flow_args=self.flow_args,
            flow_kwargs=self.flow_kwargs,
            in_binding=resolved_in,
            out_binding=resolved_out,
        )

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> BoundFlowTemplate:
        return BoundFlowTemplate(
            declaration=self.declaration.use_shared_state(
                alias,
                descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            flow_args=self.flow_args,
            flow_kwargs=self.flow_kwargs,
        )


@dataclass(frozen=True)
class BoundFlowDeclaration:
    declaration: FlowDeclaration
    flow_args: tuple[Any, ...] = ()
    flow_kwargs: dict[str, Any] = field(default_factory=dict)
    in_binding: Any = None
    out_binding: Any = None
    _flow_program: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "flow_args", tuple(self.flow_args))
        object.__setattr__(self, "flow_kwargs", dict(self.flow_kwargs))
        object.__setattr__(
            self,
            "_flow_program",
            self.declaration.compile(*self.flow_args, **self.flow_kwargs),
        )

    @property
    def flow_program(self):
        return self._flow_program

    @property
    def flow_uri(self) -> str | None:
        return _normalize_optional_text(getattr(self._flow_program, "flow_uri", None))

    def _resolve_io_topics(
        self,
        *,
        in_topic: str | None = None,
        out_topic: str | None = None,
    ) -> tuple[str | None, str | None]:
        resolved_in = _resolve_topic_from_binding(in_topic) or _resolve_topic_from_binding(
            self.in_binding
        )
        resolved_out = _resolve_topic_from_binding(out_topic) or _resolve_topic_from_binding(
            self.out_binding
        )
        return resolved_in, resolved_out

    def to_symbol_ref(self) -> dict[str, Any]:
        symbol: dict[str, Any] = {
            "kind": "flow_symbol_ref",
            "binding_mode": "bound",
            "declaration": self.flow_program,
            "bind": {
                "args": list(self.flow_args),
                "kwargs": dict(self.flow_kwargs),
            },
            "declaration_id": self.declaration.declaration_id,
            "definition_hash": self.declaration.definition_hash,
            "namespace": self.declaration.namespace,
        }
        flow_uri = _normalize_optional_text(getattr(self.flow_program, "flow_uri", None))
        if flow_uri is not None:
            symbol["flow_uri"] = flow_uri
        metadata = getattr(self.flow_program, "metadata", None)
        if isinstance(metadata, Mapping):
            for key in ("flow_program_rev", "program_rev", "version"):
                rev = _normalize_optional_text(metadata.get(key))
                if rev is not None:
                    symbol["program_rev"] = rev
                    break
        policies = getattr(self.flow_program, "policies", None)
        if isinstance(policies, Mapping):
            raw_policy = policies.get("subflow_materialization")
            if raw_policy is not None:
                symbol["materialization_policy"] = raw_policy
        if self.in_binding is not None or self.out_binding is not None:
            symbol["io_bind"] = {
                "in": self.in_binding,
                "out": self.out_binding,
            }
        return symbol

    def endpoint(
        self,
        *,
        client: Any | None = None,
        in_topic: str | None = None,
        out_topic: str | None = None,
        reuse_existing: bool = True,
        **kwargs: Any,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        flow_surface = getattr(runtime_client, "flows", None)
        endpoint_fn = getattr(flow_surface, "endpoint", None)
        if not callable(endpoint_fn):
            raise RuntimeError("v1_runtime_client_missing_flow_surface")
        resolved_in, resolved_out = self._resolve_io_topics(
            in_topic=in_topic,
            out_topic=out_topic,
        )
        return endpoint_fn(
            self.flow_program,
            in_topic=resolved_in,
            out_topic=resolved_out,
            reuse_existing=reuse_existing,
            **kwargs,
        )

    def publish(
        self,
        *,
        client: Any | None = None,
        name: str,
        namespace: str | None = None,
        version: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        in_topic: str | None = None,
        out_topic: str | None = None,
        reuse_existing: bool = True,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        flow_surface = getattr(runtime_client, "flows", None)
        publish_fn = getattr(flow_surface, "publish_endpoint", None)
        if not callable(publish_fn):
            raise RuntimeError("v1_runtime_client_missing_flow_publish_endpoint")
        resolved_in, resolved_out = self._resolve_io_topics(
            in_topic=in_topic,
            out_topic=out_topic,
        )
        return publish_fn(
            self.flow_program,
            name=name,
            namespace=namespace,
            version=version,
            metadata=metadata,
            in_topic=resolved_in,
            out_topic=resolved_out,
            config=config,
            policies=policies,
            reuse_existing=reuse_existing,
        )

    def find_endpoint(
        self,
        *,
        client: Any | None = None,
        name: str,
        namespace: str | None = None,
    ) -> Any:
        return self.flow_program.find_endpoint(
            client=client,
            name=name,
            namespace=namespace or self.declaration.namespace,
        )

    def inspect_endpoint(
        self,
        *,
        client: Any | None = None,
        endpoint_id: str | None = None,
        name: str | None = None,
        namespace: str | None = None,
    ) -> Any:
        return self.flow_program.inspect_endpoint(
            client=client,
            endpoint_id=endpoint_id,
            name=name,
            namespace=namespace or self.declaration.namespace,
        )

    def list_endpoints(
        self,
        *,
        client: Any | None = None,
        namespace: str | None = None,
        include_released: bool = True,
    ) -> Any:
        return self.flow_program.list_endpoints(
            client=client,
            namespace=namespace or self.declaration.namespace,
            include_released=include_released,
        )

    def remote(
        self,
        *,
        client: Any | None = None,
        name: str | None = None,
        namespace: str | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        start: bool = False,
        in_topic: str | None = None,
        out_topic: str | None = None,
        **kwargs: Any,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        flow_surface = getattr(runtime_client, "flows", None)
        if flow_surface is None:
            raise RuntimeError("v1_runtime_client_missing_flow_surface")
        resolved_in, resolved_out = self._resolve_io_topics(
            in_topic=in_topic,
            out_topic=out_topic,
        )
        options = dict(kwargs)
        if name is not None:
            options["name"] = _normalize_required_name(name, field_name="name")
        if namespace is not None:
            options["namespace"] = _normalize_required_name(namespace, field_name="namespace")
        target_method_name = (
            "start" if start and callable(getattr(flow_surface, "start", None)) else "instantiate"
        )
        target_method = getattr(flow_surface, target_method_name, None)
        if not callable(target_method):
            raise RuntimeError("v1_runtime_client_missing_flow_instantiate")
        return target_method(
            self.flow_program,
            config=config,
            policies=policies,
            in_topic=resolved_in,
            out_topic=resolved_out,
            **options,
        )


@dataclass(frozen=True)
class NamedFlowDeclarationRef:
    declaration: FlowDeclaration
    name: str
    namespace: str | None = None
    selector: str = "find"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_required_name(self.name, field_name="name"))
        if self.namespace is not None:
            object.__setattr__(
                self,
                "namespace",
                _normalize_required_name(self.namespace, field_name="namespace"),
            )
        selector = str(self.selector or "find").strip() or "find"
        object.__setattr__(self, "selector", selector)

    def to_symbol_ref(self) -> dict[str, Any]:
        flow_uri = _normalize_optional_text(self.declaration.flow_uri)
        if flow_uri is None:
            raise ValueError(
                "named flow reference requires declaration flow_uri. "
                "Use a flow declaration with explicit uri/flow_uri.",
            )
        return {
            "kind": "flow_symbol_ref",
            "binding_mode": "named",
            "flow_uri": flow_uri,
            "name": self.name,
            "namespace": self.namespace,
            "selector": self.selector,
            "declaration_id": self.declaration.declaration_id,
            "definition_hash": self.declaration.definition_hash,
        }

    def endpoint(
        self,
        *,
        client: Any | None = None,
        in_topic: str | None = None,
        out_topic: str | None = None,
        reuse_existing: bool = True,
        **kwargs: Any,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        flow_surface = getattr(runtime_client, "flows", None)
        if flow_surface is None:
            raise RuntimeError("v1_runtime_client_missing_flow_surface")
        find_fn = getattr(flow_surface, "find", None)
        if callable(find_fn):
            resolved_instance = find_fn(
                name=self.name, namespace=self.namespace, selector=self.selector
            )
            if resolved_instance is not None:
                endpoint_fn = getattr(flow_surface, "endpoint", None)
                if not callable(endpoint_fn):
                    raise RuntimeError("v1_runtime_client_missing_flow_endpoint")
                return endpoint_fn(
                    resolved_instance,
                    in_topic=in_topic,
                    out_topic=out_topic,
                    reuse_existing=reuse_existing,
                    **kwargs,
                )
        endpoint_fn = getattr(flow_surface, "endpoint", None)
        if not callable(endpoint_fn):
            raise RuntimeError("v1_runtime_client_missing_flow_endpoint")
        return endpoint_fn(
            self.declaration.compile(),
            in_topic=in_topic,
            out_topic=out_topic,
            reuse_existing=reuse_existing,
            **kwargs,
        )

    def remote(
        self,
        *,
        client: Any | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        start: bool = False,
        in_topic: str | None = None,
        out_topic: str | None = None,
        **kwargs: Any,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        flow_surface = getattr(runtime_client, "flows", None)
        if flow_surface is None:
            raise RuntimeError("v1_runtime_client_missing_flow_surface")
        target_method_name = (
            "start" if start and callable(getattr(flow_surface, "start", None)) else "instantiate"
        )
        target_method = getattr(flow_surface, target_method_name, None)
        if not callable(target_method):
            raise RuntimeError("v1_runtime_client_missing_flow_instantiate")
        options = dict(kwargs)
        options.setdefault("name", self.name)
        if self.namespace is not None:
            options.setdefault("namespace", self.namespace)
        options.setdefault("selector", self.selector)
        return target_method(
            self.declaration.compile(),
            config=config,
            policies=policies,
            in_topic=in_topic,
            out_topic=out_topic,
            **options,
        )

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> BoundFlowDeclaration:
        return BoundFlowDeclaration(
            declaration=self.declaration.use_shared_state(
                alias,
                descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            flow_args=self.flow_args,
            flow_kwargs=self.flow_kwargs,
            in_binding=self.in_binding,
            out_binding=self.out_binding,
        )


@dataclass(frozen=True)
class BoundSourceDeclaration:
    declaration: SourceDeclaration
    out_binding: Any = None

    def remote(
        self,
        *,
        client: Any | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        source_surface = getattr(runtime_client, "sources", None)
        start = getattr(source_surface, "start", None)
        if not callable(start):
            raise RuntimeError("v1_runtime_client_missing_source_surface")
        options = dict(kwargs)
        resolved_out_topic = _resolve_topic_from_binding(self.out_binding)
        if resolved_out_topic is not None:
            options.setdefault("out_topic", resolved_out_topic)
        return start(
            self.declaration,
            config=config,
            policies=policies,
            **options,
        )


@dataclass(frozen=True)
class BoundServiceDeclaration:
    declaration: ServiceDeclaration
    in_binding: Any = None
    out_binding: Any = None

    def remote(
        self,
        *,
        client: Any | None = None,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        runtime_client = _resolve_runtime_client(client)
        service_surface = getattr(runtime_client, "services", None)
        start = getattr(service_surface, "start", None)
        if not callable(start):
            raise RuntimeError("v1_runtime_client_missing_service_surface")
        options = dict(kwargs)
        resolved_in_topic = _resolve_topic_from_binding(self.in_binding)
        resolved_out_topic = _resolve_topic_from_binding(self.out_binding)
        if resolved_in_topic is not None:
            options.setdefault("in_topic", resolved_in_topic)
        if resolved_out_topic is not None:
            options.setdefault("out_topic", resolved_out_topic)
        return start(
            self.declaration,
            config=config,
            policies=policies,
            **options,
        )

    def use_shared_state(
        self,
        alias: str,
        descriptor: SharedStateServiceDescriptor | Mapping[str, Any],
        *,
        required: bool = True,
        binding_metadata: Mapping[str, Any] | None = None,
    ) -> BoundServiceDeclaration:
        return BoundServiceDeclaration(
            declaration=self.declaration.use_shared_state(
                alias,
                descriptor,
                required=required,
                binding_metadata=binding_metadata,
            ),
            in_binding=self.in_binding,
            out_binding=self.out_binding,
        )


def _resolve_runtime_client(client: Any | None) -> Any:
    if client is not None:
        return client
    from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client

    resolved = get_scoped_runtime_client()
    if resolved is None:
        raise RuntimeError(
            "flownet_session_scope_required:"
            " provide client=... or use `with v1.connect(...):` / `with v1.client_scope(client):`.",
        )
    return resolved


def _resolve_topic_from_binding(binding: Any) -> str | None:
    if binding is None:
        return None
    if isinstance(binding, str):
        normalized = binding.strip()
        return normalized or None
    if isinstance(binding, Mapping):
        for key in ("topic", "topic_uri", "uri"):
            candidate = binding.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    candidate = getattr(binding, "topic_uri", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    candidate = getattr(binding, "uri", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _resolve_ref_namespace(*, namespace: str | None, declaration: Any) -> str | None:
    if namespace is not None:
        return _normalize_required_name(namespace, field_name="namespace")
    candidate = _normalize_optional_text(getattr(declaration, "namespace", None))
    return candidate


def _resolve_namespace(
    *,
    explicit_namespace: Any | None,
    metadata: Mapping[str, Any],
    target: Any,
) -> str | None:
    resolved = _normalize_optional_text(explicit_namespace)
    if resolved is not None:
        return resolved
    metadata_namespace = _normalize_optional_text(metadata.get("namespace"))
    if metadata_namespace is not None:
        return metadata_namespace
    module = _normalize_optional_text(getattr(target, "__module__", None))
    return module


def _build_declaration_id(
    *,
    declaration_kind: str,
    namespace: str | None,
    uri: str | None,
    dsl_name: str | None,
    target: Any,
) -> str:
    normalized_kind = _normalize_required_name(
        declaration_kind, field_name="declaration_kind"
    ).lower()
    normalized_namespace = _normalize_required_name(
        namespace or "global", field_name="namespace"
    ).lower()
    identity_token = (
        _normalize_optional_text(uri)
        or _normalize_optional_text(dsl_name)
        or _resolve_callable_hint(target)
        or type(target).__name__
    )
    normalized_token = _sanitize_token(identity_token)
    return f"{normalized_namespace}:{normalized_kind}:{normalized_token}"


def _build_definition_hash(
    *,
    declaration_kind: str,
    target: Any,
    uri: str | None,
    dsl_name: str | None,
    namespace: str | None,
    metadata: Mapping[str, Any],
    policies: Mapping[str, Any],
) -> str:
    payload = {
        "declaration_kind": str(declaration_kind),
        "uri": _normalize_optional_text(uri),
        "dsl_name": _normalize_optional_text(dsl_name),
        "namespace": _normalize_optional_text(namespace),
        "callable": _resolve_callable_hint(target),
        "source": _resolve_source_text(target),
        "metadata": _canonicalize_for_hash(metadata),
        "policies": _canonicalize_for_hash(policies),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _canonicalize_for_hash(raw_value: Any) -> Any:
    if raw_value is None or isinstance(raw_value, (bool, int, float, str)):
        return raw_value
    if isinstance(raw_value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(raw_value.keys(), key=lambda item: str(item)):
            normalized[str(key)] = _canonicalize_for_hash(raw_value[key])
        return normalized
    if isinstance(raw_value, (list, tuple)):
        return [_canonicalize_for_hash(item) for item in raw_value]
    if isinstance(raw_value, set):
        normalized_items = [_canonicalize_for_hash(item) for item in raw_value]
        return sorted(
            normalized_items, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True)
        )
    return repr(raw_value)


def _resolve_source_text(target: Any) -> str | None:
    try:
        source = inspect.getsource(target)
    except Exception:
        source = None
    normalized_source = _normalize_optional_text(source)
    if normalized_source is not None:
        return normalized_source
    code = getattr(target, "__code__", None)
    if code is None:
        return None
    co_code = getattr(code, "co_code", None)
    if isinstance(co_code, (bytes, bytearray)):
        return co_code.hex()
    return None


def _resolve_callable_hint(raw_value: Any) -> str | None:
    if not callable(raw_value):
        return None
    module = _normalize_optional_text(getattr(raw_value, "__module__", None))
    qualname = _normalize_optional_text(getattr(raw_value, "__qualname__", None))
    if module is None or qualname is None:
        return None
    return f"{module}:{qualname}"


def _sanitize_token(raw_value: str) -> str:
    cleaned = "".join(
        char if (char.isalnum() or char in "._:-") else "-" for char in str(raw_value)
    ).strip("-.")
    return cleaned or "default"


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_required_name(value: Any, *, field_name: str) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


def _normalize_optional_method_name(value: Any) -> str | None:
    return _normalize_optional_text(value)


def _normalize_non_empty_method_name(value: Any) -> str:
    normalized = _normalize_optional_method_name(value)
    if normalized is None:
        raise ValueError("actor method name must be a non-empty string.")
    return normalized


def _normalize_optional_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping when provided.")
    return dict(value)


def _normalize_selector(value: Any) -> str:
    normalized = _normalize_required_name(value, field_name="selector").lower()
    if normalized not in {"find", "locate"}:
        raise ValueError("selector must be one of: find, locate.")
    return normalized


def _deep_merge_mapping(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping):
            base_value = merged.get(key)
            if isinstance(base_value, Mapping):
                merged[str(key)] = _deep_merge_mapping(dict(base_value), value)
            else:
                merged[str(key)] = dict(value)
            continue
        merged[str(key)] = value
    return merged


def _resolve_replica_count(materialization_policy_override: Mapping[str, Any]) -> int:
    replica_policy = materialization_policy_override.get("replica_policy")
    if not isinstance(replica_policy, Mapping):
        return 1
    raw_count = replica_policy.get("count")
    if raw_count is None:
        return 1
    try:
        count = int(raw_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("replica_policy.count must be an integer when provided.") from exc
    if count < 1:
        raise ValueError("replica_policy.count must be >= 1 when provided.")
    return count


__all__ = [
    "ActorMethodSymbolRef",
    "ActorDeclaration",
    "BoundActorDeclaration",
    "BoundFlowDeclaration",
    "BoundFlowTemplate",
    "BoundServiceDeclaration",
    "BoundSourceDeclaration",
    "Declaration",
    "FlowDeclaration",
    "GroupPolicyDefault",
    "NamedActorDeclarationRef",
    "NamedFlowDeclarationRef",
    "ProcessDeclaration",
    "ServiceDeclaration",
    "ServiceStyle",
    "SourceDeclaration",
    "StatelessDeclaration",
]
