from __future__ import annotations

from typing import Any

from sage.runtime.flownet.runtime.actors.actor_api import ActorAPI
from sage.runtime.flownet.runtime.comm import OP_RPC_ACTOR_CALL, PLANE_RPC, V1CommHub


def register_actor_call_rpc_handler(*, actor_api: ActorAPI, comm_hub: V1CommHub) -> None:
    """Register owner-side rpc handler that applies incoming actor call intents."""

    async def _handle_actor_call(envelope) -> dict[str, Any]:
        intent = _coerce_actor_call_intent(envelope.body)
        return await actor_api.apply_call_intent(intent)

    comm_hub.protocol_router.register_handler(
        plane=PLANE_RPC,
        op=OP_RPC_ACTOR_CALL,
        handler=_handle_actor_call,
    )


async def call_actor_via_comm(
    actor_api: ActorAPI,
    comm_hub: V1CommHub,
    target: Any,
    *call_args: Any,
    timeout: float | None = None,
    request_ref_id: str | None = None,
    **call_kwargs: Any,
) -> dict[str, Any]:
    """
    Caller-side actor invocation path.

    Local target returns local_result immediately; remote target is sent through
    V1CommHub as rpc/actor.call and returns owner apply result.
    """

    prepared = await actor_api.call_or_prepare_call(target, *call_args, **call_kwargs)
    mode = str(prepared.get("mode") or "").strip()
    if mode == "local_result":
        return prepared
    if mode != "actor_call_intent":
        raise RuntimeError(f"unsupported_actor_call_prepare_mode:{mode}")

    reply = await comm_hub.request(
        plane=PLANE_RPC,
        op=OP_RPC_ACTOR_CALL,
        target_address=_normalize_non_empty(prepared.get("address"), field_name="address"),
        timeout=timeout,
        request_ref_id=request_ref_id,
        body=prepared,
    )
    return _coerce_actor_call_reply(reply.body)


def _coerce_actor_call_intent(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise TypeError("actor_call_intent body must be a dict.")
    intent = dict(body)
    mode = _normalize_non_empty(intent.get("mode"), field_name="mode")
    if mode != "actor_call_intent":
        raise ValueError(f"unsupported_actor_call_intent_mode:{mode}")
    return intent


def _coerce_actor_call_reply(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise TypeError("actor_call_reply body must be a dict.")
    reply = dict(body)
    mode = _normalize_non_empty(reply.get("mode"), field_name="mode")
    if mode not in {"applied_actor_call", "applied_actor_call_error"}:
        raise ValueError(f"unsupported_actor_call_reply_mode:{mode}")
    return reply


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = [
    "register_actor_call_rpc_handler",
    "call_actor_via_comm",
]
