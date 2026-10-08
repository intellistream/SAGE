from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import FlowProgramRef

from .errors import LoopOperatorContractError, ProcessTargetResolutionError

_LOOP_MISSING = object()


def _resolve_process_program_ref(transformation: Any) -> FlowProgramRef:
    target = getattr(transformation, "target", None)
    ref = _coerce_flow_program_ref(target)
    if ref is not None:
        return ref

    pipe_flow = getattr(transformation, "pipe_flow", None)
    ref = _coerce_flow_program_ref(pipe_flow)
    if ref is not None:
        return ref

    raise ProcessTargetResolutionError(
        "process operator target must provide canonical program_uri/program_rev metadata.",
    )


def resolve_loop_body_program_ref(transformation: Any) -> FlowProgramRef | None:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise LoopOperatorContractError("loop operator_config must be a mapping.")
    loop_meta = operator_config.get("loop")
    if not isinstance(loop_meta, Mapping):
        raise LoopOperatorContractError("loop operator_config.loop must be a mapping.")
    body = loop_meta.get("body", _LOOP_MISSING)
    if body is _LOOP_MISSING:
        raise LoopOperatorContractError("loop.body is required.")
    return _coerce_flow_program_ref(body)


def _coerce_flow_program_ref(raw: Any) -> FlowProgramRef | None:
    if raw is None:
        return None

    program_uri = None
    program_rev = None
    if isinstance(raw, Mapping):
        program_uri = raw.get("program_uri")
        program_rev = raw.get("program_rev")
    else:
        program_uri = getattr(raw, "program_uri", None)
        program_rev = getattr(raw, "program_rev", None)

    if (
        isinstance(program_uri, str)
        and program_uri.strip()
        and isinstance(program_rev, str)
        and program_rev.strip()
    ):
        return FlowProgramRef(program_uri=program_uri.strip(), program_rev=program_rev.strip())

    return None


__all__ = [
    "resolve_loop_body_program_ref",
    "_resolve_process_program_ref",
    "_coerce_flow_program_ref",
]
