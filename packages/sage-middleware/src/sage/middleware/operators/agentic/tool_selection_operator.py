"""
Tool Selection Operator

Middleware operator for tool selection using runtime components.
"""

from typing import Any, Optional

from sage.common.core.functions import MapFunction
from sage.libs.agentic.agents.runtime import BenchmarkAdapter, Orchestrator, RuntimeConfig
from sage.libs.agentic.agents.runtime.config import SelectorConfig


class ToolSelectionOperator(MapFunction):
    """
    Operator for tool selection.

    Wraps runtime tool selector in a middleware operator interface.
    """

    def __init__(
        self,
        selector: Optional[Any] = None,
        config: Optional[dict[str, Any]] = None,
    ):
        """Initialize tool selection operator.

        Args:
            selector: Tool selector instance (optional)
            config: Configuration dictionary
        """
        super().__init__()

        # Parse configuration
        if config is None:
            config = {}

        selector_config = SelectorConfig(**config.get("selector", {}))
        runtime_config = RuntimeConfig(selector=selector_config)

        # Create orchestrator
        self.orchestrator = Orchestrator(config=runtime_config, selector=selector)

        # Create adapter for easy use
        self.adapter = BenchmarkAdapter(self.orchestrator)

        self.config = config

    def __call__(self, query: Any) -> list[Any]:
        """Execute tool selection.

        Args:
            query: Tool selection query

        Returns:
            List of selected tools
        """
        top_k = self.config.get("selector", {}).get("top_k", 5)
        return self.adapter.run_tool_selection(query, top_k=top_k)

    def execute(self, data: Any) -> list[Any]:
        """Execute map function interface."""
        return self.__call__(data)

    def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dictionary of metrics
        """
        return self.adapter.get_metrics()
