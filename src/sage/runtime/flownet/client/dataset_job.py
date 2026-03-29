from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sage.runtime.flownet.api.declarations import ServiceDeclaration, SourceDeclaration
from sage.runtime.flownet.client.handles import InstanceHandle
from sage.runtime.flownet.client.runtime_client import V1RuntimeClient, build_runtime_client
from sage.runtime.flownet.compiler import compile_flow_program
from sage.runtime.flownet.core import FlowProgram

DATASET_CANONICAL_TOPOLOGY = (
    "source",
    "ingress_topic",
    "flow",
    "egress_topic",
    "egress_connector",
)

DATASET_JOB_SPEC_INVALID = "dataset_job_spec_invalid"
DATASET_JOB_FLOW_REQUIRED = "dataset_job_flow_required"
DATASET_JOB_FLOW_INVALID = "dataset_job_flow_invalid"
DATASET_JOB_TOPIC_INVALID = "dataset_job_topic_invalid"
DATASET_JOB_PLAN_INVALID = "dataset_job_plan_invalid"
DATASET_JOB_SOURCE_INVALID = "dataset_job_source_invalid"
DATASET_JOB_OUTPUT_INVALID = "dataset_job_output_invalid"
# Backward-compatible alias kept for S3-3 callers.
DATASET_JOB_EGRESS_INVALID = DATASET_JOB_OUTPUT_INVALID

DATASET_OUTPUT_MODE_SINK = "sink"
DATASET_OUTPUT_MODE_CONSUMER = "consumer"
DATASET_OUTPUT_MODE_COLLECT = "collect"

_DATASET_OUTPUT_MODES = {
    DATASET_OUTPUT_MODE_SINK,
    DATASET_OUTPUT_MODE_CONSUMER,
    DATASET_OUTPUT_MODE_COLLECT,
}
_DATASET_SOURCE_MODE_STREAM = "stream"
_TOPIC_BASE_RE = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class DatasetJobPlan:
    plan_id: str
    topology: tuple[str, str, str, str, str]
    dataset: dict[str, Any]
    source: dict[str, Any]
    flow: dict[str, Any]
    topics: dict[str, str]
    output: dict[str, Any]
    flow_program: FlowProgram
    source_declaration: SourceDeclaration
    output_declaration: ServiceDeclaration | None = None

    @property
    def egress(self) -> dict[str, Any]:
        return self.output

    @property
    def egress_declaration(self) -> ServiceDeclaration | None:
        return self.output_declaration

    def explain(self) -> dict[str, Any]:
        payload = {
            "plan_id": self.plan_id,
            "topology": list(self.topology),
            "dataset": dict(self.dataset),
            "source_uri": self.source.get("uri"),
            "flow_uri": self.flow.get("uri"),
            "ingress_topic": self.topics.get("ingress_topic"),
            "egress_topic": self.topics.get("egress_topic"),
            "output_mode": self.output.get("mode"),
            "output_kind": self.output.get("kind"),
            "output_uri": self.output.get("uri"),
            # Backward-compatible key for S3-3 snapshots.
            "egress_kind": self.output.get("kind"),
        }
        collect_limits = self.output.get("collect")
        if isinstance(collect_limits, Mapping):
            payload["collect"] = dict(collect_limits)
        return payload


@dataclass
class DatasetJobHandle:
    plan: DatasetJobPlan
    client: V1RuntimeClient
    source_instance: InstanceHandle
    flow_instance: InstanceHandle
    output_instance: InstanceHandle | None = None
    status: str = "running"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def egress_instance(self) -> InstanceHandle | None:
        return self.output_instance

    def stop(self) -> dict[str, bool]:
        source_stopped = self.client.stop_source(self.source_instance)
        self.client.unbind_flow_process(self.flow_instance)
        output_stopped = True
        if self.output_instance is not None:
            output_stopped = self.client.stop_service(self.output_instance)
        self.status = "stopped"
        return {
            "source_stopped": source_stopped,
            "output_stopped": output_stopped,
            # Backward-compatible key for S3-3 stop snapshots.
            "egress_stopped": output_stopped,
        }

    def snapshot(self) -> dict[str, Any]:
        output_instance_id = (
            self.output_instance.instance_id if self.output_instance is not None else None
        )
        return {
            "plan_id": self.plan.plan_id,
            "status": self.status,
            "topology": list(self.plan.topology),
            "source_instance_id": self.source_instance.instance_id,
            "flow_instance_id": self.flow_instance.instance_id,
            "output_instance_id": output_instance_id,
            # Backward-compatible key for S3-3 snapshots.
            "egress_instance_id": output_instance_id,
            "ingress_topic": self.plan.topics["ingress_topic"],
            "egress_topic": self.plan.topics["egress_topic"],
        }


def build_dataset_job(
    spec: Mapping[str, Any],
    *,
    id_factory: Callable[[], str] | None = None,
) -> DatasetJobPlan:
    if not isinstance(spec, Mapping):
        raise TypeError(build_dataset_job_error(DATASET_JOB_SPEC_INVALID, field="spec"))
    if "pipeline" in spec:
        raise ValueError(
            build_dataset_job_error(
                DATASET_JOB_SPEC_INVALID,
                field="pipeline",
                reason="removed_in_r6",
            )
        )

    token_factory = id_factory or (lambda: uuid.uuid4().hex)
    plan_id = _normalize_non_empty(token_factory(), field_name="plan_id")

    dataset = _normalize_dataset_spec(spec.get("dataset"))

    flow_payload = _normalize_flow_spec(spec.get("flow"))
    flow_program = _coerce_flow_program(flow_payload["declaration"])
    flow_uri = _normalize_optional_non_empty(flow_payload.get("uri"))
    if flow_uri is None:
        flow_uri = _normalize_optional_non_empty(getattr(flow_program, "flow_uri", None))
    if flow_uri is None:
        flow_uri = f"flow://dataset-jobs/{plan_id}"
    flow_payload["uri"] = flow_uri

    topic_base = _derive_topic_base(flow_uri)
    topics = _normalize_topic_spec(spec.get("topics"), topic_base=topic_base)

    source_payload = _normalize_source_spec(
        spec.get("source"),
        default_uri=f"source://dataset-jobs/{plan_id}",
        dataset=dataset,
    )
    output_payload, output_declaration = _normalize_output_spec(
        raw_output=spec.get("output"),
        has_output_key="output" in spec,
        raw_egress=spec.get("egress"),
        has_legacy_egress_key="egress" in spec,
        default_uri=f"service://dataset-jobs/{plan_id}/output",
        source_mode=_normalize_optional_non_empty(source_payload.get("mode")),
    )

    return DatasetJobPlan(
        plan_id=plan_id,
        topology=DATASET_CANONICAL_TOPOLOGY,
        dataset=dataset,
        source=source_payload,
        flow=flow_payload,
        topics=topics,
        output=output_payload,
        flow_program=flow_program,
        source_declaration=source_payload["declaration"],
        output_declaration=output_declaration,
    )


def submit_dataset_job(
    plan: DatasetJobPlan,
    *,
    client: V1RuntimeClient | None = None,
    owner: str = "dataset-job-owner",
) -> DatasetJobHandle:
    if not isinstance(plan, DatasetJobPlan):
        raise TypeError(build_dataset_job_error(DATASET_JOB_PLAN_INVALID, field="plan"))

    resolved_client = client or build_runtime_client(owner=owner)

    source_options = dict(plan.source.get("options", {}))
    source_options.setdefault("out_topic", plan.topics["ingress_topic"])
    source_mode = _normalize_optional_non_empty(plan.source.get("mode"))
    if source_mode is not None:
        source_options.setdefault("mode", source_mode)
    source_instance = resolved_client.sources.start(
        plan.source_declaration,
        config=dict(plan.source.get("config", {})),
        policies=dict(plan.source.get("policies", {})),
        **source_options,
    )

    flow_options = dict(plan.flow.get("options", {}))
    flow_options.setdefault("in_topic", plan.topics["ingress_topic"])
    flow_options.setdefault("out_topic", plan.topics["egress_topic"])
    flow_registration = resolved_client.flows.register(
        plan.flow_program,
        uri=plan.flow["uri"],
    )
    flow_instance = resolved_client.flows.instantiate(
        flow_registration,
        config=dict(plan.flow.get("config", {})),
        policies=dict(plan.flow.get("policies", {})),
        **flow_options,
    )

    output_instance: InstanceHandle | None = None
    if plan.output_declaration is not None:
        output_options = dict(plan.output.get("options", {}))
        output_options.setdefault("subscriptions", [plan.topics["egress_topic"]])
        output_options.setdefault("mode", plan.output.get("mode", DATASET_OUTPUT_MODE_SINK))
        collect_limits = plan.output.get("collect")
        if isinstance(collect_limits, Mapping):
            output_options.setdefault("max_rows", int(collect_limits["max_rows"]))
            output_options.setdefault("max_bytes", int(collect_limits["max_bytes"]))
            output_options.setdefault("timeout", float(collect_limits["timeout"]))
        output_instance = resolved_client.services.start(
            plan.output_declaration,
            config=dict(plan.output.get("config", {})),
            policies=dict(plan.output.get("policies", {})),
            **output_options,
        )

    return DatasetJobHandle(
        plan=plan,
        client=resolved_client,
        source_instance=source_instance,
        flow_instance=flow_instance,
        output_instance=output_instance,
    )


def build_dataset_job_error(code: str, **fields: Any) -> str:
    normalized_code = _normalize_non_empty(code, field_name="code")
    if not fields:
        return normalized_code
    parts = [f"{key}={fields[key]}" for key in sorted(fields)]
    return f"{normalized_code}:{','.join(parts)}"


def _normalize_dataset_spec(raw_dataset: Any) -> dict[str, Any]:
    if raw_dataset is None:
        raise ValueError(build_dataset_job_error(DATASET_JOB_SPEC_INVALID, field="dataset"))
    if isinstance(raw_dataset, Mapping):
        return dict(raw_dataset)
    if isinstance(raw_dataset, str):
        normalized_uri = _normalize_non_empty(raw_dataset, field_name="dataset")
        return {"uri": normalized_uri}
    raise TypeError(
        build_dataset_job_error(
            DATASET_JOB_SPEC_INVALID,
            field="dataset",
            actual_type=type(raw_dataset).__name__,
        )
    )


def _normalize_flow_spec(raw_flow: Any) -> dict[str, Any]:
    if raw_flow is None:
        raise ValueError(build_dataset_job_error(DATASET_JOB_FLOW_REQUIRED))

    if isinstance(raw_flow, Mapping):
        declaration = raw_flow.get("declaration")
        if declaration is None:
            declaration = raw_flow.get("program")
        if declaration is None:
            declaration = raw_flow.get("flow")
        if declaration is None:
            raise ValueError(
                build_dataset_job_error(DATASET_JOB_FLOW_REQUIRED, field="flow.declaration")
            )
        payload = {
            "declaration": declaration,
            "uri": raw_flow.get("uri"),
            "config": _normalize_optional_mapping(raw_flow.get("config"), field_name="flow.config"),
            "policies": _normalize_optional_mapping(
                raw_flow.get("policies"),
                field_name="flow.policies",
            ),
            "options": _normalize_optional_mapping(
                raw_flow.get("options"), field_name="flow.options"
            ),
        }
        return payload

    return {
        "declaration": raw_flow,
        "config": {},
        "policies": {},
        "options": {},
    }


def _coerce_flow_program(raw_flow: Any) -> FlowProgram:
    if isinstance(raw_flow, FlowProgram):
        return raw_flow
    try:
        return compile_flow_program(raw_flow)
    except Exception as exc:
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_FLOW_INVALID,
                actual_type=type(raw_flow).__name__,
            )
        ) from exc


def _normalize_topic_spec(
    raw_topics: Any,
    *,
    topic_base: str,
) -> dict[str, str]:
    if raw_topics is None:
        raw_topics = {}
    if not isinstance(raw_topics, Mapping):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_TOPIC_INVALID,
                field="topics",
                actual_type=type(raw_topics).__name__,
            )
        )

    ingress_topic = _normalize_optional_non_empty(
        raw_topics.get("ingress_topic", raw_topics.get("in_topic"))
    )
    egress_topic = _normalize_optional_non_empty(
        raw_topics.get("egress_topic", raw_topics.get("out_topic"))
    )

    return {
        "ingress_topic": ingress_topic or f"topic:{topic_base}.ingress",
        "egress_topic": egress_topic or f"topic:{topic_base}.egress",
    }


def _normalize_source_spec(
    raw_source: Any,
    *,
    default_uri: str,
    dataset: dict[str, Any],
) -> dict[str, Any]:
    if raw_source is None:
        raw_source = {}
    if not isinstance(raw_source, Mapping):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_SOURCE_INVALID,
                field="source",
                actual_type=type(raw_source).__name__,
            )
        )

    source_uri = _normalize_optional_non_empty(raw_source.get("uri")) or default_uri
    declaration = raw_source.get("declaration")
    if declaration is None:
        declaration = _autogenerated_source_declaration(uri=source_uri, dataset=dataset)
    if not isinstance(declaration, SourceDeclaration):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_SOURCE_INVALID,
                field="source.declaration",
                actual_type=type(declaration).__name__,
            )
        )

    return {
        "uri": source_uri,
        "declaration": declaration,
        "config": _normalize_optional_mapping(raw_source.get("config"), field_name="source.config"),
        "policies": _normalize_optional_mapping(
            raw_source.get("policies"),
            field_name="source.policies",
        ),
        "options": _normalize_optional_mapping(
            raw_source.get("options"), field_name="source.options"
        ),
        "mode": _normalize_optional_non_empty(raw_source.get("mode")),
    }


def _normalize_output_spec(
    *,
    raw_output: Any,
    has_output_key: bool,
    raw_egress: Any,
    has_legacy_egress_key: bool,
    default_uri: str,
    source_mode: str | None,
) -> tuple[dict[str, Any], ServiceDeclaration | None]:
    if has_output_key:
        resolved_spec = raw_output
    elif has_legacy_egress_key:
        resolved_spec = _normalize_legacy_egress_as_output(raw_egress)
    else:
        resolved_spec = {"mode": DATASET_OUTPUT_MODE_SINK, "kind": "none"}

    if resolved_spec is None:
        resolved_spec = {"mode": DATASET_OUTPUT_MODE_SINK, "kind": "none"}
    if not isinstance(resolved_spec, Mapping):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output",
                actual_type=type(resolved_spec).__name__,
            )
        )

    output_spec = dict(resolved_spec)
    mode = _normalize_optional_non_empty(output_spec.get("mode")) or DATASET_OUTPUT_MODE_SINK
    mode = mode.lower()
    if mode not in _DATASET_OUTPUT_MODES:
        raise ValueError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.mode",
                actual_value=mode,
            )
        )

    if mode == DATASET_OUTPUT_MODE_SINK:
        return _normalize_sink_output_spec(output_spec, default_uri=default_uri)
    if mode == DATASET_OUTPUT_MODE_CONSUMER:
        return _normalize_consumer_output_spec(output_spec, default_uri=default_uri)
    return _normalize_collect_output_spec(
        output_spec,
        default_uri=default_uri,
        source_mode=source_mode,
    )


def _normalize_sink_output_spec(
    raw_output: Mapping[str, Any],
    *,
    default_uri: str,
) -> tuple[dict[str, Any], ServiceDeclaration | None]:
    kind = _normalize_non_empty(raw_output.get("kind", "none"), field_name="output.kind").lower()
    output_uri = _normalize_optional_non_empty(raw_output.get("uri")) or default_uri
    declaration: ServiceDeclaration | None
    if kind == "none":
        declaration = None
    else:
        declaration = raw_output.get("declaration")
        if declaration is None:
            declaration = _autogenerated_output_declaration(
                uri=output_uri,
                mode=DATASET_OUTPUT_MODE_SINK,
                kind=kind,
            )
        if not isinstance(declaration, ServiceDeclaration):
            raise TypeError(
                build_dataset_job_error(
                    DATASET_JOB_OUTPUT_INVALID,
                    field="output.declaration",
                    actual_type=type(declaration).__name__,
                )
            )

    payload = {
        "mode": DATASET_OUTPUT_MODE_SINK,
        "kind": kind,
        "uri": output_uri,
        "config": _normalize_optional_mapping(raw_output.get("config"), field_name="output.config"),
        "policies": _normalize_optional_mapping(
            raw_output.get("policies"),
            field_name="output.policies",
        ),
        "options": _normalize_optional_mapping(
            raw_output.get("options"), field_name="output.options"
        ),
    }
    return payload, declaration


def _normalize_consumer_output_spec(
    raw_output: Mapping[str, Any],
    *,
    default_uri: str,
) -> tuple[dict[str, Any], ServiceDeclaration]:
    if "callback" in raw_output:
        raise ValueError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.callback",
                reason="unmanaged_callback_not_allowed",
            )
        )

    kind = _normalize_non_empty(
        raw_output.get("kind", "managed_topic_consumer"),
        field_name="output.kind",
    ).lower()
    output_uri = _normalize_optional_non_empty(raw_output.get("uri")) or default_uri
    declaration = raw_output.get("declaration")
    if declaration is None:
        declaration = _autogenerated_output_declaration(
            uri=output_uri,
            mode=DATASET_OUTPUT_MODE_CONSUMER,
            kind=kind,
        )
    if not isinstance(declaration, ServiceDeclaration):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.declaration",
                actual_type=type(declaration).__name__,
            )
        )

    options = _normalize_optional_mapping(raw_output.get("options"), field_name="output.options")
    options.setdefault("managed", True)
    if options["managed"] is not True:
        raise ValueError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.options.managed",
                reason="must_be_true",
            )
        )
    consumer_id = _normalize_optional_non_empty(raw_output.get("consumer_id"))
    if consumer_id is not None:
        options.setdefault("consumer_id", consumer_id)

    payload = {
        "mode": DATASET_OUTPUT_MODE_CONSUMER,
        "kind": kind,
        "uri": output_uri,
        "config": _normalize_optional_mapping(raw_output.get("config"), field_name="output.config"),
        "policies": _normalize_optional_mapping(
            raw_output.get("policies"),
            field_name="output.policies",
        ),
        "options": options,
    }
    return payload, declaration


def _normalize_collect_output_spec(
    raw_output: Mapping[str, Any],
    *,
    default_uri: str,
    source_mode: str | None,
) -> tuple[dict[str, Any], ServiceDeclaration]:
    collect_limits = _normalize_collect_limits(raw_output)
    if source_mode == _DATASET_SOURCE_MODE_STREAM and not collect_limits["allow_stream"]:
        raise ValueError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.collect.allow_stream",
                reason="stream_mode_requires_explicit_opt_in",
            )
        )

    output_uri = _normalize_optional_non_empty(raw_output.get("uri")) or f"{default_uri}/collect"
    declaration = raw_output.get("declaration")
    if declaration is None:
        declaration = _autogenerated_output_declaration(
            uri=output_uri,
            mode=DATASET_OUTPUT_MODE_COLLECT,
            kind="collect",
        )
    if not isinstance(declaration, ServiceDeclaration):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.declaration",
                actual_type=type(declaration).__name__,
            )
        )

    payload = {
        "mode": DATASET_OUTPUT_MODE_COLLECT,
        "kind": "collect",
        "uri": output_uri,
        "config": _normalize_optional_mapping(raw_output.get("config"), field_name="output.config"),
        "policies": _normalize_optional_mapping(
            raw_output.get("policies"),
            field_name="output.policies",
        ),
        "options": _normalize_optional_mapping(
            raw_output.get("options"), field_name="output.options"
        ),
        "collect": collect_limits,
    }
    return payload, declaration


def _normalize_collect_limits(raw_output: Mapping[str, Any]) -> dict[str, Any]:
    raw_collect = raw_output.get("collect")
    if raw_collect is None:
        raw_collect = raw_output
    if not isinstance(raw_collect, Mapping):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="output.collect",
                actual_type=type(raw_collect).__name__,
            )
        )
    collect_mapping = dict(raw_collect)
    allow_stream_raw = collect_mapping.get("allow_stream", raw_output.get("allow_stream", False))
    return {
        "max_rows": _normalize_positive_int(
            collect_mapping.get("max_rows"), field_name="output.collect.max_rows"
        ),
        "max_bytes": _normalize_positive_int(
            collect_mapping.get("max_bytes"),
            field_name="output.collect.max_bytes",
        ),
        "timeout": _normalize_positive_float(
            collect_mapping.get("timeout"), field_name="output.collect.timeout"
        ),
        "allow_stream": _normalize_boolean(
            allow_stream_raw, field_name="output.collect.allow_stream"
        ),
    }


def _normalize_legacy_egress_as_output(raw_egress: Any) -> dict[str, Any]:
    if raw_egress is None:
        return {"mode": DATASET_OUTPUT_MODE_SINK, "kind": "none"}
    if not isinstance(raw_egress, Mapping):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_OUTPUT_INVALID,
                field="egress",
                actual_type=type(raw_egress).__name__,
            )
        )
    payload = dict(raw_egress)
    payload.setdefault("mode", DATASET_OUTPUT_MODE_SINK)
    return payload


def _autogenerated_source_declaration(
    *,
    uri: str,
    dataset: dict[str, Any],
) -> SourceDeclaration:
    def _source_target() -> None:
        _ = dict(dataset)
        return None

    return SourceDeclaration(
        target=_source_target,
        uri=uri,
        metadata={"generated": True, "kind": "dataset_source"},
        dsl_name=_source_target.__name__,
    )


def _autogenerated_output_declaration(
    *,
    uri: str,
    mode: str,
    kind: str,
) -> ServiceDeclaration:
    def _output_target() -> None:
        return None

    return ServiceDeclaration(
        target=_output_target,
        uri=uri,
        metadata={
            "generated": True,
            "output_mode": mode,
            "output_kind": kind,
        },
        dsl_name=_output_target.__name__,
    )


def _derive_topic_base(flow_uri: str) -> str:
    base = _TOPIC_BASE_RE.sub("-", flow_uri.strip()).strip("-.")
    if not base:
        base = "dataset-job"
    return base.lower()


def _normalize_optional_mapping(raw_value: Any, *, field_name: str) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError(
            build_dataset_job_error(
                DATASET_JOB_SPEC_INVALID,
                field=field_name,
                actual_type=type(raw_value).__name__,
            )
        )
    return dict(raw_value)


def _normalize_positive_int(raw_value: Any, *, field_name: str) -> int:
    if not isinstance(raw_value, int) or isinstance(raw_value, bool) or raw_value <= 0:
        raise ValueError(build_dataset_job_error(DATASET_JOB_OUTPUT_INVALID, field=field_name))
    return int(raw_value)


def _normalize_positive_float(raw_value: Any, *, field_name: str) -> float:
    if raw_value is None:
        raise ValueError(build_dataset_job_error(DATASET_JOB_OUTPUT_INVALID, field=field_name))
    if isinstance(raw_value, bool):
        raise ValueError(build_dataset_job_error(DATASET_JOB_OUTPUT_INVALID, field=field_name))
    try:
        normalized = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            build_dataset_job_error(DATASET_JOB_OUTPUT_INVALID, field=field_name)
        ) from exc
    if normalized <= 0:
        raise ValueError(build_dataset_job_error(DATASET_JOB_OUTPUT_INVALID, field=field_name))
    return normalized


def _normalize_boolean(raw_value: Any, *, field_name: str) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    raise ValueError(build_dataset_job_error(DATASET_JOB_OUTPUT_INVALID, field=field_name))


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = [
    "DATASET_CANONICAL_TOPOLOGY",
    "DATASET_JOB_SPEC_INVALID",
    "DATASET_JOB_FLOW_REQUIRED",
    "DATASET_JOB_FLOW_INVALID",
    "DATASET_JOB_TOPIC_INVALID",
    "DATASET_JOB_PLAN_INVALID",
    "DATASET_JOB_SOURCE_INVALID",
    "DATASET_JOB_OUTPUT_INVALID",
    "DATASET_JOB_EGRESS_INVALID",
    "DatasetJobPlan",
    "DatasetJobHandle",
    "build_dataset_job",
    "submit_dataset_job",
    "build_dataset_job_error",
]
