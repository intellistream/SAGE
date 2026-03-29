from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from sage.runtime.flownet.runtime.comm.loopback import InMemoryLoopbackTransport
from sage.runtime.flownet.runtime.comm.protocol import (
    OP_CONTROL_NODE_CALL,
    OP_CONTROL_NODE_RESULT,
    OP_RPC_ACTOR_CALL,
    OP_RPC_ACTOR_CALL_RESULT,
    OP_RPC_FLOW_PROGRAM_PULL,
    OP_RPC_FLOW_PROGRAM_PULL_RESULT,
    V1Envelope,
    coerce_envelope,
    make_envelope,
)
from sage.runtime.flownet.runtime.comm.reply_tracker import V1ReplyTracker
from sage.runtime.flownet.runtime.comm.router import V1ProtocolRouter
from sage.runtime.flownet.runtime.comm.transport import V1TransportBackend

_REPLY_OP_BY_REQUEST_OP: dict[str, str] = {
    OP_RPC_ACTOR_CALL: OP_RPC_ACTOR_CALL_RESULT,
    OP_RPC_FLOW_PROGRAM_PULL: OP_RPC_FLOW_PROGRAM_PULL_RESULT,
    OP_CONTROL_NODE_CALL: OP_CONTROL_NODE_RESULT,
}


class V1CommHub:
    """
    v1 communication hub.

    - sends envelopes through a transport
    - receives envelopes and dispatches via protocol router
    - tracks request/reply correlation through msg_id + meta.reply_to_msg_id
    """

    def __init__(
        self,
        *,
        local_address: str,
        transport: V1TransportBackend | None = None,
        protocol_router: V1ProtocolRouter | None = None,
        reply_tracker: V1ReplyTracker | None = None,
    ) -> None:
        self._local_address = _normalize_non_empty(local_address, field_name="local_address")
        self._transport = transport or InMemoryLoopbackTransport()
        self._router = protocol_router or V1ProtocolRouter()
        self._reply_tracker = reply_tracker or V1ReplyTracker()
        self._closed = False
        self._transport.register_endpoint(
            address=self._local_address,
            receiver=self._on_transport_envelope,
        )

    @property
    def local_address(self) -> str:
        return self._local_address

    @property
    def protocol_router(self) -> V1ProtocolRouter:
        return self._router

    def pending_request_count(self) -> int:
        return self._reply_tracker.pending_count()

    async def send(
        self,
        *,
        plane: str,
        op: str,
        target_address: str,
        request_ref_id: str | None = None,
        body: Any = None,
        meta: Mapping[str, Any] | None = None,
        msg_id: str | None = None,
    ) -> V1Envelope:
        self._ensure_open()
        envelope = make_envelope(
            plane=plane,
            op=op,
            source_address=self._local_address,
            target_address=target_address,
            expects_reply=False,
            request_ref_id=request_ref_id,
            body=body,
            meta=meta,
            msg_id=msg_id,
        )
        await self._transport.send(envelope)
        return envelope

    async def request(
        self,
        *,
        plane: str,
        op: str,
        target_address: str,
        timeout: float | None = None,
        request_ref_id: str | None = None,
        body: Any = None,
        meta: Mapping[str, Any] | None = None,
        msg_id: str | None = None,
    ) -> V1Envelope:
        self._ensure_open()
        envelope = make_envelope(
            plane=plane,
            op=op,
            source_address=self._local_address,
            target_address=target_address,
            expects_reply=True,
            request_ref_id=request_ref_id,
            body=body,
            meta=meta,
            msg_id=msg_id,
        )
        wait_future = self._reply_tracker.register(envelope.msg_id)
        try:
            await self._transport.send(envelope)
            if timeout is None:
                reply = await wait_future
            else:
                reply = await asyncio.wait_for(wait_future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._reply_tracker.cancel(envelope.msg_id)
            raise TimeoutError(f"comm_request_timeout:{envelope.msg_id}") from exc
        except Exception:
            self._reply_tracker.cancel(envelope.msg_id)
            raise
        return reply

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._reply_tracker.cancel_all()
        self._transport.unregister_endpoint(address=self._local_address)

    async def _on_transport_envelope(self, envelope_payload: V1Envelope | dict[str, Any]) -> None:
        envelope = coerce_envelope(envelope_payload)
        reply_to_msg_id = _normalize_optional_non_empty(
            (envelope.meta or {}).get("reply_to_msg_id")
        )
        if reply_to_msg_id is not None:
            self._reply_tracker.complete(reply_to_msg_id=reply_to_msg_id, value=envelope)
            return

        response_body: Any
        try:
            response_body = await self._router.dispatch(envelope)
        except Exception as exc:
            if not envelope.expects_reply:
                return
            response_body = {
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            }

        if not envelope.expects_reply:
            return

        reply_op = _REPLY_OP_BY_REQUEST_OP.get(envelope.op, envelope.op)
        reply_meta = dict(envelope.meta or {})
        reply_meta["reply_to_msg_id"] = envelope.msg_id
        reply_envelope = make_envelope(
            plane=envelope.plane,
            op=reply_op,
            source_address=self._local_address,
            target_address=envelope.source_address,
            expects_reply=False,
            request_ref_id=envelope.request_ref_id,
            body=response_body,
            meta=reply_meta,
        )
        await self._transport.send(reply_envelope)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("v1_comm_hub_closed")


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


__all__ = ["V1CommHub"]
