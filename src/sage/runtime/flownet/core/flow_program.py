from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.runtime.flownet.compiler.transformation import Transformation


class FlowProgram:
    """
    v1 compiled flow topology.

    This is an independent program model and does not depend on
    compiler.flowtask.FlowProgram/FlowTask.

    v1 execution model notes:
    - FlowProgram is a static topology + program defaults.
    - Runtime invocation is not direct submit/call; it is topic binding.
    - Binding (in_topic -> out_topic) creates a cluster lifecycle object:
      FlowProcess (metadata registration in runtime/topic modules).
    - FlowProcessCatalog and TopicRoutingDirectory are URI/meta views only.
    - In-topic coordinator drives per-input-event flow execution.
    - Internal control signals (event delta/ack/done) converge at out-topic
      coordinator, which decides request completion.
    - Coordinator state is lazily materialized by (topic_uri, epoch) and
      owner-checked by routing snapshot.
    - Control-plane signals are decoupled from data-plane payload routing.
    """

    def __init__(self):
        self.pipeline: list[Transformation] = []
        self.transformations: dict[str, Transformation] = {}
        self.entry_id: str | None = None
        self.entry_ids: list[str] = []
        self._entry_router: Transformation | None = None
        self._exception_handler_stack: list[Any | None] = [None]
        self.return_ids: list[str] = []
        self.sink_ids: list[str] = []
        self.no_return: bool = True
        # Program-level definition metadata. Topic bindings are intentionally
        # outside this object and should be attached in runtime registration APIs.
        # In v1, scheduler/resources/uri belong to program definition, while
        # input/output topic wiring belongs to FlowProcess registration.
        # Coordinator request-ledger state is also outside this object.
        self.flow_uri: str | None = None
        self.scheduler: dict[str, Any] = {}
        self.resources: dict[str, Any] = {}
        self.policies: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}
        self.dsl_name: str | None = None

    def configure(
        self,
        *,
        flow_uri: str | None = None,
        scheduler: Mapping[str, Any] | None = None,
        resources: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        dsl_name: str | None = None,
    ) -> FlowProgram:
        # configure() only sets program-level defaults; it does not create
        # runtime bindings or coordinator registrations.
        if flow_uri is not None:
            normalized_uri = str(flow_uri).strip()
            if not normalized_uri:
                raise ValueError("flow_uri must not be empty when provided.")
            self.flow_uri = normalized_uri
        else:
            self.flow_uri = None
        self.scheduler = dict(scheduler or {})
        self.resources = dict(resources or {})
        self.policies = dict(policies or {})
        self.metadata = dict(metadata or {})
        self.dsl_name = str(dsl_name).strip() if dsl_name is not None else None
        return self

    def append(self, transformation: Transformation) -> None:
        self.pipeline.append(transformation)

    def lookup_transformation(self, trans_id: str) -> Transformation | None:
        return self.transformations.get(trans_id)

    def set_entry_id(self, entry_id: str) -> None:
        if entry_id not in self.entry_ids:
            self.entry_ids.append(entry_id)
        if self.entry_id is None:
            self.entry_id = entry_id
        self._unregister_entry_router()
        self._entry_router = None

    @staticmethod
    def _system_target():
        from sage.runtime.flownet.compiler.targets import system_target

        return system_target()

    def _resolve_entry_transformations(self) -> list[Transformation]:
        entry_ids = list(self.entry_ids)
        if not entry_ids and self.entry_id is not None:
            entry_ids = [self.entry_id]

        entries: list[Transformation] = []
        for trans_id in entry_ids:
            trans = self.lookup_transformation(trans_id)
            if trans is not None:
                entries.append(trans)
        if entries:
            return entries
        if self.pipeline:
            return [self.pipeline[0]]
        return []

    def _register_entry_router(self, router: Transformation) -> None:
        self.transformations[router.trans_id] = router

    def _unregister_entry_router(self) -> None:
        router = self._entry_router
        if router is None:
            return
        self.transformations.pop(router.trans_id, None)

    def resolve_entry_transformation(self) -> Transformation | None:
        entries = self._resolve_entry_transformations()
        if not entries:
            return None
        if len(entries) == 1:
            return entries[0]

        entry_trans_ids = [trans.trans_id for trans in entries]
        router = self._entry_router
        if router is not None:
            routes = (router.operator_config or {}).get("routes") or []
            route_ids = [
                route.get("transformation").trans_id
                for route in routes
                if isinstance(route, dict) and route.get("transformation") is not None
            ]
            if route_ids == entry_trans_ids:
                self._register_entry_router(router)
                return router
            self._unregister_entry_router()

        from sage.runtime.flownet.compiler.transformation import Transformation

        router = Transformation(
            self,
            self._system_target(),
            type="sys/router",
            operator_config={
                "routes": [{"transformation": trans} for trans in entries],
            },
        )
        router.exception_handler_stack = list(self._exception_handler_stack)
        self._entry_router = router
        self._register_entry_router(router)
        return router

    def current_exception_handler(self):
        if not self._exception_handler_stack:
            return None
        return self._exception_handler_stack[-1]

    def mark_return(self, transformation: Transformation) -> None:
        if not transformation.is_return:
            transformation.is_return = True
            self.return_ids.append(transformation.trans_id)
        self.no_return = False

    def mark_sink(self, transformation: Transformation) -> None:
        if not transformation.is_sink:
            transformation.is_sink = True
            self.sink_ids.append(transformation.trans_id)

    @property
    def graph(self) -> FlowProgram:
        return self

    @property
    def task(self) -> FlowProgram:
        return self

    def endpoint(self, *, client=None, **kwargs):
        resolved_client = client
        if resolved_client is None:
            from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client

            resolved_client = get_scoped_runtime_client()
        if resolved_client is None:
            raise RuntimeError(
                "flownet_session_scope_required:"
                " provide client=... or use `with v1.connect(...):` / `with v1.client_scope(client):`.",
            )
        flows_surface = getattr(resolved_client, "flows", None)
        endpoint_fn = getattr(flows_surface, "endpoint", None)
        if not callable(endpoint_fn):
            raise RuntimeError("v1_endpoint_client_surface_missing_flows_endpoint")
        return endpoint_fn(self, **kwargs)

    def publish(
        self,
        *,
        client=None,
        name: str,
        namespace: str | None = None,
        version: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        in_topic: str | None = None,
        out_topic: str | None = None,
        reuse_existing: bool = True,
        config: Mapping[str, Any] | None = None,
        policies: Mapping[str, Any] | None = None,
    ):
        resolved_client = client
        if resolved_client is None:
            from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client

            resolved_client = get_scoped_runtime_client()
        if resolved_client is None:
            raise RuntimeError(
                "flownet_session_scope_required:"
                " provide client=... or use `with v1.connect(...):` / `with v1.client_scope(client):`.",
            )
        publish_fn = getattr(resolved_client, "publish_flow_endpoint", None)
        if not callable(publish_fn):
            raise RuntimeError("v1_endpoint_client_surface_missing_publish_flow_endpoint")
        return publish_fn(
            self,
            name=name,
            namespace=namespace,
            version=version,
            metadata=metadata,
            in_topic=in_topic,
            out_topic=out_topic,
            reuse_existing=reuse_existing,
            config=config,
            policies=policies,
        )

    def find_endpoint(
        self,
        *,
        client=None,
        name: str,
        namespace: str | None = None,
    ):
        resolved_client = client
        if resolved_client is None:
            from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client

            resolved_client = get_scoped_runtime_client()
        if resolved_client is None:
            raise RuntimeError(
                "flownet_session_scope_required:"
                " provide client=... or use `with v1.connect(...):` / `with v1.client_scope(client):`.",
            )
        find_fn = getattr(resolved_client, "find_flow_endpoint", None)
        if not callable(find_fn):
            raise RuntimeError("v1_endpoint_client_surface_missing_find_flow_endpoint")
        return find_fn(
            name=name,
            namespace=namespace,
            flow_uri=self.flow_uri,
        )

    def inspect_endpoint(
        self,
        *,
        client=None,
        endpoint_id: str | None = None,
        name: str | None = None,
        namespace: str | None = None,
    ):
        resolved_client = client
        if resolved_client is None:
            from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client

            resolved_client = get_scoped_runtime_client()
        if resolved_client is None:
            raise RuntimeError(
                "flownet_session_scope_required:"
                " provide client=... or use `with v1.connect(...):` / `with v1.client_scope(client):`.",
            )
        inspect_fn = getattr(resolved_client, "inspect_flow_endpoint", None)
        if not callable(inspect_fn):
            raise RuntimeError("v1_endpoint_client_surface_missing_inspect_flow_endpoint")
        return inspect_fn(
            endpoint_id=endpoint_id,
            name=name,
            namespace=namespace,
            flow_uri=self.flow_uri,
        )

    def list_endpoints(
        self,
        *,
        client=None,
        namespace: str | None = None,
        include_released: bool = True,
    ):
        resolved_client = client
        if resolved_client is None:
            from sage.runtime.flownet.client.runtime_client import get_scoped_runtime_client

            resolved_client = get_scoped_runtime_client()
        if resolved_client is None:
            raise RuntimeError(
                "flownet_session_scope_required:"
                " provide client=... or use `with v1.connect(...):` / `with v1.client_scope(client):`.",
            )
        list_fn = getattr(resolved_client, "list_flow_endpoints", None)
        if not callable(list_fn):
            raise RuntimeError("v1_endpoint_client_surface_missing_list_flow_endpoints")
        return list_fn(
            namespace=namespace,
            flow_uri=self.flow_uri,
            include_released=include_released,
        )

    def call(self, payload, *, client=None, timeout: float = 5.0, **kwargs):
        return self.endpoint(client=client, **kwargs).call(payload, timeout=timeout)

    def open_request(
        self,
        *,
        client=None,
        request_id: str | None = None,
        tags: Mapping[str, str] | None = None,
        **kwargs,
    ):
        return self.endpoint(client=client, **kwargs).open_request(
            request_id=request_id,
            tags=tags,
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
        return self.endpoint(client=client, **kwargs).submit(
            payload,
            request_id=request_id,
            tags=tags,
        )

    def __get__(self, instance, owner):
        # v1 does not support descriptor-style bound flow methods (no BoundFlow).
        if instance is not None:
            raise TypeError(
                "v1 FlowProgram does not support class-instance binding. "
                "Define v1 flow DSL as module/static function and bind topics externally.",
            )
        return self


__all__ = [
    "FlowProgram",
]
