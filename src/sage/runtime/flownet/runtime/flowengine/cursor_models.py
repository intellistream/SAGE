from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FLOW_STACK_FRAME_KIND_PROCESS_RETURN = "process_return"
FLOW_STACK_FRAME_KIND_LOOP_SCOPE = "loop_scope"
FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION = "flatmap_continuation"


@dataclass(frozen=True)
class FlowProgramRef:
    program_uri: str
    program_rev: str


@dataclass(frozen=True)
class TopicRef:
    topic_uri: str
    coordinator_address: str


@dataclass(frozen=True)
class FlowStackFrame:
    resume_flow_program_ref: FlowProgramRef
    resume_pc_node_ids: tuple[str, ...]
    caller_event_chain_id: str
    callsite_pc_node_id: str
    frame_meta: dict[str, Any]
    frame_kind: str = FLOW_STACK_FRAME_KIND_PROCESS_RETURN


@dataclass(frozen=True)
class EventCursor:
    event_group_id: str
    event_chain_id: str
    flow_program_ref: FlowProgramRef
    pc_node_id: str
    flow_stack: tuple[FlowStackFrame, ...]
    payload: Any
    tags: dict[str, str]
    seq: int | None
    origin_topic_ref: TopicRef
    convergence_topic_ref: TopicRef
    convergence_topic_epoch: int
    meta: dict[str, Any]


__all__ = [
    "FLOW_STACK_FRAME_KIND_PROCESS_RETURN",
    "FLOW_STACK_FRAME_KIND_LOOP_SCOPE",
    "FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION",
    "FlowProgramRef",
    "TopicRef",
    "FlowStackFrame",
    "EventCursor",
]
