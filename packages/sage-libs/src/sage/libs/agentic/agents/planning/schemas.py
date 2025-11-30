"""
Schemas and Data Structures for Planning Module

Defines core data structures for hierarchical planning and timing judgment.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    """Metadata about an available tool."""

    tool_id: str
    name: str
    description: str
    category: str
    capabilities: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class PlanStep(BaseModel):
    """Single step in a task plan."""

    id: int
    action: str
    tool_id: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    description: Optional[str] = None

    class Config:
        extra = "allow"


class PlanRequest(BaseModel):
    """Request for generating a task plan."""

    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    tools: list[ToolMetadata] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=10, ge=1, le=20)
    min_steps: int = Field(default=5, ge=1)

    class Config:
        extra = "allow"


class PlanResult(BaseModel):
    """Result of plan generation."""

    steps: list[PlanStep]
    success: bool = True
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def num_steps(self) -> int:
        """Get number of steps in plan."""
        return len(self.steps)

    @property
    def tool_sequence(self) -> list[str]:
        """Get sequence of tool IDs."""
        return [step.tool_id for step in self.steps if step.tool_id]

    class Config:
        extra = "allow"


class TimingMessage(BaseModel):
    """Message context for timing judgment."""

    user_message: str
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    last_tool_call: Optional[dict[str, Any]] = None
    context: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class TimingDecision(BaseModel):
    """Decision about whether to call a tool."""

    should_call_tool: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    suggested_tool: Optional[str] = None

    class Config:
        extra = "allow"


class PlannerConfig(BaseModel):
    """Configuration for hierarchical planner."""

    min_steps: int = Field(default=5, ge=1)
    max_steps: int = Field(default=10, ge=1, le=20)
    enable_repair: bool = True
    enable_dependency_check: bool = True
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_retries: int = Field(default=2, ge=0, le=5)

    class Config:
        extra = "allow"


class TimingConfig(BaseModel):
    """Configuration for timing decider."""

    decision_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    use_rule_based: bool = True
    use_learning_based: bool = False
    history_window: int = Field(default=5, ge=1, le=20)

    class Config:
        extra = "allow"
