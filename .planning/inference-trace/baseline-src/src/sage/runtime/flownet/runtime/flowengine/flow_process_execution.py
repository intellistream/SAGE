from __future__ import annotations

import inspect
import logging
from collections import deque
from collections.abc import Callable
from threading import Lock
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_ctx import bind_event_cursor
from sage.runtime.flownet.runtime.flowengine.cursor_models import (
    EventCursor,
    FlowProgramRef,
    TopicRef,
)
from sage.runtime.flownet.runtime.flowengine.engine import FlowEngineV1
from sage.runtime.flownet.runtime.flowengine.exception_runner import (
    resolve_exception_for_cursor_sync,
)
from sage.runtime.flownet.runtime.flowengine.operator_executor import (
    CursorStepResult,
    materialize_exception_fallback_step,
)
from sage.runtime.flownet.runtime.flowengine.operator_runtime import (
    CollectiveContractError,
    FlatMapContractError,
    LoopOperatorContractError,
    ProcessTargetResolutionError,
    ReducerContractError,
    ShuffleOperatorContractError,
    StatefulProcessContractError,
    UnsupportedOperatorTypeError,
)
from sage.runtime.flownet.runtime.flowengine.scope_resolver import (
    ProgramScopeRegistry,
    compile_exception_scopes,
)
from sage.runtime.flownet.runtime.topics.coordinator_registry import CoordinatorTopicState
from sage.runtime.flownet.runtime.topics.flow_process_catalog import FlowProcessCatalog
from sage.runtime.flownet.runtime.topics.normalization import _normalize_non_empty
from sage.runtime.flownet.runtime.topics.routing_directory import TopicRouteView

_LOGGER = logging.getLogger(__name__)
_PROCESS_FACTORY_LOG_EXTRA_KEY = "process_factory"
_PROCESS_FACTORY_ERROR_MESSAGE_TOKENS = (
    "missing_flow_program:",
    "flow_program_missing_entry:",
    "process entry nodes must not be empty.",
)
_FACTORY_OUTCOME_META_KEY = "factory_outcome"
_FACTORY_RESOLUTION_MS_META_KEY = "factory_resolution_ms"
_ESCALATION_DEPTH_META_KEY = "escalation_depth"


class FlowProcessExecution:
    """Flowengine-side ingress executor: input event -> out-topic intents."""

    def __init__(
        self,
        *,
        flow_process_catalog: FlowProcessCatalog,
        flow_engine: FlowEngineV1,
        resolve_flow_program: Callable[[FlowProgramRef], Any | None],
        resolve_topic_route: Callable[..., TopicRouteView],
        publish_flow_output: Callable[
            [str, str, Any, dict[str, str] | None, int | None, int | None],
            dict[str, Any],
        ],
        apply_or_forward_event_chain_delta: Callable[
            [str, str, int, int | None],
            dict[str, Any] | None,
        ],
        apply_or_forward_request_outcome: Callable[
            [
                str,
                str,
                str,
                str | None,
                str | None,
                str | None,
                dict[str, Any] | None,
                int | None,
            ],
            dict[str, Any] | None,
        ]
        | None = None,
        invoke_actor_target: Callable[[Any, Any], Any] | None = None,
        invoke_exception_handler: Callable[[Any, dict[str, Any]], Any] | None = None,
        exception_terminal_policy: str = "strict_fail",
        max_cursor_steps: int = 10_000,
    ) -> None:
        self._flow_process_catalog = flow_process_catalog
        self._flow_engine = flow_engine
        self._resolve_flow_program = resolve_flow_program
        self._resolve_topic_route = resolve_topic_route
        self._publish_flow_output = publish_flow_output
        self._apply_or_forward_event_chain_delta = apply_or_forward_event_chain_delta
        self._apply_or_forward_request_outcome = (
            apply_or_forward_request_outcome or _default_apply_or_forward_request_outcome
        )
        self._invoke_actor_target = invoke_actor_target
        self._scope_registry = ProgramScopeRegistry()
        self._invoke_exception_handler = (
            invoke_exception_handler or _default_exception_handler_invoker
        )
        self._exception_terminal_policy = _normalize_exception_terminal_policy(
            exception_terminal_policy,
        )
        self._max_cursor_steps = max(1, int(max_cursor_steps))
        self._process_factory_metrics_lock = Lock()
        self._process_factory_metrics = _new_process_factory_metrics_state()

    def process_factory_metrics_snapshot(self) -> dict[str, Any]:
        with self._process_factory_metrics_lock:
            snapshot = dict(self._process_factory_metrics)

        latency_count = int(snapshot.pop("factory_latency_ms_count", 0))
        latency_sum = float(snapshot.pop("factory_latency_ms_sum", 0.0))
        latency_max = float(snapshot.pop("factory_latency_ms_max", 0.0))
        depth_count = int(snapshot.pop("escalation_depth_count", 0))
        depth_max = int(snapshot.pop("escalation_depth_max", 0))
        latency_avg = (latency_sum / latency_count) if latency_count > 0 else 0.0
        snapshot["factory_latency_ms"] = {
            "count": latency_count,
            "sum": round(latency_sum, 3),
            "avg": round(latency_avg, 3),
            "max": round(latency_max, 3),
        }
        snapshot["escalation_depth"] = {
            "count": depth_count,
            "max": depth_max,
        }
        return snapshot

    def dispatch(
        self,
        *,
        state: CoordinatorTopicState,
        event_group_id: str,
        payload: Any,
        tags: dict[str, str] | None,
        seq: int | None,
    ) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for flow_process_uri in sorted(state.consuming_flow_process_uris):
            reports.append(
                self.execute_flow_process(
                    flow_process_uri=flow_process_uri,
                    event_group_id=event_group_id,
                    payload=payload,
                    tags=tags,
                    seq=seq,
                    in_topic_epoch=state.epoch,
                )
            )
        return reports

    def execute_flow_process(
        self,
        *,
        flow_process_uri: str,
        event_group_id: str,
        payload: Any,
        tags: dict[str, str] | None,
        seq: int | None,
        in_topic_epoch: int | None = None,
    ) -> dict[str, Any]:
        normalized_flow_process_uri = _normalize_non_empty(
            flow_process_uri,
            field_name="flow_process_uri",
        )
        normalized_event_group_id = _normalize_non_empty(
            event_group_id,
            field_name="event_group_id",
        )
        record = self._flow_process_catalog.get(normalized_flow_process_uri)
        if record is None:
            return {
                "flow_process_uri": normalized_flow_process_uri,
                "status": "missing_flow_process_record",
                "error_type": "RuntimeError",
                "message": f"missing_flow_process_record:{normalized_flow_process_uri}",
                "outcome_status": "failed",
                "outcome_error_type": "RuntimeError",
                "outcome_error_message": f"missing_flow_process_record:{normalized_flow_process_uri}",
                "outcome_error_stage": "flow_process_catalog",
                "outcome_metadata": {
                    "flow_process_uri": normalized_flow_process_uri,
                },
                "output_count": 0,
                "event_chain_delta": 0,
                "forward_intents": [],
            }

        execution = self._execute_with_cursor_runtime(
            flow_process_uri=normalized_flow_process_uri,
            flow_program_ref=FlowProgramRef(
                program_uri=record.flow_program_uri,
                program_rev=record.flow_program_rev,
            ),
            in_topic_uri=record.in_topic_uri,
            out_topic_uri=record.out_topic_uri,
            event_group_id=normalized_event_group_id,
            payload=payload,
            tags=tags,
            seq=seq,
            in_topic_epoch=in_topic_epoch,
        )

        out_topic_epoch_raw = execution.get("out_topic_epoch")
        out_topic_epoch = int(out_topic_epoch_raw) if out_topic_epoch_raw is not None else None
        output_count = 0
        forward_intents: list[dict[str, Any]] = []
        for output in execution["outputs"]:
            output_topic_epoch_raw = output.get("convergence_topic_epoch", out_topic_epoch)
            output_topic_epoch = (
                int(output_topic_epoch_raw) if output_topic_epoch_raw is not None else None
            )
            publish_result = self._publish_flow_output(
                record.out_topic_uri,
                normalized_event_group_id,
                output["payload"],
                output["tags"],
                output["seq"],
                output_topic_epoch,
            )
            if publish_result.get("mode") == "local":
                output_count += 1
            else:
                forward_intents.append(publish_result)

        outcome_status = _normalize_outcome_status(
            execution.get("outcome_status", "pending"),
        )
        outcome_error_type = _normalize_optional_non_empty(
            execution.get("outcome_error_type"),
        )
        outcome_error_message = _normalize_optional_non_empty(
            execution.get("outcome_error_message"),
        )
        outcome_error_stage = _normalize_optional_non_empty(
            execution.get("outcome_error_stage"),
        )
        outcome_metadata = (
            dict(execution.get("outcome_metadata") or {})
            if isinstance(execution.get("outcome_metadata"), dict)
            else {}
        )
        # Attach canonical program identity to every outcome for request-level
        # mixed-version observability on coordinator ledgers.
        outcome_metadata.setdefault("flow_process_uri", normalized_flow_process_uri)
        outcome_metadata.setdefault("flow_program_uri", record.flow_program_uri)
        outcome_metadata.setdefault("flow_program_rev", record.flow_program_rev)
        if self._should_emit_error_event(outcome_status):
            error_payload = self._build_flow_error_payload(
                event_group_id=normalized_event_group_id,
                flow_process_uri=normalized_flow_process_uri,
                flow_program_uri=record.flow_program_uri,
                outcome_status=outcome_status,
                outcome_error_type=outcome_error_type,
                outcome_error_message=outcome_error_message,
                outcome_error_stage=outcome_error_stage,
                outcome_metadata=outcome_metadata,
            )
            publish_result = self._publish_flow_output(
                record.out_topic_uri,
                normalized_event_group_id,
                error_payload,
                {"kind": "flow_error"},
                None,
                out_topic_epoch,
            )
            if publish_result.get("mode") == "local":
                output_count += 1
            else:
                forward_intents.append(publish_result)

        event_chain_delta = int(execution["event_chain_delta"])
        if event_chain_delta != 0:
            control_result = self._apply_or_forward_event_chain_delta(
                record.out_topic_uri,
                normalized_event_group_id,
                event_chain_delta,
                out_topic_epoch,
            )
            if control_result is not None:
                forward_intents.append(control_result)

        if self._should_record_outcome():
            outcome_result = self._apply_or_forward_request_outcome(
                record.out_topic_uri,
                normalized_event_group_id,
                outcome_status,
                outcome_error_type,
                outcome_error_message,
                outcome_error_stage,
                outcome_metadata,
                out_topic_epoch,
            )
            if outcome_result is not None:
                forward_intents.append(outcome_result)

        status = "executed"
        if forward_intents:
            status = "executed_with_forward_intents"
        if execution["status"] == "error":
            status = execution["error_status"]
        elif (
            self._exception_terminal_policy == "strict_fail"
            and outcome_status in _OUTCOME_FAILURE_STATUSES
        ):
            status = "cursor_execution_error"
        return {
            "flow_process_uri": normalized_flow_process_uri,
            "flow_program_uri": record.flow_program_uri,
            "status": status,
            "error_type": (
                execution.get("error_type")
                if execution["status"] == "error"
                else outcome_error_type
            ),
            "message": (
                execution.get("message")
                if execution["status"] == "error"
                else outcome_error_message
            ),
            "outcome_status": outcome_status,
            "outcome_error_type": outcome_error_type,
            "outcome_error_message": outcome_error_message,
            "outcome_error_stage": outcome_error_stage,
            "outcome_metadata": outcome_metadata,
            "output_count": output_count,
            "event_chain_delta": event_chain_delta,
            "forward_intents": forward_intents,
        }

    def _execute_with_cursor_runtime(
        self,
        *,
        flow_process_uri: str,
        flow_program_ref: FlowProgramRef,
        in_topic_uri: str,
        out_topic_uri: str,
        event_group_id: str,
        payload: Any,
        tags: dict[str, str] | None,
        seq: int | None,
        in_topic_epoch: int | None,
    ) -> dict[str, Any]:
        out_topic_route = self._resolve_topic_route(out_topic_uri, epoch=None)
        root_program = self._resolve_flow_program(flow_program_ref)
        if root_program is None:
            return {
                "status": "error",
                "error_status": "missing_flow_program_runtime",
                "error_type": "RuntimeError",
                "message": (
                    "missing_flow_program:"
                    f"{flow_program_ref.program_uri}@{flow_program_ref.program_rev}"
                ),
                "outputs": (),
                "event_chain_delta": 0,
                "out_topic_epoch": out_topic_route.epoch,
                "outcome_status": "failed",
                "outcome_error_type": "RuntimeError",
                "outcome_error_message": (
                    "missing_flow_program:"
                    f"{flow_program_ref.program_uri}@{flow_program_ref.program_rev}"
                ),
                "outcome_error_stage": "flow_program_resolution",
                "outcome_metadata": {
                    "flow_program_uri": flow_program_ref.program_uri,
                    "flow_program_rev": flow_program_ref.program_rev,
                },
            }

        root_entry_node_ids = self._resolve_entry_node_ids(root_program)
        if not root_entry_node_ids:
            return {
                "status": "error",
                "error_status": "invalid_flow_program_entry",
                "error_type": "RuntimeError",
                "message": (
                    "flow_program_missing_entry:"
                    f"{flow_program_ref.program_uri}@{flow_program_ref.program_rev}"
                ),
                "outputs": (),
                "event_chain_delta": 0,
                "out_topic_epoch": out_topic_route.epoch,
                "outcome_status": "failed",
                "outcome_error_type": "RuntimeError",
                "outcome_error_message": (
                    "flow_program_missing_entry:"
                    f"{flow_program_ref.program_uri}@{flow_program_ref.program_rev}"
                ),
                "outcome_error_stage": "flow_program_entry_resolution",
                "outcome_metadata": {
                    "flow_program_uri": flow_program_ref.program_uri,
                    "flow_program_rev": flow_program_ref.program_rev,
                },
            }

        in_topic_route = self._resolve_topic_route(in_topic_uri, epoch=in_topic_epoch)
        root_cursor = EventCursor(
            event_group_id=event_group_id,
            event_chain_id=f"{event_group_id}:chain:0",
            flow_program_ref=flow_program_ref,
            pc_node_id=root_entry_node_ids[0],
            flow_stack=(),
            payload=payload,
            tags=dict(tags or {}),
            seq=seq,
            origin_topic_ref=TopicRef(
                topic_uri=in_topic_route.topic_uri,
                coordinator_address=in_topic_route.coordinator_address,
            ),
            convergence_topic_ref=TopicRef(
                topic_uri=out_topic_route.topic_uri,
                coordinator_address=out_topic_route.coordinator_address,
            ),
            convergence_topic_epoch=out_topic_route.epoch,
            meta={"flow_process_uri": flow_process_uri},
        )

        pending: deque[EventCursor] = deque([root_cursor])
        outputs: list[dict[str, Any]] = []
        step_count = 0
        outstanding_event_chains = 1

        try:
            while pending:
                cursor = pending.popleft()
                step_result = self._execute_cursor_step_with_exception_handling(cursor)
                self._observe_process_factory_step(
                    cursor=cursor,
                    step_result=step_result,
                )
                step_count += 1
                if step_count > self._max_cursor_steps:
                    raise RuntimeError(f"cursor_step_limit_exceeded:{self._max_cursor_steps}")
                outstanding_event_chains += int(step_result.event_chain_delta)
                pending.extend(step_result.next_cursors)
                for terminal_payload, terminal_tags in step_result.terminal_outputs:
                    outputs.append(
                        {
                            "payload": terminal_payload,
                            "tags": dict(terminal_tags),
                            "seq": None,
                            "convergence_topic_epoch": cursor.convergence_topic_epoch,
                        }
                    )
        except _TerminalCursorOutcome as terminal:
            return {
                "status": "ok",
                "outputs": tuple(outputs),
                "event_chain_delta": 0,
                "out_topic_epoch": root_cursor.convergence_topic_epoch,
                "outcome_status": terminal.outcome_status,
                "outcome_error_type": terminal.error_type,
                "outcome_error_message": terminal.message,
                "outcome_error_stage": terminal.error_stage,
                "outcome_metadata": dict(terminal.metadata),
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_status": "cursor_execution_error",
                "error_type": exc.__class__.__name__,
                "message": str(exc),
                "outputs": (),
                "event_chain_delta": 0,
                "out_topic_epoch": root_cursor.convergence_topic_epoch,
                "outcome_status": "failed",
                "outcome_error_type": exc.__class__.__name__,
                "outcome_error_message": str(exc),
                "outcome_error_stage": "cursor_execution",
                "outcome_metadata": {
                    "flow_program_uri": flow_program_ref.program_uri,
                    "flow_program_rev": flow_program_ref.program_rev,
                },
            }

        event_chain_delta = max(0, outstanding_event_chains)
        return {
            "status": "ok",
            "outputs": tuple(outputs),
            "event_chain_delta": event_chain_delta,
            "out_topic_epoch": root_cursor.convergence_topic_epoch,
            "outcome_status": "succeeded",
            "outcome_error_type": None,
            "outcome_error_message": None,
            "outcome_error_stage": None,
            "outcome_metadata": {},
        }

    def _execute_cursor_step_with_exception_handling(
        self,
        cursor: EventCursor,
    ) -> CursorStepResult:
        cursor_program = self._resolve_flow_program(cursor.flow_program_ref)
        if cursor_program is None:
            raise RuntimeError(
                "missing_flow_program:"
                f"{cursor.flow_program_ref.program_uri}@{cursor.flow_program_ref.program_rev}",
            )
        with bind_event_cursor(cursor):
            try:
                return self._flow_engine.execute_cursor_step(
                    cursor=cursor,
                    flow_program=cursor_program,
                    invoke_target=self._invoke_target,
                    resolve_process_entry_nodes=self._resolve_process_entry_nodes,
                )
            except (
                UnsupportedOperatorTypeError,
                StatefulProcessContractError,
                ShuffleOperatorContractError,
                ReducerContractError,
                CollectiveContractError,
                LoopOperatorContractError,
                FlatMapContractError,
            ):
                # Advanced operator contract violations are non-recoverable runtime errors.
                raise
            except Exception as exc:
                message = str(exc)
                self._observe_process_factory_error_if_needed(
                    cursor=cursor,
                    flow_program=cursor_program,
                    exc=exc,
                )
                if message.startswith("layer_dispatch_remote_call_error:") or message.startswith(
                    "flow_actor_target_remote_call_error:"
                ):
                    # Remote actor path must fail-fast to avoid silent drops.
                    raise
                return self._resolve_step_exception(
                    cursor=cursor,
                    flow_program=cursor_program,
                    exc=exc,
                )

    def _observe_process_factory_step(
        self,
        *,
        cursor: EventCursor,
        step_result: CursorStepResult,
    ) -> None:
        if not step_result.process_called:
            return
        if not step_result.next_cursors:
            return
        child_meta = step_result.next_cursors[0].meta
        if not isinstance(child_meta, dict):
            return
        outcome = _normalize_optional_non_empty(
            child_meta.get(_FACTORY_OUTCOME_META_KEY),
        )
        if outcome not in {"ok", "fallback"}:
            return
        resolution_ms = _coerce_optional_float(
            child_meta.get(_FACTORY_RESOLUTION_MS_META_KEY),
        )
        escalation_depth = _coerce_optional_non_negative_int(
            child_meta.get(_ESCALATION_DEPTH_META_KEY),
        )
        self._record_process_factory_outcome(
            outcome=outcome,
            resolution_ms=resolution_ms,
            escalation_depth=escalation_depth,
        )
        if outcome != "fallback":
            return
        reason = (
            _normalize_optional_non_empty(child_meta.get("factory_fallback_reason")) or "fallback"
        )
        payload = self._build_process_factory_log_payload(
            cursor=cursor,
            child_meta=child_meta,
            outcome=outcome,
            reason=reason,
        )
        _LOGGER.warning(
            "process_factory_fallback",
            extra={_PROCESS_FACTORY_LOG_EXTRA_KEY: payload},
        )

    def _observe_process_factory_error_if_needed(
        self,
        *,
        cursor: EventCursor,
        flow_program: Any,
        exc: Exception,
    ) -> None:
        transformation = _lookup_transformation_optional(
            flow_program=flow_program,
            pc_node_id=cursor.pc_node_id,
        )
        if not _is_dynamic_process_factory_transformation(transformation):
            return
        if not _is_process_factory_error_exception(exc):
            return
        self._record_process_factory_error()
        payload = self._build_process_factory_log_payload(
            cursor=cursor,
            child_meta=None,
            outcome="error",
            reason=str(exc),
        )
        payload["error_type"] = exc.__class__.__name__
        _LOGGER.error(
            "process_factory_error",
            extra={_PROCESS_FACTORY_LOG_EXTRA_KEY: payload},
        )

    def _record_process_factory_outcome(
        self,
        *,
        outcome: str,
        resolution_ms: float | None,
        escalation_depth: int | None,
    ) -> None:
        with self._process_factory_metrics_lock:
            metrics = self._process_factory_metrics
            metrics["factory_calls_total"] += 1
            if outcome == "ok":
                metrics["factory_success_total"] += 1
            elif outcome == "fallback":
                metrics["factory_fallback_total"] += 1
            if resolution_ms is not None:
                metrics["factory_latency_ms_count"] += 1
                metrics["factory_latency_ms_sum"] += resolution_ms
                metrics["factory_latency_ms_max"] = max(
                    float(metrics["factory_latency_ms_max"]),
                    resolution_ms,
                )
            if escalation_depth is not None:
                metrics["escalation_depth_count"] += 1
                metrics["escalation_depth_max"] = max(
                    int(metrics["escalation_depth_max"]),
                    escalation_depth,
                )

    def _record_process_factory_error(self) -> None:
        with self._process_factory_metrics_lock:
            metrics = self._process_factory_metrics
            metrics["factory_calls_total"] += 1
            metrics["factory_error_total"] += 1

    def _build_process_factory_log_payload(
        self,
        *,
        cursor: EventCursor,
        child_meta: dict[str, Any] | None,
        outcome: str,
        reason: str,
    ) -> dict[str, Any]:
        program_ref = _resolve_log_program_ref(
            cursor=cursor,
            child_meta=child_meta,
        )
        return {
            "event_group_id": cursor.event_group_id,
            "event_chain_id": cursor.event_chain_id,
            "pc_node_id": cursor.pc_node_id,
            "program_ref": program_ref,
            "factory_outcome": outcome,
            "reason": reason,
        }

    def _resolve_step_exception(
        self,
        *,
        cursor: EventCursor,
        flow_program: Any,
        exc: Exception,
    ) -> CursorStepResult:
        event = {
            "kind": "operator_exception",
            "error": exc,
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "event_group_id": cursor.event_group_id,
            "event_chain_id": cursor.event_chain_id,
            "flow_program_uri": cursor.flow_program_ref.program_uri,
            "pc_node_id": cursor.pc_node_id,
            "payload": cursor.payload,
            "tags": dict(cursor.tags),
            "seq": cursor.seq,
            "meta": dict(cursor.meta),
        }
        try:
            resolution = resolve_exception_for_cursor_sync(
                cursor=cursor,
                event=event,
                resolve_scopes=self._resolve_exception_scopes,
                invoke_handler=self._invoke_exception_handler,
            )
        except Exception as resolution_exc:
            raise _TerminalCursorOutcome(
                outcome_status="failed",
                error_type=exc.__class__.__name__,
                message=str(exc),
                error_stage=cursor.pc_node_id,
                metadata={
                    "flow_program_uri": cursor.flow_program_ref.program_uri,
                    "pc_node_id": cursor.pc_node_id,
                    "exception_action": "drop",
                    "resolution_error_type": resolution_exc.__class__.__name__,
                    "resolution_error_message": str(resolution_exc),
                },
            ) from resolution_exc

        if not resolution.handled or resolution.decision is None:
            raise _TerminalCursorOutcome(
                outcome_status="failed",
                error_type=exc.__class__.__name__,
                message=str(exc),
                error_stage=cursor.pc_node_id,
                metadata={
                    "flow_program_uri": cursor.flow_program_ref.program_uri,
                    "pc_node_id": cursor.pc_node_id,
                    "exception_action": "drop",
                    "resolution": "unhandled",
                },
            )

        decision = resolution.decision
        if decision.action == "fallback":
            fallback_payloads = tuple(decision.fallback_payloads or ())
            return materialize_exception_fallback_step(
                cursor=cursor,
                fallback_payloads=fallback_payloads,
                flow_program=flow_program,
            )

        if decision.action in {"drop", "abort"}:
            raise _TerminalCursorOutcome(
                outcome_status=("aborted" if decision.action == "abort" else "failed"),
                error_type=exc.__class__.__name__,
                message=str(exc),
                error_stage=cursor.pc_node_id,
                metadata={
                    "flow_program_uri": cursor.flow_program_ref.program_uri,
                    "pc_node_id": cursor.pc_node_id,
                    "exception_action": decision.action,
                    "decision_metadata": dict(decision.metadata),
                },
            )

        raise _TerminalCursorOutcome(
            outcome_status="failed",
            error_type=exc.__class__.__name__,
            message=str(exc),
            error_stage=cursor.pc_node_id,
            metadata={
                "flow_program_uri": cursor.flow_program_ref.program_uri,
                "pc_node_id": cursor.pc_node_id,
                "exception_action": "drop",
                "resolution": "unknown_decision",
            },
        )

    def _resolve_exception_scopes(self, program_ref: FlowProgramRef):
        try:
            return self._scope_registry.resolve(program_ref)
        except KeyError:
            flow_program = self._resolve_flow_program(program_ref)
            if flow_program is None:
                raise
            compiled_scopes = compile_exception_scopes(flow_program)
            self._scope_registry.register(program_ref, compiled_scopes)
            return compiled_scopes

    def _resolve_process_entry_nodes(self, program_ref: FlowProgramRef) -> tuple[str, ...]:
        flow_program = self._resolve_flow_program(program_ref)
        if flow_program is None:
            raise RuntimeError(
                f"missing_flow_program:{program_ref.program_uri}@{program_ref.program_rev}",
            )
        entry_node_ids = self._resolve_entry_node_ids(flow_program)
        if not entry_node_ids:
            raise RuntimeError(
                f"flow_program_missing_entry:{program_ref.program_uri}@{program_ref.program_rev}",
            )
        return entry_node_ids

    def _resolve_entry_node_ids(self, flow_program: Any) -> tuple[str, ...]:
        resolver = getattr(flow_program, "resolve_entry_transformation", None)
        if callable(resolver):
            entry_transformation = resolver()
            trans_id = getattr(entry_transformation, "trans_id", None)
            if isinstance(trans_id, str) and trans_id.strip():
                return (trans_id.strip(),)
        return ()

    def _invoke_target(
        self, target: Any, payload: Any, tags: dict[str, str], seq: int | None
    ) -> Any:
        if callable(target):
            return _invoke_callable_target(target, payload=payload, tags=tags, seq=seq)
        if self._invoke_actor_target is not None and _is_actor_target_ref(target):
            return self._invoke_actor_target(target, payload)
        raise RuntimeError(f"unsupported_operator_target:{type(target).__name__}")

    def _should_record_outcome(self) -> bool:
        return self._exception_terminal_policy != "legacy_drop"

    def _should_emit_error_event(self, outcome_status: str) -> bool:
        if outcome_status not in _OUTCOME_FAILURE_STATUSES:
            return False
        return self._exception_terminal_policy in {"emit_error_event", "strict_fail"}

    def _build_flow_error_payload(
        self,
        *,
        event_group_id: str,
        flow_process_uri: str,
        flow_program_uri: str,
        outcome_status: str,
        outcome_error_type: str | None,
        outcome_error_message: str | None,
        outcome_error_stage: str | None,
        outcome_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "kind": "flow_error",
            "event_group_id": event_group_id,
            "flow_process_uri": flow_process_uri,
            "flow_program_uri": flow_program_uri,
            "outcome_status": outcome_status,
            "error_type": outcome_error_type or "RuntimeError",
            "message": outcome_error_message or "flow_execution_failed",
            "error_stage": outcome_error_stage or "flow_process_execution",
            "meta": dict(outcome_metadata),
        }


_OUTCOME_FAILURE_STATUSES = frozenset({"failed", "aborted", "dropped"})
_ALLOWED_EXCEPTION_TERMINAL_POLICIES = frozenset(
    {"legacy_drop", "record_only", "emit_error_event", "strict_fail"},
)


class _TerminalCursorOutcome(RuntimeError):
    def __init__(
        self,
        *,
        outcome_status: str,
        error_type: str | None,
        message: str | None,
        error_stage: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or "terminal_cursor_outcome")
        self.outcome_status = _normalize_outcome_status(outcome_status)
        self.error_type = _normalize_optional_non_empty(error_type) or "RuntimeError"
        self.message = _normalize_optional_non_empty(message) or "flow_execution_failed"
        self.error_stage = _normalize_optional_non_empty(error_stage) or "unknown"
        self.metadata = {str(key): value for key, value in dict(metadata or {}).items()}


def _is_actor_target_ref(target: Any) -> bool:
    if isinstance(target, dict):
        if _is_actor_replica_pool_target(target):
            return True
        return all(
            isinstance(target.get(field_name), str) and str(target.get(field_name)).strip()
            for field_name in ("address", "actor_id", "method")
        )
    return all(
        isinstance(getattr(target, field_name, None), str)
        and str(getattr(target, field_name, None)).strip()
        for field_name in ("address", "actor_id", "method")
    )


def _is_actor_replica_pool_target(target: dict[str, Any]) -> bool:
    kind = str(target.get("kind") or "").strip()
    if kind != "actor_replica_pool_ref":
        return False
    method = target.get("method")
    replicas = target.get("replicas")
    if not isinstance(method, str) or not method.strip():
        return False
    if not isinstance(replicas, list) or not replicas:
        return False
    for replica in replicas:
        if not isinstance(replica, dict):
            return False
        address = replica.get("address")
        actor_id = replica.get("actor_id")
        if not isinstance(address, str) or not address.strip():
            return False
        if not isinstance(actor_id, str) or not actor_id.strip():
            return False
    return True


def _invoke_callable_target(
    target: Callable[..., Any],
    *,
    payload: Any,
    tags: dict[str, str],
    seq: int | None,
) -> Any:
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return target(payload)

    positional_capacity = 0
    has_var_positional = False
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            has_var_positional = True
            break
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_capacity += 1
    if has_var_positional:
        return target(payload, tags, seq)
    if positional_capacity >= 3:
        return target(payload, tags, seq)
    if positional_capacity == 2:
        return target(payload, tags)
    if positional_capacity == 1:
        return target(payload)
    return target()


def _default_exception_handler_invoker(handler_target: Any, event: dict[str, Any]) -> Any:
    if callable(handler_target):
        return handler_target(event)
    raise RuntimeError(
        f"unsupported_exception_handler_target:{type(handler_target).__name__}",
    )


def _default_apply_or_forward_request_outcome(
    _out_topic_uri: str,
    _event_group_id: str,
    _outcome_status: str,
    _outcome_error_type: str | None,
    _outcome_error_message: str | None,
    _outcome_error_stage: str | None,
    _outcome_metadata: dict[str, Any] | None,
    _out_topic_epoch: int | None,
) -> dict[str, Any] | None:
    return None


def _normalize_exception_terminal_policy(exception_terminal_policy: str) -> str:
    normalized = (
        _normalize_non_empty(
            exception_terminal_policy,
            field_name="exception_terminal_policy",
        )
        .strip()
        .lower()
    )
    if normalized not in _ALLOWED_EXCEPTION_TERMINAL_POLICIES:
        raise ValueError(f"unsupported_exception_terminal_policy:{normalized}")
    return normalized


def _normalize_optional_non_empty(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_outcome_status(outcome_status: str) -> str:
    normalized = _normalize_non_empty(outcome_status, field_name="outcome_status").strip().lower()
    if normalized not in {"pending", "succeeded", "failed", "aborted", "dropped"}:
        raise ValueError(f"unsupported_outcome_status:{normalized}")
    return normalized


def _new_process_factory_metrics_state() -> dict[str, Any]:
    return {
        "factory_calls_total": 0,
        "factory_success_total": 0,
        "factory_fallback_total": 0,
        "factory_error_total": 0,
        "factory_latency_ms_count": 0,
        "factory_latency_ms_sum": 0.0,
        "factory_latency_ms_max": 0.0,
        "escalation_depth_count": 0,
        "escalation_depth_max": 0,
    }


def _lookup_transformation_optional(*, flow_program: Any, pc_node_id: str) -> Any | None:
    lookup = getattr(flow_program, "lookup_transformation", None)
    if callable(lookup):
        return lookup(pc_node_id)
    transformations = getattr(flow_program, "transformations", None)
    if isinstance(transformations, dict):
        return transformations.get(pc_node_id)
    return None


def _is_dynamic_process_factory_transformation(transformation: Any) -> bool:
    if transformation is None:
        return False
    operator_type = str(getattr(transformation, "type", "")).strip()
    if operator_type != "process":
        return False
    target = getattr(transformation, "target", None)
    if target is None:
        return False
    if _is_canonical_program_ref_like(target):
        return False
    return callable(target) or _is_actor_target_ref(target)


def _is_canonical_program_ref_like(target: Any) -> bool:
    if isinstance(target, dict):
        program_uri = target.get("program_uri")
        program_rev = target.get("program_rev")
    else:
        program_uri = getattr(target, "program_uri", None)
        program_rev = getattr(target, "program_rev", None)
    return (
        isinstance(program_uri, str)
        and program_uri.strip()
        and isinstance(program_rev, str)
        and program_rev.strip()
    )


def _is_process_factory_error_exception(exc: Exception) -> bool:
    if isinstance(exc, ProcessTargetResolutionError):
        return True
    message = str(exc or "")
    if not message:
        return False
    return any(token in message for token in _PROCESS_FACTORY_ERROR_MESSAGE_TOKENS)


def _coerce_optional_float(raw_value: Any) -> float | None:
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except Exception:
        return None
    if value < 0:
        return None
    return value


def _coerce_optional_non_negative_int(raw_value: Any) -> int | None:
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except Exception:
        return None
    if value < 0:
        return None
    return value


def _resolve_log_program_ref(
    *,
    cursor: EventCursor,
    child_meta: dict[str, Any] | None,
) -> dict[str, str]:
    if isinstance(child_meta, dict):
        last_ref = child_meta.get("escalation_last_ref")
        if isinstance(last_ref, dict):
            program_uri = _normalize_optional_non_empty(last_ref.get("program_uri"))
            program_rev = _normalize_optional_non_empty(last_ref.get("program_rev"))
            if program_uri is not None and program_rev is not None:
                return {
                    "program_uri": program_uri,
                    "program_rev": program_rev,
                }
    return {
        "program_uri": cursor.flow_program_ref.program_uri,
        "program_rev": cursor.flow_program_ref.program_rev,
    }


__all__ = ["FlowProcessExecution"]
