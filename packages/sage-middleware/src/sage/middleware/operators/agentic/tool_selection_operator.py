"""
Tool Selection Operator

Middleware operator for tool selection using runtime components.

Supports engine_type switching:
- sagellm (default): SageLLMGenerator with configurable backend
  - backend_type="auto": Automatically select best available backend
  - backend_type="mock": Mock backend for testing without GPU
  - backend_type="cuda": NVIDIA CUDA backend
  - backend_type="ascend": Huawei Ascend NPU backend
- openai: OpenAIGenerator for OpenAI-compatible APIs
- hf: HFGenerator for HuggingFace models
"""

from typing import Any, Optional

from sage_libs.sage_agentic.agents.runtime import BenchmarkAdapter, Orchestrator, RuntimeConfig
from sage_libs.sage_agentic.agents.runtime.config import SelectorConfig

from sage.common.core.functions import MapFunction

from .runtime import _build_generator


class ToolSelectionOperator(MapFunction):
    """
    Operator for tool selection.

    Wraps runtime tool selector in a middleware operator interface.

    Args:
        selector: Tool selector instance (optional)
        config: Configuration dictionary with optional keys:
            - selector: Selector-specific config (e.g., top_k)
            - generator: Generator config with engine_type/backend_type
            - engine_type: Shorthand for generator.engine_type (sagellm/openai/hf)
            - backend_type: Shorthand for generator.backend_type (auto/mock/cuda/ascend)

    Example:
        ```python
        # Using sagellm with mock backend (for testing)
        operator = ToolSelectionOperator(config={
            "generator": {
                "engine_type": "sagellm",
                "backend_type": "mock",
            },
            "selector": {"top_k": 5},
        })

        # Using default sagellm with auto backend
        operator = ToolSelectionOperator(config={
            "engine_type": "sagellm",
            "backend_type": "auto",
        })
        ```
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

        self.config = config

        # Build generator if config provided
        generator_conf = config.get("generator", {})
        # Allow shorthand engine_type/backend_type at top level
        if "engine_type" in config and "engine_type" not in generator_conf:
            generator_conf["engine_type"] = config["engine_type"]
        if "backend_type" in config and "backend_type" not in generator_conf:
            generator_conf["backend_type"] = config["backend_type"]

        # Build generator (defaults to sagellm with auto backend)
        if generator_conf or not selector:
            engine_type = generator_conf.get("engine_type", "sagellm")
            # Ensure we have at least minimal config
            if not generator_conf:
                generator_conf = {"engine_type": "sagellm", "backend_type": "auto"}
            self.generator = _build_generator(generator_conf, engine_type=engine_type)
        else:
            self.generator = None

        selector_config = SelectorConfig(**config.get("selector", {}))
        runtime_config = RuntimeConfig(selector=selector_config)

        # Create orchestrator
        self.orchestrator = Orchestrator(config=runtime_config, selector=selector)

        # Create adapter for easy use
        self.adapter = BenchmarkAdapter(self.orchestrator)

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
