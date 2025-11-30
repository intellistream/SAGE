"""
Orchestrator Module

Provides unified scheduler for coordinating tool calls, planning execution,
and workflow management.
"""

from typing import Any, Optional, Protocol

from sage.libs.agentic.agents.runtime.config import RuntimeConfig
from sage.libs.agentic.agents.runtime.telemetry import TelemetryCollector


class ToolSelector(Protocol):
    """Protocol for tool selection strategies."""

    def select(self, query: Any, top_k: int = 5) -> list[Any]:
        """Select top-k tools for the given query."""
        ...


class Planner(Protocol):
    """Protocol for planning strategies."""

    def plan(self, request: Any) -> Any:
        """Generate a plan for the given request."""
        ...


class TimingDecider(Protocol):
    """Protocol for timing decision strategies."""

    def decide(self, message: Any) -> Any:
        """Decide whether to call a tool."""
        ...


class Orchestrator:
    """
    Unified orchestrator for agent execution.

    Coordinates tool selection, planning, and timing decisions while
    collecting telemetry data.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        selector: Optional[ToolSelector] = None,
        planner: Optional[Planner] = None,
        timing_decider: Optional[TimingDecider] = None,
        telemetry: Optional[TelemetryCollector] = None,
    ):
        """Initialize orchestrator.

        Args:
            config: Runtime configuration
            selector: Tool selector instance
            planner: Planner instance
            timing_decider: Timing decider instance
            telemetry: Telemetry collector instance
        """
        self.config = config
        self.selector = selector
        self.planner = planner
        self.timing_decider = timing_decider
        self.telemetry = telemetry or TelemetryCollector(config.telemetry)

    def execute_tool_selection(self, query: Any, top_k: Optional[int] = None) -> list[Any]:
        """Execute tool selection with telemetry.

        Args:
            query: Tool selection query
            top_k: Number of tools to select (overrides config)

        Returns:
            List of selected tools
        """
        if self.selector is None:
            raise RuntimeError("Tool selector not configured")

        record = self.telemetry.start("tool_selection", metadata={"top_k": top_k})

        try:
            k = top_k if top_k is not None else self.config.selector.top_k
            result = self.selector.select(query, top_k=k)
            self.telemetry.finish(record, success=True)
            return result
        except Exception as e:
            self.telemetry.finish(record, success=False, error=str(e))
            raise

    def execute_planning(self, request: Any) -> Any:
        """Execute planning with telemetry.

        Args:
            request: Planning request

        Returns:
            Generated plan
        """
        if self.planner is None:
            raise RuntimeError("Planner not configured")

        record = self.telemetry.start("planning")

        try:
            result = self.planner.plan(request)
            self.telemetry.finish(record, success=True)
            return result
        except Exception as e:
            self.telemetry.finish(record, success=False, error=str(e))
            raise

    def execute_timing_decision(self, message: Any) -> Any:
        """Execute timing decision with telemetry.

        Args:
            message: Message to evaluate

        Returns:
            Timing decision
        """
        if self.timing_decider is None:
            raise RuntimeError("Timing decider not configured")

        record = self.telemetry.start("timing_decision")

        try:
            result = self.timing_decider.decide(message)
            self.telemetry.finish(record, success=True)
            return result
        except Exception as e:
            self.telemetry.finish(record, success=False, error=str(e))
            raise

    def get_telemetry_metrics(self) -> dict[str, Any]:
        """Get current telemetry metrics.

        Returns:
            Dictionary of metrics
        """
        return self.telemetry.get_metrics()

    def reset_telemetry(self) -> None:
        """Reset telemetry data."""
        self.telemetry.clear()
