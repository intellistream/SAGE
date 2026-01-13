"""
Timing Operator

Middleware operator for timing decisions using runtime components.

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
from sage_libs.sage_agentic.agents.runtime.config import TimingConfig

from sage.common.core.functions import MapFunction

from .runtime import _build_generator


class TimingOperator(MapFunction):
    """
    Operator for timing decisions.

    Wraps runtime timing decider in a middleware operator interface.

    Args:
        timing_decider: Timing decider instance (optional)
        config: Configuration dictionary with optional keys:
            - timing: Timing-specific config
            - generator: Generator config with engine_type/backend_type
            - engine_type: Shorthand for generator.engine_type (sagellm/openai/hf)
            - backend_type: Shorthand for generator.backend_type (auto/mock/cuda/ascend)

    Example:
        ```python
        # Using sagellm with mock backend (for testing)
        operator = TimingOperator(config={
            "generator": {
                "engine_type": "sagellm",
                "backend_type": "mock",
            },
        })

        # Using default sagellm with auto backend
        operator = TimingOperator(config={
            "engine_type": "sagellm",
            "backend_type": "auto",
        })
        ```
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

        self.config = config

        # Build generator if config provided
        generator_conf = config.get("generator", {})
        # Allow shorthand engine_type/backend_type at top level
        if "engine_type" in config and "engine_type" not in generator_conf:
            generator_conf["engine_type"] = config["engine_type"]
        if "backend_type" in config and "backend_type" not in generator_conf:
            generator_conf["backend_type"] = config["backend_type"]

        # Build generator (defaults to sagellm with auto backend)
        if generator_conf or not timing_decider:
            engine_type = generator_conf.get("engine_type", "sagellm")
            # Ensure we have at least minimal config
            if not generator_conf:
                generator_conf = {"engine_type": "sagellm", "backend_type": "auto"}
            self.generator = _build_generator(generator_conf, engine_type=engine_type)
        else:
            self.generator = None

        timing_config = TimingConfig(**config.get("timing", {}))
        runtime_config = RuntimeConfig(timing=timing_config)

        # Create orchestrator
        self.orchestrator = Orchestrator(config=runtime_config, timing_decider=timing_decider)

        # Create adapter for easy use
        self.adapter = BenchmarkAdapter(self.orchestrator)

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
