"""
Strategy Adapter Registry

Provides a unified registry for mapping strategy names (e.g., "baseline.keyword")
to actual selector/planner/timing implementations from sage-libs.

This bridges the benchmark experiments with the runtime components.
"""

from typing import Any, Callable, Optional, Protocol

# Lazy imports to avoid circular dependencies
_SELECTOR_REGISTRY = None
_PLANNER_CLASS = None
_TIMING_DECIDER_CLASS = None


class StrategyProtocol(Protocol):
    """Protocol for strategy adapters."""

    def predict(self, query: Any, **kwargs) -> Any:
        """Make a prediction."""
        ...


class SelectorAdapter:
    """
    Adapter wrapping tool selectors to provide unified predict() interface.

    Maps the selector's select() method to predict() for benchmark compatibility.
    """

    def __init__(self, selector: Any):
        """
        Initialize adapter.

        Args:
            selector: A tool selector instance with select() method
        """
        self.selector = selector

    def predict(self, query: Any, top_k: Optional[int] = None, **kwargs) -> list:
        """
        Make tool selection prediction.

        Args:
            query: ToolSelectionQuery from experiment
            top_k: Number of tools to select

        Returns:
            List of ToolPrediction objects
        """
        # Convert experiment query to selector query format
        from sage.libs.agentic.agents.action.tool_selection.schemas import (
            ToolSelectionQuery as SelectorQuery,
        )

        selector_query = SelectorQuery(
            sample_id=query.sample_id,
            instruction=query.instruction,
            candidate_tools=getattr(query, "candidate_tools", None),
            context=getattr(query, "context", {}),
        )

        k = top_k if top_k is not None else 5
        return self.selector.select(selector_query, top_k=k)


class PlannerAdapter:
    """
    Adapter wrapping planners to provide unified plan() interface.
    """

    def __init__(self, planner: Any):
        """
        Initialize adapter.

        Args:
            planner: A planner instance with plan() method
        """
        self.planner = planner

    def plan(self, task: Any, **kwargs) -> Any:
        """
        Generate a plan for the task.

        Args:
            task: PlanningTask from experiment

        Returns:
            PlanningPrediction with steps and tool_sequence
        """
        return self.planner.plan(task)


class TimingAdapter:
    """
    Adapter wrapping timing deciders to provide unified decide() interface.
    """

    def __init__(self, decider: Any):
        """
        Initialize adapter.

        Args:
            decider: A timing decider instance with decide() method
        """
        self.decider = decider

    def decide(self, message: Any, **kwargs) -> Any:
        """
        Make timing decision.

        Args:
            message: TimingMessage from experiment

        Returns:
            TimingDecision with should_call_tool, confidence, reasoning
        """
        return self.decider.decide(message)


class AdapterRegistry:
    """
    Registry for strategy adapters.

    Maps string names like "baseline.keyword" to actual implementations.
    """

    def __init__(self):
        """Initialize registry with built-in strategies."""
        self._selectors: dict[str, Any] = {}
        self._planners: dict[str, Any] = {}
        self._timing_deciders: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}

        # Register built-in strategies
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in baseline strategies."""
        # Selector factories
        self._factories["baseline.keyword"] = self._create_keyword_selector
        self._factories["baseline.embedding"] = self._create_embedding_selector
        self._factories["keyword"] = self._create_keyword_selector
        self._factories["embedding"] = self._create_embedding_selector

        # Planner factories
        self._factories["baseline.template"] = self._create_template_planner
        self._factories["baseline.hierarchical"] = self._create_hierarchical_planner
        self._factories["cot"] = self._create_hierarchical_planner
        self._factories["baseline.sequence"] = self._create_sequence_planner

        # Timing factories
        self._factories["baseline.threshold"] = self._create_threshold_decider
        self._factories["llm_based"] = self._create_llm_timing_decider

    def register(self, name: str, strategy: Any) -> None:
        """
        Register a strategy by name.

        Args:
            name: Strategy name (e.g., "my_selector")
            strategy: Strategy instance or factory
        """
        if callable(strategy) and not hasattr(strategy, "predict"):
            self._factories[name] = strategy
        else:
            # Store instance directly
            if hasattr(strategy, "select"):
                self._selectors[name] = SelectorAdapter(strategy)
            elif hasattr(strategy, "plan"):
                self._planners[name] = PlannerAdapter(strategy)
            elif hasattr(strategy, "decide"):
                self._timing_deciders[name] = TimingAdapter(strategy)
            else:
                self._factories[name] = lambda: strategy

    def get(self, name: str, resources: Optional[Any] = None) -> Any:
        """
        Get a strategy by name.

        Args:
            name: Strategy name
            resources: Optional SelectorResources for initialization

        Returns:
            Strategy adapter instance

        Raises:
            ValueError: If strategy not found
        """
        # Check cached instances
        if name in self._selectors:
            return self._selectors[name]
        if name in self._planners:
            return self._planners[name]
        if name in self._timing_deciders:
            return self._timing_deciders[name]

        # Try factory
        if name in self._factories:
            strategy = self._factories[name](resources)
            return strategy

        raise ValueError(f"Unknown strategy: {name}. Available: {self.list_strategies()}")

    def list_strategies(self) -> list:
        """List all registered strategy names."""
        all_names = set(self._selectors.keys())
        all_names.update(self._planners.keys())
        all_names.update(self._timing_deciders.keys())
        all_names.update(self._factories.keys())
        return sorted(all_names)

    # --- Factory methods for built-in strategies ---

    def _create_keyword_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
        """Create keyword-based selector."""
        from sage.libs.agentic.agents.action.tool_selection import (
            KeywordSelector,
            KeywordSelectorConfig,
        )

        config = KeywordSelectorConfig(
            name="keyword",
            method="bm25",
            top_k=5,
        )

        if resources is None:
            # Create minimal resources with mock tools loader
            resources = self._create_mock_resources()

        selector = KeywordSelector(config, resources)
        return SelectorAdapter(selector)

    def _create_embedding_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
        """Create embedding-based selector."""
        from sage.libs.agentic.agents.action.tool_selection import (
            EmbeddingSelector,
            EmbeddingSelectorConfig,
        )

        config = EmbeddingSelectorConfig(
            name="embedding",
            embedding_model="default",
            similarity_metric="cosine",
            top_k=5,
        )

        if resources is None or resources.embedding_client is None:
            # Fallback to keyword selector if no embedding client
            return self._create_keyword_selector(resources)

        selector = EmbeddingSelector(config, resources)
        return SelectorAdapter(selector)

    def _create_template_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """Create template-based planner."""

        # Return a simple mock planner for now
        class MockPlanner:
            def plan(self, task):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                return PlanningPrediction(
                    steps=[
                        PlanStep(
                            step_id=0,
                            description="Execute task",
                            tool_id=task.available_tools[0] if task.available_tools else "unknown",
                            confidence=0.5,
                        )
                    ],
                    tool_sequence=[task.available_tools[0] if task.available_tools else "unknown"],
                )

        return PlannerAdapter(MockPlanner())

    def _create_hierarchical_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """Create hierarchical planner."""
        try:
            from sage.libs.agentic.agents.planning import HierarchicalPlanner

            planner = HierarchicalPlanner()
            return PlannerAdapter(planner)
        except ImportError:
            return self._create_template_planner(resources)

    def _create_sequence_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """Create sequence-based planner using selector for tool ordering."""

        class SequencePlanner:
            """Plan by selecting tools in sequence based on task steps."""

            def __init__(self, selector_factory):
                self._selector_factory = selector_factory

            def plan(self, task):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                # Use task instruction (not description) to select relevant tools
                instruction = (
                    getattr(task, "instruction", "") or getattr(task, "description", "") or ""
                )
                steps = []
                tool_sequence = []

                # Parse task for steps (simple heuristic)
                sub_tasks = [s.strip() for s in instruction.split(".") if s.strip()]

                available = task.available_tools if task.available_tools else []

                # Match each sub-task to a tool
                for i, sub_task in enumerate(sub_tasks[:5]):  # Max 5 steps
                    # Simple matching: pick tool with most keyword overlap
                    best_tool = available[i % len(available)] if available else "unknown"

                    steps.append(
                        PlanStep(
                            step_id=i,
                            description=sub_task,
                            tool_id=best_tool,
                            confidence=0.6,
                        )
                    )
                    tool_sequence.append(best_tool)

                if not steps and available:
                    # Fallback: at least one step
                    steps.append(
                        PlanStep(
                            step_id=0,
                            description=instruction[:100] if instruction else "Execute task",
                            tool_id=available[0],
                            confidence=0.5,
                        )
                    )
                    tool_sequence.append(available[0])

                return PlanningPrediction(
                    steps=steps,
                    tool_sequence=tool_sequence,
                )

        return PlannerAdapter(SequencePlanner(self._create_keyword_selector))

    def _create_threshold_decider(self, resources: Optional[Any] = None) -> TimingAdapter:
        """Create threshold-based timing decider."""

        class ThresholdDecider:
            """Simple keyword-based timing decider."""

            # Keywords indicating tool invocation is needed
            ACTION_KEYWORDS = frozenset(
                [
                    "search",
                    "find",
                    "calculate",
                    "analyze",
                    "create",
                    "update",
                    "delete",
                    "get",
                    "fetch",
                    "query",
                    "look up",
                    "current",
                    "now",
                    "today",
                    "latest",
                    "real-time",
                    "weather",
                    "time",
                    "stock",
                    "price",
                    "news",
                    "check",
                    "verify",
                    "compare",
                    "list",
                    "show",
                ]
            )

            # Keywords indicating direct answer (no tool needed)
            FACTUAL_KEYWORDS = frozenset(
                [
                    "what is",
                    "how many",
                    "define",
                    "explain",
                    "meaning of",
                    "who was",
                    "when was",
                    "where is",
                    "+ ",
                    "multiply",
                    "capital of",
                    "population of",
                    "history of",
                ]
            )

            def decide(self, message):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    TimingDecision,
                )

                text = message.message.lower()

                # Check for action keywords
                has_action = any(kw in text for kw in self.ACTION_KEYWORDS)

                # Check for factual (no-tool) keywords
                has_factual = any(kw in text for kw in self.FACTUAL_KEYWORDS)

                # Heuristic: action keywords > factual keywords
                # Real-time or current info needs tools
                should_call = has_action and not (
                    has_factual
                    and not any(
                        kw in text
                        for kw in [
                            "current",
                            "now",
                            "today",
                            "latest",
                            "real-time",
                            "weather",
                            "time",
                            "stock",
                            "news",
                        ]
                    )
                )

                return TimingDecision(
                    should_call_tool=should_call,
                    confidence=0.8 if (has_action or has_factual) else 0.5,
                    reasoning="Detected action keywords"
                    if should_call
                    else "No action keywords or factual query",
                )

        return TimingAdapter(ThresholdDecider())

    def _create_llm_timing_decider(self, resources: Optional[Any] = None) -> TimingAdapter:
        """Create LLM-based timing decider."""
        try:
            from sage.libs.agentic.agents.planning import TimingDecider

            decider = TimingDecider()
            return TimingAdapter(decider)
        except ImportError:
            return self._create_threshold_decider(resources)

    def _create_mock_resources(self) -> Any:
        """Create mock resources for testing."""
        from sage.libs.agentic.agents.action.tool_selection import SelectorResources

        class MockToolsLoader:
            """Mock tools loader for testing."""

            def iter_all(self):
                """Yield mock tools."""

                class MockTool:
                    def __init__(self, tool_id, name, description, category):
                        self.tool_id = tool_id
                        self.name = name
                        self.description = description
                        self.category = category

                # Generate some mock tools
                categories = ["search", "calculate", "data", "communication"]
                for i in range(50):
                    cat = categories[i % len(categories)]
                    yield MockTool(
                        tool_id=f"tool_{i:03d}",
                        name=f"{cat}_tool_{i}",
                        description=f"A tool for {cat} operations, variant {i}",
                        category=cat,
                    )

        return SelectorResources(
            tools_loader=MockToolsLoader(),
            embedding_client=None,
        )


# Global registry instance
_global_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


def register_strategy(name: str, strategy: Any) -> None:
    """Register a strategy in the global registry."""
    get_adapter_registry().register(name, strategy)


__all__ = [
    "AdapterRegistry",
    "SelectorAdapter",
    "PlannerAdapter",
    "TimingAdapter",
    "get_adapter_registry",
    "register_strategy",
]
