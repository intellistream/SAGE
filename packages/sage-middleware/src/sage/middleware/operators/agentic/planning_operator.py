"""
Planning Operator

Middleware operator for planning using runtime components.
"""

from typing import Any, Optional

from sage.common.core.functions import MapFunction
from sage.libs.agentic.agents.runtime import BenchmarkAdapter, Orchestrator, RuntimeConfig
from sage.libs.agentic.agents.runtime.config import PlannerConfig


class PlanningOperator(MapFunction):
    """
    Operator for planning.

    Wraps runtime planner in a middleware operator interface.
    """

    def __init__(
        self,
        planner: Optional[Any] = None,
        config: Optional[dict[str, Any]] = None,
    ):
        """Initialize planning operator.

        Args:
            planner: Planner instance (optional)
            config: Configuration dictionary
        """
        super().__init__()

        # Parse configuration
        if config is None:
            config = {}

        planner_config = PlannerConfig(**config.get("planner", {}))
        runtime_config = RuntimeConfig(planner=planner_config)

        # Create orchestrator
        self.orchestrator = Orchestrator(config=runtime_config, planner=planner)

        # Create adapter for easy use
        self.adapter = BenchmarkAdapter(self.orchestrator)

        self.config = config

    def __call__(self, request: Any) -> Any:
        """Execute planning.

        Args:
            request: Planning request

        Returns:
            Generated plan
        """
        return self.adapter.run_planning(request)

    def execute(self, data: Any) -> Any:
        """Execute map function interface."""
        return self.__call__(data)

    def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dictionary of metrics
        """
        return self.adapter.get_metrics()
