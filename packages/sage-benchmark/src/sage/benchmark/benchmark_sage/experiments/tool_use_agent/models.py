"""
Data Models for Tool Use Agent Pipeline
========================================

Defines the core data structures used throughout the pipeline:
- ToolCallRequest: Request to call a specific tool
- ToolCallResult: Result from tool execution
- ReActStep: A single ReAct reasoning step (Thought-Action-Observation)
- AgentState: Complete state flowing through the pipeline
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReActPhase(Enum):
    """ReAct reasoning phases"""

    THOUGHT = "thought"  # Reasoning about the current state
    ACTION = "action"  # Deciding which tool to use
    OBSERVATION = "observation"  # Result from tool execution
    REFLECTION = "reflection"  # Self-critique and adjustment


@dataclass
class ToolCallRequest:
    """Tool call request with arguments"""

    tool_name: str
    arguments: dict[str, Any]
    reason: str = ""  # Why this tool was selected (from ReAct reasoning)


@dataclass
class ToolCallResult:
    """Tool call result with success/error status"""

    tool_name: str
    success: bool
    result: Any
    error: str | None = None
    execution_time: float = 0.0


@dataclass
class ReActStep:
    """A single step in ReAct reasoning loop"""

    phase: ReActPhase
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "phase": self.phase.value,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentState:
    """
    Complete agent state flowing through the pipeline.

    This state accumulates information as it passes through each operator:
    1. UserQuerySource: Sets query, session_id, timestamp
    2. ToolSelector: Adds selected_tools, react_trace, memory_context, compressed_context
    3. ToolExecutor: Adds tool_results
    4. ResponseGenerator: Adds response, updates react_trace with reflection
    """

    # Core fields
    query: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Tool selection and execution
    selected_tools: list[ToolCallRequest] = field(default_factory=list)
    tool_results: list[ToolCallResult] = field(default_factory=list)

    # ReAct reasoning trace
    react_trace: list[ReActStep] = field(default_factory=list)
    max_react_iterations: int = 3
    current_iteration: int = 0

    # Memory and context (from services)
    memory_context: list[dict[str, Any]] = field(default_factory=list)
    compressed_context: str = ""
    retrieved_documents: list[dict[str, Any]] = field(default_factory=list)

    # Output
    response: str = ""

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def add_thought(self, content: str) -> None:
        """Add a thought step to ReAct trace"""
        self.react_trace.append(
            ReActStep(
                phase=ReActPhase.THOUGHT,
                content=content,
            )
        )

    def add_action(self, content: str) -> None:
        """Add an action step to ReAct trace"""
        self.react_trace.append(
            ReActStep(
                phase=ReActPhase.ACTION,
                content=content,
            )
        )

    def add_observation(self, content: str) -> None:
        """Add an observation step to ReAct trace"""
        self.react_trace.append(
            ReActStep(
                phase=ReActPhase.OBSERVATION,
                content=content,
            )
        )

    def add_reflection(self, content: str) -> None:
        """Add a reflection step to ReAct trace"""
        self.react_trace.append(
            ReActStep(
                phase=ReActPhase.REFLECTION,
                content=content,
            )
        )

    def get_react_trace_str(self) -> str:
        """Get formatted ReAct trace as string"""
        lines = []
        for step in self.react_trace:
            prefix = {
                ReActPhase.THOUGHT: "Thought",
                ReActPhase.ACTION: "Action",
                ReActPhase.OBSERVATION: "Observation",
                ReActPhase.REFLECTION: "Reflection",
            }.get(step.phase, "Step")
            lines.append(f"[{prefix}] {step.content}")
        return "\n".join(lines)

    def to_memory_entry(self) -> dict[str, Any]:
        """Convert to format suitable for memory storage"""
        return {
            "session_id": self.session_id,
            "query": self.query,
            "response": self.response,
            "tools_used": [t.tool_name for t in self.selected_tools],
            "timestamp": self.timestamp,
            "react_trace": [s.to_dict() for s in self.react_trace],
        }
