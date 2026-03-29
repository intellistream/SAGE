from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Coroutine
from typing import Any

from sage.runtime.flownet.runtime.actors.actor_api import ActorAPI
from sage.runtime.flownet.runtime.comm import OP_RPC_ACTOR_CALL, PLANE_RPC, V1CommHub
from sage.runtime.flownet.runtime.flowengine.cursor_ctx import current_event_meta


def build_actor_payload_target_invoker(
    *,
    actor_api: ActorAPI,
    comm_hub: V1CommHub | None = None,
    timeout: float | None = None,
    run_coroutine: Callable[[Coroutine[Any, Any, Any]], Any] | None = None,
) -> Callable[[Any, Any], Any]:
    """
    Build a sync invoker for flow actor-target execution.

    Contract (payload-first):
    1. actor target receives a single payload argument.
    2. local actor target executes in ActorAPI local runtime.
    3. remote actor target executes through v1 actor-call rpc plane.
    """
    group_replica_index_by_pool: dict[str, dict[str, int]] = {}
    rr_cursor_by_pool: dict[str, int] = {}

    def _runner(coro: Coroutine[Any, Any, Any]) -> Any:
        if callable(run_coroutine):
            return run_coroutine(coro)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "actor_cursor_target_invoker_requires_run_coroutine_when_called_inside_running_event_loop",
        )

    async def _invoke_async(target: Any, payload: Any) -> Any:
        resolved_target = _resolve_target_for_payload(
            target=target,
            payload=payload,
            group_replica_index_by_pool=group_replica_index_by_pool,
            rr_cursor_by_pool=rr_cursor_by_pool,
        )
        prepared = await actor_api.call_or_prepare_call(resolved_target, payload)
        mode = _normalize_non_empty(prepared.get("mode"), field_name="mode")
        if mode == "local_result":
            return prepared.get("result")
        if mode == "actor_call_intent":
            trace = _resolve_remote_trace(prepared=prepared, payload=payload)
            if comm_hub is None:
                raise RuntimeError(
                    _format_remote_call_error(
                        category="missing_comm_hub",
                        trace=trace,
                        error_type="RuntimeError",
                        message="remote_flow_actor_target_requires_comm_hub",
                    )
                )
            try:
                reply = await comm_hub.request(
                    plane=PLANE_RPC,
                    op=OP_RPC_ACTOR_CALL,
                    target_address=trace["target_address"],
                    timeout=timeout,
                    request_ref_id=_normalize_optional_non_empty(trace["request_ref_id"]),
                    body=prepared,
                )
            except Exception as exc:
                raise RuntimeError(
                    _format_remote_call_error(
                        category=_classify_comm_request_error(exc),
                        trace=trace,
                        error_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                ) from exc

            body = reply.body
            if not isinstance(body, dict):
                raise RuntimeError(
                    _format_remote_call_error(
                        category="invalid_reply",
                        trace=trace,
                        error_type="TypeError",
                        message="actor_call_reply_body_must_be_dict",
                    )
                )
            reply_mode = _normalize_non_empty(body.get("mode"), field_name="mode")
            if reply_mode == "applied_actor_call":
                return body.get("result")
            if reply_mode == "applied_actor_call_error":
                error_type = _normalize_non_empty(body.get("error_type"), field_name="error_type")
                message = _normalize_non_empty(body.get("message"), field_name="message")
                raise RuntimeError(
                    _format_remote_call_error(
                        category="remote_exception",
                        trace=trace,
                        error_type=error_type,
                        message=message,
                    )
                )
            raise RuntimeError(
                _format_remote_call_error(
                    category="unsupported_reply_mode",
                    trace=trace,
                    error_type="ValueError",
                    message=f"unsupported_actor_call_reply_mode:{reply_mode}",
                )
            )
        raise RuntimeError(f"unsupported_actor_call_prepare_mode:{mode}")

    def _invoke(target: Any, payload: Any) -> Any:
        coro = _invoke_async(target, payload)
        try:
            return _runner(coro)
        except Exception:
            try:
                coro.close()
            except Exception:
                pass
            raise

    return _invoke


def build_actor_cursor_target_invoker(
    *,
    actor_api: ActorAPI,
    comm_hub: V1CommHub | None = None,
    timeout: float | None = None,
    run_coroutine: Callable[[Coroutine[Any, Any, Any]], Any] | None = None,
) -> Callable[[Any, Any], Any]:
    """
    Compatibility alias.

    This name is kept for one migration window; semantics are payload-first.
    """

    return build_actor_payload_target_invoker(
        actor_api=actor_api,
        comm_hub=comm_hub,
        timeout=timeout,
        run_coroutine=run_coroutine,
    )


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_optional_non_empty(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


def _resolve_remote_trace(*, prepared: dict[str, Any], payload: Any) -> dict[str, str]:
    target_address = _normalize_non_empty(prepared.get("address"), field_name="address")
    actor_id = _normalize_non_empty(prepared.get("actor_id"), field_name="actor_id")
    method = _normalize_non_empty(prepared.get("method"), field_name="method")
    event_group_id = _resolve_event_group_id(payload)
    request_ref_id = event_group_id or _resolve_request_ref_id(payload)
    route_plan_id = _resolve_route_plan_id(payload)
    return {
        "target_address": target_address,
        "actor_id": actor_id,
        "method": method,
        "event_group_id": event_group_id,
        "request_ref_id": request_ref_id,
        "route_plan_id": route_plan_id,
    }


def _resolve_event_group_id(payload: Any) -> str:
    for candidate in (
        _extract_event_group_id_from_cursor_meta(),
        _extract_field_from_payload(payload, "event_group_id"),
        _extract_field_from_payload_metadata(payload, "event_group_id"),
    ):
        if candidate:
            return candidate
    return ""


def _resolve_route_plan_id(payload: Any) -> str:
    for candidate in (
        _extract_field_from_payload(payload, "route_plan_id"),
        _extract_field_from_payload_metadata(payload, "route_plan_id"),
    ):
        if candidate:
            return candidate
    return ""


def _resolve_request_ref_id(payload: Any) -> str:
    for candidate in (
        _extract_field_from_payload(payload, "request_ref_id"),
        _extract_field_from_payload(payload, "request_ref"),
        _extract_field_from_payload_metadata(payload, "request_ref_id"),
        _extract_field_from_payload_metadata(payload, "request_ref"),
    ):
        if candidate:
            return candidate
    return ""


def _extract_field_from_payload(payload: Any, field_name: str) -> str:
    if isinstance(payload, dict):
        return str(payload.get(field_name) or "").strip()
    return str(getattr(payload, field_name, "") or "").strip()


def _extract_field_from_payload_metadata(payload: Any, field_name: str) -> str:
    metadata: Any
    if isinstance(payload, dict):
        metadata = payload.get("metadata")
    else:
        metadata = getattr(payload, "metadata", None)
    if isinstance(metadata, dict):
        return str(metadata.get(field_name) or "").strip()
    return ""


def _extract_event_group_id_from_cursor_meta() -> str:
    meta = current_event_meta()
    if not isinstance(meta, dict):
        return ""
    return str(meta.get("event_group_id") or "").strip()


def _resolve_target_for_payload(
    *,
    target: Any,
    payload: Any,
    group_replica_index_by_pool: dict[str, dict[str, int]],
    rr_cursor_by_pool: dict[str, int],
) -> Any:
    if not isinstance(target, dict):
        return target
    kind = str(target.get("kind") or "").strip()
    if kind != "actor_replica_pool_ref":
        return target
    return _resolve_replica_pool_target(
        target=target,
        payload=payload,
        group_replica_index_by_pool=group_replica_index_by_pool,
        rr_cursor_by_pool=rr_cursor_by_pool,
    )


def _resolve_replica_pool_target(
    *,
    target: dict[str, Any],
    payload: Any,
    group_replica_index_by_pool: dict[str, dict[str, int]],
    rr_cursor_by_pool: dict[str, int],
) -> dict[str, str]:
    method = _normalize_non_empty(target.get("method"), field_name="method")
    replicas = target.get("replicas")
    if not isinstance(replicas, list) or not replicas:
        raise RuntimeError("actor_replica_pool_invalid_replicas")

    normalized_replicas: list[dict[str, str]] = []
    for replica in replicas:
        if not isinstance(replica, dict):
            raise RuntimeError("actor_replica_pool_invalid_replica_entry")
        normalized_replicas.append(
            {
                "address": _normalize_non_empty(replica.get("address"), field_name="address"),
                "actor_id": _normalize_non_empty(replica.get("actor_id"), field_name="actor_id"),
            }
        )

    event_meta = current_event_meta()
    if not isinstance(event_meta, dict):
        raise RuntimeError(
            "actor_replica_requires_flow_context:"
            " replicas>1 symbolic actor target requires bound flow cursor context.",
        )

    keyby_key = _resolve_keyby_route_key(payload=payload, event_meta=event_meta)
    if keyby_key is not None:
        replica_index = int(hashlib.sha1(keyby_key.encode("utf-8")).hexdigest(), 16) % len(
            normalized_replicas
        )
        selected = normalized_replicas[replica_index]
        return {
            "address": selected["address"],
            "actor_id": selected["actor_id"],
            "method": method,
        }

    event_group_id = _resolve_event_group_id(payload)
    if not event_group_id:
        raise RuntimeError(
            "actor_replica_requires_flow_context:"
            " replicas>1 symbolic actor target requires event_group_id.",
        )
    pool_key = _normalize_optional_non_empty(
        target.get("symbol_key")
    ) or _normalize_optional_non_empty(target.get("actor_uri"))
    if pool_key is None:
        pool_key = f"pool:{id(target)}"
    sticky_mapping = group_replica_index_by_pool.setdefault(pool_key, {})
    existing_index = sticky_mapping.get(event_group_id)
    if existing_index is None:
        rr_index = int(rr_cursor_by_pool.get(pool_key, 0))
        existing_index = rr_index % len(normalized_replicas)
        sticky_mapping[event_group_id] = existing_index
        rr_cursor_by_pool[pool_key] = rr_index + 1
    selected = normalized_replicas[int(existing_index)]
    return {
        "address": selected["address"],
        "actor_id": selected["actor_id"],
        "method": method,
    }


def _resolve_keyby_route_key(*, payload: Any, event_meta: dict[str, Any]) -> str | None:
    tags = event_meta.get("tags")
    if isinstance(tags, dict):
        for key_name in ("state_partition_key", "keyby_key"):
            candidate = _normalize_optional_non_empty(tags.get(key_name))
            if candidate is not None:
                return candidate
    for key_name in ("state_partition_key", "keyby_key"):
        candidate = _extract_field_from_payload(payload, key_name)
        if candidate:
            return candidate
        candidate = _extract_field_from_payload_metadata(payload, key_name)
        if candidate:
            return candidate
    return None


def _classify_comm_request_error(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "remote_timeout"
    message = str(exc)
    if message.startswith("comm_request_timeout:"):
        return "remote_timeout"
    if (
        "target_not_found" in message
        or "endpoint_not_found" in message
        or "owner_mismatch" in message
    ):
        return "target_unreachable"
    return "transport_error"


def _format_remote_call_error(
    *,
    category: str,
    trace: dict[str, str],
    error_type: str,
    message: str,
) -> str:
    return (
        "flow_actor_target_remote_call_error:"
        f"category={category},"
        f"target_address={trace['target_address']},"
        f"actor_id={trace['actor_id']},"
        f"method={trace['method']},"
        f"event_group_id={trace['event_group_id']},"
        f"request_ref_id={trace['request_ref_id']},"
        f"route_plan_id={trace['route_plan_id']},"
        f"error_type={str(error_type or '').strip()},"
        f"message={str(message or '').strip()}"
    )


__all__ = [
    "build_actor_payload_target_invoker",
    "build_actor_cursor_target_invoker",
]
