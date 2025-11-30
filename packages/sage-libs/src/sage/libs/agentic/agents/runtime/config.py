"""
Runtime Configuration Models

Defines Pydantic models for configuring agent runtime components.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SelectorConfig(BaseModel):
    """Configuration for tool selector."""

    name: str = Field(default="keyword", description="Selector strategy name")
    top_k: int = Field(default=5, description="Number of tools to select")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")
    cache_enabled: bool = Field(default=True, description="Enable result caching")


class PlannerConfig(BaseModel):
    """Configuration for task planner."""

    name: str = Field(default="llm", description="Planner strategy name")
    min_steps: int = Field(default=1, description="Minimum plan steps")
    max_steps: int = Field(default=10, description="Maximum plan steps")
    params: dict[str, Any] = Field(default_factory=dict, description="Planner-specific parameters")
    enable_repair: bool = Field(default=True, description="Enable plan repair on errors")


class TimingConfig(BaseModel):
    """Configuration for timing decider."""

    name: str = Field(default="rule_based", description="Timing strategy name")
    threshold: float = Field(default=0.5, description="Decision threshold")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")
    use_context: bool = Field(default=True, description="Use conversation context")


class TelemetryConfig(BaseModel):
    """Configuration for telemetry collection."""

    enabled: bool = Field(default=True, description="Enable telemetry")
    collect_latency: bool = Field(default=True, description="Collect latency metrics")
    collect_accuracy: bool = Field(default=True, description="Collect accuracy metrics")
    output_path: Optional[str] = Field(default=None, description="Path to save telemetry data")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")


class RuntimeConfig(BaseModel):
    """Main configuration for agent runtime."""

    selector: SelectorConfig = Field(default_factory=SelectorConfig)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)

    max_turns: int = Field(default=8, description="Maximum conversation turns")
    timeout: float = Field(default=30.0, description="Timeout in seconds")

    class Config:
        """Pydantic config."""

        extra = "allow"
