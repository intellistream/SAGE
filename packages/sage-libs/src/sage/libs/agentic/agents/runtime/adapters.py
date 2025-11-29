"""
Benchmark Adapter Module

Provides interface between agent runtime and benchmark evaluation systems.
Allows benchmark runners to interact with runtime components in a standardized way.
"""

from typing import Any, Optional

from sage.libs.agentic.agents.runtime.orchestrator import Orchestrator


class BenchmarkAdapter:
    """
    Adapter for connecting runtime to benchmark evaluation.

    Provides simple, stateless interfaces for benchmark runners to
    evaluate tool selection, planning, and timing decisions.
    """

    def __init__(self, orchestrator: Orchestrator):
        """Initialize benchmark adapter.

        Args:
            orchestrator: Orchestrator instance to use
        """
        self.orchestrator = orchestrator

    def run_tool_selection(self, query: Any, top_k: Optional[int] = None) -> list[Any]:
        """Execute tool selection for benchmark evaluation.

        Args:
            query: Tool selection query (from benchmark)
            top_k: Number of tools to select

        Returns:
            List of selected tool predictions

        Example:
            ```python
            from sage.benchmark.benchmark_agent.experiments import ToolSelectionQuery

            query = ToolSelectionQuery(
                sample_id="ts_001",
                instruction="Find weather in Beijing",
                candidate_tools=["weather_001", "weather_002", ...],
                context={}
            )

            predictions = adapter.run_tool_selection(query, top_k=5)
            ```
        """
        return self.orchestrator.execute_tool_selection(query, top_k=top_k)

    def run_planning(self, request: Any) -> Any:
        """Execute planning for benchmark evaluation.

        Args:
            request: Planning request (from benchmark)

        Returns:
            Generated plan result

        Example:
            ```python
            from sage.benchmark.benchmark_agent.experiments import PlanRequest

            request = PlanRequest(
                goal="Deploy application to production",
                context={},
                tools=[...],
                constraints=[]
            )

            plan = adapter.run_planning(request)
            ```
        """
        return self.orchestrator.execute_planning(request)

    def run_timing(self, message: Any) -> Any:
        """Execute timing decision for benchmark evaluation.

        Args:
            message: Message to evaluate (from benchmark)

        Returns:
            Timing decision

        Example:
            ```python
            from sage.benchmark.benchmark_agent.experiments import TimingMessage

            message = TimingMessage(
                content="What's the weather?",
                context={},
                history=[]
            )

            decision = adapter.run_timing(message)
            ```
        """
        return self.orchestrator.execute_timing_decision(message)

    def get_metrics(self) -> dict:
        """Get telemetry metrics from runtime.

        Returns:
            Dictionary of performance metrics
        """
        return self.orchestrator.get_telemetry_metrics()

    def reset(self) -> None:
        """Reset adapter state (clear telemetry)."""
        self.orchestrator.reset_telemetry()
