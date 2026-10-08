from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from sage.runtime.flownet.runtime.comm import (
    OP_RPC_FLOW_PROGRAM_PULL,
    PLANE_RPC,
    V1CommHub,
)
from sage.runtime.flownet.runtime.flowengine.cursor_models import FlowProgramRef


def register_flow_program_pull_handler(
    *,
    comm_hub: V1CommHub,
    resolve_flow_program: Callable[[FlowProgramRef], Any | None],
) -> None:
    """Register owner-side rpc handler for flow-program pull requests."""

    def _handle_pull(envelope) -> dict[str, Any]:
        requested_ref = _decode_flow_program_ref_from_body(envelope.body)
        flow_program = resolve_flow_program(requested_ref)
        return {
            "mode": "flow_program_pull_result",
            "flow_program_ref": _encode_flow_program_ref(requested_ref),
            "found": flow_program is not None,
            "flow_program": flow_program,
        }

    comm_hub.protocol_router.register_handler(
        plane=PLANE_RPC,
        op=OP_RPC_FLOW_PROGRAM_PULL,
        handler=_handle_pull,
    )


def build_flow_program_pull_resolver(
    *,
    comm_hub: V1CommHub,
    resolve_owner_address: Callable[[FlowProgramRef], str],
    timeout: float | None = None,
    run_coroutine: Callable[[Coroutine[Any, Any, Any]], Any] | None = None,
) -> Callable[[FlowProgramRef], Any | None]:
    """Build sync FlowProgramCache pull callback from owner route + comm pull."""

    def _runner(coro: Coroutine[Any, Any, Any]) -> Any:
        if callable(run_coroutine):
            return run_coroutine(coro)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "flow_program_pull_resolver_requires_run_coroutine_when_called_inside_running_event_loop",
        )

    async def _pull_async(flow_program_ref: FlowProgramRef) -> Any | None:
        owner_address = _normalize_non_empty(
            resolve_owner_address(flow_program_ref),
            field_name="owner_address",
        )
        return await pull_flow_program_via_comm(
            comm_hub=comm_hub,
            target_address=owner_address,
            flow_program_ref=flow_program_ref,
            timeout=timeout,
        )

    def _pull(flow_program_ref: FlowProgramRef) -> Any | None:
        normalized_ref = _normalize_program_ref(flow_program_ref)
        coro = _pull_async(normalized_ref)
        try:
            return _runner(coro)
        except Exception:
            try:
                coro.close()
            except Exception:
                pass
            raise

    return _pull


async def pull_flow_program_via_comm(
    *,
    comm_hub: V1CommHub,
    target_address: str,
    flow_program_ref: FlowProgramRef,
    timeout: float | None = None,
) -> Any | None:
    """Pull flow program from remote owner over rpc flow_program.pull."""

    normalized_target = _normalize_non_empty(target_address, field_name="target_address")
    normalized_ref = _normalize_program_ref(flow_program_ref)
    reply = await comm_hub.request(
        plane=PLANE_RPC,
        op=OP_RPC_FLOW_PROGRAM_PULL,
        target_address=normalized_target,
        timeout=timeout,
        request_ref_id=_normalize_request_ref(normalized_ref),
        body={
            "mode": "flow_program_pull",
            "flow_program_ref": _encode_flow_program_ref(normalized_ref),
        },
    )
    if not isinstance(reply.body, dict):
        raise TypeError("flow_program_pull_reply_body must be a dict.")
    body = dict(reply.body)

    if "error_type" in body and "message" in body and "mode" not in body:
        error_type = _normalize_non_empty(body.get("error_type"), field_name="error_type")
        message = _normalize_non_empty(body.get("message"), field_name="message")
        raise RuntimeError(f"flow_program_pull_failed:{error_type}:{message}")

    mode = _normalize_non_empty(body.get("mode"), field_name="mode")
    if mode != "flow_program_pull_result":
        raise ValueError(f"unsupported_flow_program_pull_reply_mode:{mode}")
    returned_ref = _decode_flow_program_ref_mapping(body.get("flow_program_ref"))
    if returned_ref != normalized_ref:
        raise ValueError(
            "flow_program_pull_ref_mismatch:"
            f" expected={_normalize_request_ref(normalized_ref)},"
            f" actual={_normalize_request_ref(returned_ref)}",
        )
    found = bool(body.get("found"))
    if not found:
        return None
    if "flow_program" not in body:
        raise ValueError("flow_program_pull_result_missing_flow_program")
    return body.get("flow_program")


def _decode_flow_program_ref_from_body(body: Any) -> FlowProgramRef:
    if not isinstance(body, dict):
        raise TypeError("flow_program_pull_body must be a dict.")
    mode = _normalize_non_empty(body.get("mode"), field_name="mode")
    if mode != "flow_program_pull":
        raise ValueError(f"unsupported_flow_program_pull_mode:{mode}")
    return _decode_flow_program_ref_mapping(body.get("flow_program_ref"))


def _decode_flow_program_ref_mapping(raw: Any) -> FlowProgramRef:
    if not isinstance(raw, dict):
        raise TypeError("flow_program_ref must be a dict.")
    return FlowProgramRef(
        program_uri=_normalize_non_empty(
            raw.get("program_uri"),
            field_name="flow_program_ref.program_uri",
        ),
        program_rev=_normalize_non_empty(
            raw.get("program_rev"),
            field_name="flow_program_ref.program_rev",
        ),
    )


def _encode_flow_program_ref(flow_program_ref: FlowProgramRef) -> dict[str, str]:
    normalized_ref = _normalize_program_ref(flow_program_ref)
    return {
        "program_uri": normalized_ref.program_uri,
        "program_rev": normalized_ref.program_rev,
    }


def _normalize_program_ref(flow_program_ref: FlowProgramRef) -> FlowProgramRef:
    if not isinstance(flow_program_ref, FlowProgramRef):
        raise TypeError("flow_program_ref must be FlowProgramRef.")
    return FlowProgramRef(
        program_uri=_normalize_non_empty(
            flow_program_ref.program_uri,
            field_name="flow_program_ref.program_uri",
        ),
        program_rev=_normalize_non_empty(
            flow_program_ref.program_rev,
            field_name="flow_program_ref.program_rev",
        ),
    )


def _normalize_request_ref(flow_program_ref: FlowProgramRef) -> str:
    normalized_ref = _normalize_program_ref(flow_program_ref)
    return f"{normalized_ref.program_uri}#{normalized_ref.program_rev}"


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = [
    "register_flow_program_pull_handler",
    "build_flow_program_pull_resolver",
    "pull_flow_program_via_comm",
]
