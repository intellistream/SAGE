"""
Timing Operator

Middleware operator for timing decisions using runtime components.
"""

from typing import Any, Optional

from sage.common.core.functions import MapFunction
from sage.libs.agentic.agents.runtime import BenchmarkAdapter, Orchestrator, RuntimeConfig
from sage.libs.agentic.agents.runtime.config import TimingConfig


class TimingOperator(MapFunction):
    """
    Operator for timing decisions.

    Wraps runtime timing decider in a middleware operator interface.
    """

    def __init__(
        self,
        timing_decider: Optional[Any] = None,
        config: Optional[dict[str, Any]] = None,
    ):
        """Initialize timing operator.

        Args:
            timing_decider: Timing decider instance (optional)
            config: Configuration dictionary
        """
        super().__init__()

        # Parse configuration
        if config is None:
            config = {}

        timing_config = TimingConfig(**config.get("timing", {}))
        runtime_config = RuntimeConfig(timing=timing_config)

        # Create orchestrator
        self.orchestrator = Orchestrator(config=runtime_config, timing_decider=timing_decider)

        # Create adapter for easy use
        self.adapter = BenchmarkAdapter(self.orchestrator)

        self.config = config

    def __call__(self, message: Any) -> Any:
        """Execute timing decision.

        Args:
            message: Message to evaluate

        Returns:
            Timing decision
        """
        return self.adapter.run_timing(message)

    def execute(self, data: Any) -> Any:
        """Execute map function interface."""
        return self.__call__(data)

    def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dictionary of metrics
        """
        return self.adapter.get_metrics()
