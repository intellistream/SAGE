from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Coroutine
from typing import Any

from sage.runtime.flownet.runtime.actors.actor_api import ActorAPI
from sage.runtime.flownet.runtime.comm import OP_RPC_ACTOR_CALL, PLANE_RPC, V1CommHub
from sage.runtime.flownet.runtime.flowengine.cursor_ctx import current_event_meta


def build_actor_exception_handler_invoker(
    *,
    actor_api: ActorAPI,
    comm_hub: V1CommHub | None = None,
    timeout: float | None = None,
    run_coroutine: Callable[[Coroutine[Any, Any, Any]], Any] | None = None,
) -> Callable[[Any, dict[str, Any]], Any]:
    """
    Build a sync exception-handler invoker over v1 actor call plane.

    Local handler target:
    - resolved by ActorAPI and executed locally.

    Remote handler target:
    - encoded as actor call intent and sent via V1CommHub rpc plane.
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
            "actor_exception_handler_invoker_requires_run_coroutine_when_called_inside_running_event_loop",
        )

    async def _invoke_async(handler_target: Any, event: dict[str, Any]) -> Any:
        resolved_target = _resolve_handler_target(
            target=handler_target,
            event=event,
            group_replica_index_by_pool=group_replica_index_by_pool,
            rr_cursor_by_pool=rr_cursor_by_pool,
        )
        prepared = await actor_api.call_or_prepare_call(resolved_target, event)
        mode = _normalize_non_empty(prepared.get("mode"), field_name="mode")
        if mode == "local_result":
            return prepared.get("result")
        if mode != "actor_call_intent":
            raise RuntimeError(f"unsupported_actor_call_prepare_mode:{mode}")

        if comm_hub is None:
            raise RuntimeError("remote_exception_handler_requires_comm_hub")

        target_address = _normalize_non_empty(
            prepared.get("address"),
            field_name="address",
        )
        reply = await comm_hub.request(
            plane=PLANE_RPC,
            op=OP_RPC_ACTOR_CALL,
            target_address=target_address,
            timeout=timeout,
            request_ref_id=_resolve_request_ref_id(event),
            body=prepared,
        )
        body = reply.body
        if not isinstance(body, dict):
            raise TypeError("exception_handler_actor_call_reply_body must be a dict.")
        reply_mode = _normalize_non_empty(body.get("mode"), field_name="mode")
        if reply_mode == "applied_actor_call":
            return body.get("result")
        if reply_mode == "applied_actor_call_error":
            error_type = _normalize_non_empty(body.get("error_type"), field_name="error_type")
            message = _normalize_non_empty(body.get("message"), field_name="message")
            raise RuntimeError(f"exception_handler_actor_call_failed:{error_type}:{message}")
        raise RuntimeError(f"unsupported_actor_call_reply_mode:{reply_mode}")

    def _invoke(handler_target: Any, event: dict[str, Any]) -> Any:
        if not isinstance(event, dict):
            raise TypeError("exception event must be a dict.")
        coro = _invoke_async(handler_target, event)
        try:
            return _runner(coro)
        except Exception:
            try:
                coro.close()
            except Exception:
                pass
            raise

    return _invoke


def _resolve_request_ref_id(event: dict[str, Any]) -> str | None:
    raw = event.get("event_group_id")
    if raw is None:
        return None
    normalized = str(raw).strip()
    if not normalized:
        return None
    return normalized


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


def _resolve_handler_target(
    *,
    target: Any,
    event: dict[str, Any],
    group_replica_index_by_pool: dict[str, dict[str, int]],
    rr_cursor_by_pool: dict[str, int],
) -> Any:
    if not isinstance(target, dict):
        return target
    kind = str(target.get("kind") or "").strip()
    if kind != "actor_replica_pool_ref":
        return target

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

    keyby_key = _resolve_keyby_route_key(event=event, event_meta=event_meta)
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

    event_group_id = _normalize_optional_non_empty(
        event.get("event_group_id")
    ) or _normalize_optional_non_empty(event_meta.get("event_group_id"))
    if event_group_id is None:
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
    replica_index = sticky_mapping.get(event_group_id)
    if replica_index is None:
        rr_index = int(rr_cursor_by_pool.get(pool_key, 0))
        replica_index = rr_index % len(normalized_replicas)
        sticky_mapping[event_group_id] = replica_index
        rr_cursor_by_pool[pool_key] = rr_index + 1
    selected = normalized_replicas[int(replica_index)]
    return {
        "address": selected["address"],
        "actor_id": selected["actor_id"],
        "method": method,
    }


def _resolve_keyby_route_key(*, event: dict[str, Any], event_meta: dict[str, Any]) -> str | None:
    tags = event_meta.get("tags")
    if isinstance(tags, dict):
        for key_name in ("state_partition_key", "keyby_key"):
            candidate = _normalize_optional_non_empty(tags.get(key_name))
            if candidate is not None:
                return candidate
    metadata = event.get("meta")
    if isinstance(metadata, dict):
        for key_name in ("state_partition_key", "keyby_key"):
            candidate = _normalize_optional_non_empty(metadata.get(key_name))
            if candidate is not None:
                return candidate
    return None


__all__ = ["build_actor_exception_handler_invoker"]
