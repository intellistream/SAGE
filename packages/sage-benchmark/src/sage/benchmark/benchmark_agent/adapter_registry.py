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
    Adapter wrapping tool selectors to provide unified predict()/select() interface.

    Maps the selector's select() method to predict() for benchmark compatibility.
    Also provides select() method for run_all_experiments.py compatibility.
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

    def select(self, query: Any, candidate_tools: Optional[list] = None, top_k: int = 5) -> list:
        """
        Select tools for a query (alias for predict with simpler interface).

        This method is provided for compatibility with run_all_experiments.py
        which calls selector.select(query, candidate_tools, top_k=top_k).

        Args:
            query: Either a string (instruction) or ToolSelectionQuery object
            candidate_tools: Optional list of candidate tools (may be ignored if
                           selector has its own tool corpus)
            top_k: Number of tools to select

        Returns:
            List of ToolPrediction objects or tool IDs
        """
        from sage.libs.agentic.agents.action.tool_selection.schemas import (
            ToolSelectionQuery as SelectorQuery,
        )

        # Ensure candidate_tools is always a list (never None)
        tools = candidate_tools if candidate_tools is not None else []

        # Handle string query (from run_all_experiments.py)
        if isinstance(query, str):
            selector_query = SelectorQuery(
                sample_id="runtime",
                instruction=query,
                candidate_tools=tools,
                context={},
            )
        # Handle dict query
        elif isinstance(query, dict):
            tools_from_dict = query.get("candidate_tools", [])
            selector_query = SelectorQuery(
                sample_id=query.get("sample_id", "runtime"),
                instruction=query.get("instruction", str(query)),
                candidate_tools=tools if tools else (tools_from_dict or []),
                context=query.get("context", {}),
            )
        # Handle query object with attributes
        elif hasattr(query, "instruction"):
            tools_from_obj = getattr(query, "candidate_tools", [])
            selector_query = SelectorQuery(
                sample_id=getattr(query, "sample_id", "runtime"),
                instruction=query.instruction,
                candidate_tools=tools if tools else (tools_from_obj or []),
                context=getattr(query, "context", {}),
            )
        else:
            # Fallback: treat query as instruction string
            selector_query = SelectorQuery(
                sample_id="runtime",
                instruction=str(query),
                candidate_tools=tools,
                context={},
            )

        try:
            result = self.selector.select(selector_query, top_k=top_k)
            return result
        except Exception as e:
            # If selector fails, return empty list with debug info
            import logging

            logging.getLogger(__name__).warning(
                f"Selector failed for query '{str(query)[:50]}...': {e}"
            )
            return []


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
        self._factories["baseline.hybrid"] = self._create_hybrid_selector
        self._factories["keyword"] = self._create_keyword_selector
        self._factories["embedding"] = self._create_embedding_selector
        self._factories["hybrid"] = self._create_hybrid_selector
        # Aliased names for benchmark scripts
        self._factories["selector.keyword"] = self._create_keyword_selector
        self._factories["selector.embedding"] = self._create_embedding_selector
        self._factories["selector.hybrid"] = self._create_hybrid_selector
        # SOTA selector strategies
        self._factories["selector.gorilla"] = self._create_gorilla_selector
        self._factories["gorilla"] = self._create_gorilla_selector
        # ToolLLM DFSDT selector
        self._factories["selector.dfsdt"] = self._create_dfsdt_selector
        self._factories["selector.toolllm"] = self._create_dfsdt_selector  # Alias
        self._factories["dfsdt"] = self._create_dfsdt_selector
        self._factories["toolllm"] = self._create_dfsdt_selector  # Alias

        # Planner factories
        self._factories["baseline.template"] = self._create_template_planner
        self._factories["baseline.hierarchical"] = self._create_hierarchical_planner
        self._factories["cot"] = self._create_hierarchical_planner
        self._factories["baseline.sequence"] = self._create_sequence_planner
        # Challenge 2 planner strategies
        self._factories["planner.simple"] = self._create_simple_planner
        self._factories["planner.hierarchical"] = self._create_hierarchical_planning_strategy
        self._factories["planner.llm_based"] = self._create_llm_planning_strategy
        # ReAct planner (SOTA strategy)
        self._factories["planner.react"] = self._create_react_planner
        self._factories["react"] = self._create_react_planner  # Alias
        # Tree-of-Thoughts planner (SOTA strategy)
        self._factories["planner.tot"] = self._create_tot_planner
        self._factories["planner.tree_of_thoughts"] = self._create_tot_planner  # Alias

        # Timing factories
        self._factories["baseline.threshold"] = self._create_threshold_decider
        self._factories["llm_based"] = self._create_llm_timing_decider
        # New timing strategies for benchmark
        self._factories["timing.rule_based"] = self._create_rule_based_decider
        self._factories["timing.llm_based"] = self._create_llm_timing_decider
        self._factories["timing.hybrid"] = self._create_hybrid_timing_decider
        self._factories["timing.embedding"] = self._create_embedding_timing_decider

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

    def _create_hybrid_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
        """Create hybrid selector combining keyword and embedding."""
        # Try to import HybridSelector from the library
        try:
            from sage.libs.agentic.agents.action.tool_selection import (
                HybridSelector,
                HybridSelectorConfig,
            )

            config = HybridSelectorConfig(
                name="hybrid",
                keyword_weight=0.4,
                embedding_weight=0.6,
                keyword_method="bm25",
                embedding_model="default",
                fusion_method="weighted_sum",
                top_k=5,
            )

            if resources is None:
                resources = self._create_mock_resources()

            selector = HybridSelector(config, resources)
            return SelectorAdapter(selector)
        except ImportError:
            # Fallback: create inline hybrid selector
            return self._create_inline_hybrid_selector(resources)

    def _create_gorilla_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
        """
        Create Gorilla-style retrieval-augmented selector.

        Gorilla uses a two-stage approach:
        1. Embedding retrieval to find candidate tools
        2. LLM selection from retrieved candidates

        Reference: Patil et al. (2023) "Gorilla: Large Language Model Connected with Massive APIs"
        """
        try:
            from sage.libs.agentic.agents.action.tool_selection import (
                GorillaSelector,
                GorillaSelectorConfig,
            )

            config = GorillaSelectorConfig(
                name="gorilla",
                top_k_retrieve=20,
                top_k_select=5,
                embedding_model="default",
                llm_model="auto",  # Uses IntelligentLLMClient.create_auto()
                similarity_metric="cosine",
                temperature=0.1,
                use_detailed_docs=True,
                max_context_tools=15,
            )

            if resources is None:
                resources = self._create_mock_resources()

            # Gorilla requires embedding client with batch interface
            if resources.embedding_client is None:
                # Try to create embedding client
                try:
                    from sage.common.components.sage_embedding import (
                        EmbeddingFactory,
                        adapt_embedding_client,
                    )

                    # EmbeddingFactory returns single-text interface, need to adapt
                    raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
                    # Adapt to batch interface (embed(texts: list[str]))
                    embedding_client = adapt_embedding_client(raw_embedder)
                    resources.embedding_client = embedding_client
                except Exception as e:
                    # Fall back to hybrid selector if embedding not available
                    self.logger.warning(
                        f"Gorilla selector requires embedding client ({e}). "
                        "Falling back to hybrid selector."
                    )
                    return self._create_hybrid_selector(resources)

            selector = GorillaSelector(config, resources)
            return SelectorAdapter(selector)

        except ImportError as e:
            # Fallback to hybrid selector
            import logging

            logging.getLogger(__name__).warning(
                f"GorillaSelector not available ({e}), falling back to hybrid"
            )
            return self._create_hybrid_selector(resources)

    def _create_dfsdt_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
        """
        Create DFSDT (Depth-First Search-based Decision Tree) selector.

        Based on ToolLLM paper (Qin et al., 2023):
        "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs"

        Key features:
        - LLM-guided scoring for semantic understanding
        - Tree search for exploring multiple tool combinations
        - Diversity prompting to avoid local optima
        - Keyword pre-filtering for efficiency
        """
        try:
            from sage.libs.agentic.agents.action.tool_selection import (
                DFSDTSelector,
                DFSDTSelectorConfig,
            )

            config = DFSDTSelectorConfig(
                name="dfsdt",
                max_depth=3,
                beam_width=5,
                llm_model="auto",  # Uses IntelligentLLMClient.create_auto()
                temperature=0.1,
                use_diversity_prompt=True,
                score_threshold=0.3,
                use_keyword_prefilter=True,
                prefilter_k=20,
                top_k=5,
            )

            if resources is None:
                resources = self._create_mock_resources()

            selector = DFSDTSelector(config, resources)
            return SelectorAdapter(selector)

        except ImportError as e:
            # Fallback to hybrid selector
            import logging

            logging.getLogger(__name__).warning(
                f"DFSDTSelector not available ({e}), falling back to hybrid"
            )
            return self._create_hybrid_selector(resources)

    def _create_inline_hybrid_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
        """Create inline hybrid selector when library version unavailable."""
        from sage.libs.agentic.agents.action.tool_selection import (
            KeywordSelector,
            KeywordSelectorConfig,
            ToolPrediction,
        )

        class InlineHybridSelector:
            """Inline hybrid selector for benchmark fallback."""

            def __init__(self, resources):
                self.resources = resources
                # Create keyword selector as base
                config = KeywordSelectorConfig(
                    name="keyword",
                    method="bm25",
                    top_k=10,
                )
                self._keyword_selector = KeywordSelector(config, resources)
                self.name = "hybrid"

            def select(self, query, top_k=5):
                """Select using keyword with boosting."""
                # Use keyword selector
                results = self._keyword_selector.select(query, top_k=top_k * 2)

                # Simple score boosting based on query-tool match
                boosted = []
                query_lower = query.instruction.lower()

                for pred in results[:top_k]:
                    # Check if tool matches query keywords better
                    tool_text = self.resources.tools_loader.get_tool(pred.tool_id)
                    tool_desc = getattr(tool_text, "description", "") or ""

                    # Simple boost: increase score if query words in description
                    words = query_lower.split()
                    matches = sum(1 for w in words if w in tool_desc.lower())
                    boost = 1.0 + (matches * 0.1)

                    boosted.append(
                        ToolPrediction(
                            tool_id=pred.tool_id,
                            score=min(pred.score * boost, 1.0),
                            metadata={"method": "hybrid_inline", "boost": boost},
                        )
                    )

                boosted.sort(key=lambda x: x.score, reverse=True)

                # Optionally use LLM reranker via IntelligentLLMClient.create_auto()
                # This uses LOCAL-FIRST strategy: local vLLM (8001/8000) -> cloud API fallback
                # Set SAGE_HYBRID_ENABLE_LLM_RERANK=1 to enable
                import os

                enable_llm_rerank = os.environ.get("SAGE_HYBRID_ENABLE_LLM_RERANK", "0") == "1"

                if enable_llm_rerank and not hasattr(self, "_llm_client_checked"):
                    self._llm_client_checked = True
                    try:
                        from sage.common.components.sage_llm.client import IntelligentLLMClient

                        # Use singleton to avoid repeated model loading
                        self._llm_client = IntelligentLLMClient.get_instance(
                            cache_key="benchmark_hybrid", probe_timeout=1.0
                        )
                    except Exception:
                        self._llm_client = None

                if enable_llm_rerank and getattr(self, "_llm_client", None) is not None:
                    try:
                        reranked = self._llm_rerank(self._llm_client, query, boosted, top_k)
                        if reranked:
                            return reranked
                    except Exception:
                        pass  # Silently fall back to keyword-boosted results

                return boosted[:top_k]

            def _llm_rerank(self, llm, query, boosted, top_k):
                """Use LLM to rerank candidates."""
                import json
                import re

                # Prepare prompt
                cand_infos = []
                for p in boosted[: max(10, top_k)]:
                    try:
                        t = self.resources.tools_loader.get_tool(p.tool_id)
                        desc = getattr(t, "description", "") or ""
                    except Exception:
                        desc = ""
                    cand_infos.append(f"{p.tool_id}: {desc[:100]}")

                messages = [
                    {
                        "role": "system",
                        "content": "You are an assistant that ranks candidate tools by relevance. Return a JSON array of tool ids sorted most->least relevant. Only output the JSON array.",
                    },
                    {
                        "role": "user",
                        "content": f"Instruction: {query.instruction}\n\nCandidates:\n"
                        + "\n".join(cand_infos),
                    },
                ]

                # IntelligentLLMClient.chat() returns string directly
                resp = llm.chat(messages, temperature=0.0, max_tokens=512)

                # Parse response
                txt = resp if isinstance(resp, str) else str(resp)
                m = re.search(r"\[.*\]", txt, re.S)
                if not m:
                    return None

                try:
                    ranked = json.loads(m.group(0))
                except Exception:
                    return None

                if not isinstance(ranked, list):
                    return None

                # Build final predictions
                id_to_pred = {p.tool_id: p for p in boosted}
                final_preds = []
                for tid in ranked:
                    if tid in id_to_pred:
                        final_preds.append(id_to_pred[tid])
                for p in boosted:
                    if p.tool_id not in {fp.tool_id for fp in final_preds}:
                        final_preds.append(p)

                return final_preds[:top_k]

        if resources is None:
            resources = self._create_mock_resources()

        selector = InlineHybridSelector(resources)
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

    def _create_react_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """
        Create ReAct planner implementing Thought-Action-Observation loop.

        ReAct (Reasoning + Acting) generates plans by interleaving:
        1. Thought: Reasoning about current state
        2. Action: Selecting tool to use
        3. Observation: Expected result (predicted in planning mode)

        Reference: "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2023)
        """

        class ReActPlannerWrapper:
            """Wrapper for ReAct planner with benchmark-compatible interface."""

            def __init__(self):
                self._planner = None
                self._llm_client = None
                self._initialized = False

            def _ensure_initialized(self):
                """Lazy initialization of ReAct planner."""
                if self._initialized:
                    return

                self._initialized = True

                try:
                    from sage.libs.agentic.agents.planning import ReActConfig, ReActPlanner

                    # Try to get LLM client
                    llm_client = self._get_llm_client()

                    config = ReActConfig(
                        min_steps=5,
                        max_steps=10,
                        max_iterations=12,
                        temperature=0.2,
                    )

                    self._planner = ReActPlanner(
                        config=config,
                        llm_client=llm_client,
                    )
                except ImportError as e:
                    import logging

                    logging.warning(f"ReActPlanner import failed: {e}")
                    self._planner = None

            def _get_llm_client(self):
                """Get LLM client with local-first strategy."""
                import os

                # Try local vLLM first
                try:
                    from sage.common.components.sage_llm.client import IntelligentLLMClient

                    local_endpoints = [
                        ("http://localhost:8001/v1", 8001),
                        ("http://localhost:8000/v1", 8000),
                    ]

                    for endpoint, port in local_endpoints:
                        detected_model = IntelligentLLMClient._probe_vllm_service(
                            endpoint, timeout=1.0
                        )
                        if detected_model:
                            return IntelligentLLMClient(
                                model_name=detected_model,
                                base_url=endpoint,
                                api_key=os.getenv("VLLM_API_KEY", ""),
                            )

                    # Fall back to cloud API
                    api_key = (
                        os.getenv("SAGE_CHAT_API_KEY")
                        or os.getenv("ALIBABA_API_KEY")
                        or os.getenv("OPENAI_API_KEY")
                    )

                    if api_key and "your_" not in api_key.lower():
                        return IntelligentLLMClient(
                            model_name=os.getenv("SAGE_CHAT_MODEL", "qwen-turbo-2025-02-11"),
                            base_url=os.getenv(
                                "SAGE_CHAT_BASE_URL",
                                "https://dashscope.aliyuncs.com/compatible-mode/v1",
                            ),
                            api_key=api_key,
                        )
                except Exception:
                    pass

                return None

            def plan(self, task):
                """Generate plan using ReAct strategy."""
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                self._ensure_initialized()

                instruction = getattr(task, "instruction", "") or ""
                available_tools = getattr(task, "available_tools", []) or []

                if not available_tools:
                    return PlanningPrediction(steps=[], tool_sequence=[])

                # Try ReAct planner if available
                if self._planner is not None:
                    try:
                        from sage.libs.agentic.agents.planning import (
                            PlanRequest,
                            ToolMetadata,
                        )

                        # Convert available tools to ToolMetadata
                        tools = [
                            ToolMetadata(
                                tool_id=t,
                                name=t,
                                description=f"Tool: {t}",
                                category="general",
                            )
                            for t in available_tools
                        ]

                        request = PlanRequest(
                            goal=instruction,
                            tools=tools,
                            constraints=[],
                            min_steps=5,
                            max_steps=10,
                        )

                        result = self._planner.plan(request)

                        if result.success and result.steps:
                            steps = []
                            tool_sequence = []

                            for i, step in enumerate(result.steps):
                                tool_id = step.tool_id or step.action
                                if tool_id in available_tools:
                                    steps.append(
                                        PlanStep(
                                            step_id=i,
                                            description=step.description or step.action,
                                            tool_id=tool_id,
                                            confidence=0.8,
                                        )
                                    )
                                    tool_sequence.append(tool_id)

                            if steps:
                                return PlanningPrediction(
                                    steps=steps,
                                    tool_sequence=tool_sequence,
                                )
                    except Exception:
                        pass

                # Fallback: use heuristic-based planning
                return self._fallback_plan(instruction, available_tools)

            def _fallback_plan(self, instruction: str, available_tools: list[str]):
                """Heuristic-based fallback planning."""
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                steps = []
                tool_sequence = []
                instruction_lower = instruction.lower()

                # Score tools by relevance
                tool_scores = []
                for tool in available_tools:
                    score = 0
                    tool_lower = tool.lower()
                    tool_words = set(tool_lower.replace("_", " ").split())
                    instruction_words = set(instruction_lower.replace(",", " ").split())

                    # Word overlap
                    overlap = len(tool_words & instruction_words)
                    score += overlap * 2

                    # Action keyword matching
                    if any(w in tool_lower for w in ["read", "get", "fetch", "load"]):
                        if any(w in instruction_lower for w in ["read", "get", "load", "fetch"]):
                            score += 2
                    if any(w in tool_lower for w in ["write", "save", "send", "post"]):
                        if any(w in instruction_lower for w in ["write", "save", "send", "post"]):
                            score += 2
                    if any(w in tool_lower for w in ["process", "transform", "convert"]):
                        if any(w in instruction_lower for w in ["process", "convert", "transform"]):
                            score += 2

                    tool_scores.append((tool, score))

                tool_scores.sort(key=lambda x: x[1], reverse=True)

                # Select top tools
                selected = [t for t, s in tool_scores[:8] if s > 0]
                if len(selected) < 5:
                    for t, _ in tool_scores:
                        if t not in selected:
                            selected.append(t)
                        if len(selected) >= 5:
                            break

                for i, tool in enumerate(selected[:10]):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            description=f"ReAct step {i + 1}: Use {tool}",
                            tool_id=tool,
                            confidence=0.6,
                        )
                    )
                    tool_sequence.append(tool)

                return PlanningPrediction(steps=steps, tool_sequence=tool_sequence)

        return PlannerAdapter(ReActPlannerWrapper())

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
        """Create LLM-based timing decider using embedded VLLMService (local-first).

        Priority:
        1. Embedded VLLMService (内嵌 vLLM，无需启动服务) - highest
        2. Local vLLM API service (localhost:8001 or 8000) - if already running
        3. Cloud API via SAGE_CHAT_* environment variables - fallback
        """

        class LLMTimingDecider:
            """
            LLM-based timing decider with local-first strategy.

            Uses embedded VLLMService when available, falls back to API-based client.
            """

            TIMING_PROMPT = """You are an AI assistant that determines whether a user's message requires tool invocation or can be answered directly from your knowledge.

Analyze the following user message and determine:
1. Does this message require real-time information (weather, stock prices, current time, etc.)?
2. Does this message require performing an action (search, calculate, create file, send email, etc.)?
3. Does this message require accessing external data or APIs?

If ANY of the above is true, the user needs a tool call.
If the message is asking for factual knowledge, explanations, opinions, creative writing, or general conversation, it can be answered directly without tools.

User message: "{message}"

Respond in JSON format:
{{
    "should_call_tool": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Only output the JSON, nothing else."""

            def __init__(self, llm_client=None):
                self._client = llm_client
                self._vllm_service = None
                self._use_embedded_vllm = False
                self._initialized = False

            def _ensure_client(self):
                """Lazy initialization with embedded VLLMService priority."""
                if self._initialized:
                    return self._vllm_service is not None or self._client is not None

                self._initialized = True
                import os

                # Step 1: Try embedded VLLMService (内嵌模式，无需单独启动服务)
                try:
                    from sage.common.components.sage_llm import VLLMService

                    model_id = os.getenv("SAGE_BENCHMARK_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
                    self._vllm_service = VLLMService(
                        {
                            "model_id": model_id,
                            "auto_download": True,
                            "sampling": {"temperature": 0.1, "max_tokens": 256},
                        }
                    )
                    self._vllm_service.setup()
                    self._use_embedded_vllm = True
                    print(f"✅ [Timing] 使用内嵌 VLLMService: {model_id}")
                    return True
                except Exception:
                    self._use_embedded_vllm = False
                    # VLLMService not available, try API client

                # Step 2: Try API-based client (local vLLM or cloud)
                try:
                    from sage.common.components.sage_llm import IntelligentLLMClient

                    # Use singleton to avoid repeated model loading
                    self._client = IntelligentLLMClient.get_instance(
                        cache_key="benchmark_timing", probe_timeout=1.0
                    )
                    return True
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Failed to initialize LLM client: {e}. Falling back to rule-based."
                    )
                    self._client = None
                    return False

            def decide(self, message):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    TimingDecision,
                )

                # Ensure LLM client/service is initialized
                if not self._ensure_client():
                    # No LLM available, fall back to rule-based
                    return self._fallback_decide(message)

                try:
                    import json

                    prompt = self.TIMING_PROMPT.format(message=message.message)

                    # Use embedded VLLMService if available
                    if self._use_embedded_vllm and self._vllm_service is not None:
                        results = self._vllm_service.generate(prompt)
                        if results and results[0].get("generations"):
                            content = results[0]["generations"][0]["text"].strip()
                        else:
                            return self._fallback_decide(message)
                    elif self._client is not None:
                        # Use API-based client
                        response = self._client.chat(
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.1,
                            max_tokens=200,
                        )
                        content = response.choices[0].message.content.strip()
                    else:
                        return self._fallback_decide(message)

                    # Parse JSON response
                    # Handle potential markdown code blocks
                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    content = content.strip()

                    result = json.loads(content)
                    return TimingDecision(
                        should_call_tool=result.get("should_call_tool", False),
                        confidence=float(result.get("confidence", 0.7)),
                        reasoning=f"[LLM] {result.get('reasoning', 'LLM decision')}",
                    )
                except Exception:
                    # Fall through to rule-based
                    return self._fallback_decide(message)

            def _fallback_decide(self, message):
                """Fallback to simple rule-based for failed LLM calls."""
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    TimingDecision,
                )

                text = message.message.lower()
                action_keywords = [
                    "search",
                    "find",
                    "calculate",
                    "weather",
                    "stock",
                    "price",
                    "current",
                    "now",
                    "today",
                    "create",
                    "send",
                    "schedule",
                ]
                has_action = any(kw in text for kw in action_keywords)

                return TimingDecision(
                    should_call_tool=has_action,
                    confidence=0.6,
                    reasoning="[Fallback] Simple keyword match",
                )

        return TimingAdapter(LLMTimingDecider())

    def _create_rule_based_decider(self, resources: Optional[Any] = None) -> TimingAdapter:
        """Create rule-based timing decider with comprehensive keyword matching."""

        class RuleBasedDecider:
            """
            Enhanced rule-based timing decider v2.

            Uses multi-layer pattern matching and keyword analysis to determine
            if a message requires tool invocation.

            Improvements over v1:
            - Added patterns for prediction/forecast queries (stock prices, future events)
            - Added patterns for data lookup queries (calories, nutritional info)
            - Added NO_TOOL patterns for advice/opinion questions
            - Improved confidence scoring with weighted categories
            - Better handling of edge cases (e.g., "should I" questions)
            """

            # Patterns that strongly indicate tool invocation is needed
            TOOL_REQUIRED_PATTERNS = [
                # Real-time information
                r"\b(current|real-time|live|now|today|right now)\b.*\b(weather|temperature|stock|price|news|time|traffic)\b",
                r"\bwhat('s| is) the (current|latest)\b",
                r"\b(weather|temperature|forecast)\s+(in|for|at)\b",
                r"\b(stock|share) (price|value|chart)\b",
                # Time queries
                r"\bwhat('s| is) the\s+(current\s+)?time\s+(in|at)\b",
                r"\bwhat time is it in\b",
                # Prediction/Forecast queries (needs tool for data)
                r"\bwhat will\b.*\b(price|stock|weather|be)\b.*\b(next|tomorrow|week|month)\b",
                r"\bwill it\b.*\b(rain|snow|be sunny|be cold|be hot)\b",
                r"\b(forecast|predict|projection)\s+for\b",
                # Actions and operations
                r"\b(search|find|look up|fetch|retrieve|get|query)\s+(for|the|about)?\b",
                r"\b(calculate|compute|convert)\s+",
                r"\b(create|generate|make|build)\s+(a|an|the)?\s*(file|document|spreadsheet|chart|report)\b",
                r"\b(send|email|schedule|book|reserve|cancel)\s+",
                # File operations (enhanced patterns)
                r"\b(open|close|save|delete|rename|move|copy)\s+(the|a|this)?\s*(file|document|report|spreadsheet)\b",
                r"\bsave\s+(this|the|a)\s+(document|file|data)\b",
                r"\bsave\s+.*\s+as\b",  # "save X as Y"
                r"\bopen\s+(the|a)\s+file\b",
                r"\bdelete\s+(the|a)\s+file\b",
                # Code execution (enhanced patterns)
                r"\b(run|execute|compile|debug|test)\s+(this|the|a)?\s*(code|script|program|command|python|javascript)\b",
                r"\brun\s+this\s+\w+\s+code\b",  # "run this Python code"
                r"\bexecute\s+(this|the)\s+(script|code|program)\b",
                # Database/API operations
                r"\b(select|insert|update|delete)\s+.*\b(from|into|where)\b",
                r"\bapi\s+(call|request|endpoint)\b",
                # Data lookup queries (needs external database)
                r"\bhow many calories\b",
                r"\b(calories|carbs|protein|fat|nutrition)\s+(in|of)\b",
                r"\b(nutritional|nutrition)\s+(info|information|value|data)\b",
                r"\bexchange rate\s+(for|of|between)\b",
                r"\bconvert\s+\d+\s*\w+\s+to\b",
            ]

            # Patterns that indicate NO tool needed (advice, opinion, philosophical)
            NO_TOOL_PATTERNS = [
                # Advice/Opinion questions
                r"\bshould i\b",
                r"\bwhat do you think\b",
                r"\bwhat('s| is) your opinion\b",
                r"\bdo you recommend\b",
                r"\bany (tips|advice|suggestions)\b",
                r"\bis it (a good|worth|better)\b",
                # Personal/Philosophical questions
                r"\bwhat('s| is) the meaning of life\b",
                r"\bwhy (do|should) (we|i|people)\b",
                r"\bhow (do|can) i (feel|cope|deal)\b",
            ]

            # Keywords indicating tool invocation (with weights)
            TOOL_KEYWORDS = frozenset(
                [
                    # Search/Retrieve
                    "search",
                    "find",
                    "look up",
                    "lookup",
                    "fetch",
                    "retrieve",
                    "query",
                    # Actions
                    "calculate",
                    "compute",
                    "convert",
                    "translate",
                    "analyze",
                    # CRUD operations
                    "create",
                    "update",
                    "delete",
                    "modify",
                    "edit",
                    # Real-time indicators
                    "current",
                    "live",
                    "real-time",
                    "realtime",
                    "latest",
                    "now",
                    "today",
                    "right now",
                    # Specific domains requiring tools
                    "weather",
                    "stock",
                    "price",
                    "exchange rate",
                    "traffic",
                    "flight",
                    "news",
                    "calories",
                    "nutritional",
                    # File/System operations
                    "open",
                    "save",
                    "download",
                    "upload",
                    "export",
                    "import",
                    # Scheduling
                    "schedule",
                    "book",
                    "reserve",
                    "remind",
                    "alarm",
                    # Communication
                    "send",
                    "email",
                    "message",
                    "notify",
                    "call",
                    # Code execution
                    "run",
                    "execute",
                    "compile",
                    "debug",
                ]
            )

            # High-weight keywords that strongly suggest tool usage
            HIGH_WEIGHT_TOOL_KEYWORDS = frozenset(
                [
                    "search",
                    "calculate",
                    "weather",
                    "stock",
                    "price",
                    "calories",
                    "execute",
                    "run code",
                    "compile",
                    "exchange rate",
                    "schedule",
                    "book",
                    "send email",
                ]
            )

            # Keywords indicating NO tool needed (direct answer)
            NO_TOOL_KEYWORDS = frozenset(
                [
                    # Definitions
                    "what is",
                    "what are",
                    "define",
                    "definition",
                    "meaning of",
                    "explain",
                    "describe",
                    # Factual (static knowledge)
                    "who was",
                    "who is",
                    "who invented",
                    "who wrote",
                    "when was",
                    "when did",
                    "where is",
                    "where was",
                    "capital of",
                    "population of",
                    "history of",
                    # Knowledge/Educational
                    "how does",
                    "how do",
                    "why do",
                    "why does",
                    "what causes",
                    # Conversational
                    "hello",
                    "hi",
                    "thanks",
                    "thank you",
                    "goodbye",
                    "bye",
                    # Opinion/Advice (important: these do NOT need tools)
                    "what do you think",
                    "your opinion",
                    "any tips",
                    "advice",
                    "suggest",
                    "recommend",
                    "should i",
                    "is it worth",
                    "is it a good idea",
                    "pros and cons",
                    # Creative writing
                    "write a",
                    "compose",
                    "create a story",
                    "create a poem",
                    "tell me a story",
                    # Math/Science knowledge (not calculations)
                    "pythagorean theorem",
                    "quadratic formula",
                    "what is pi",
                ]
            )

            # High-weight keywords that strongly suggest NO tool
            HIGH_WEIGHT_NO_TOOL_KEYWORDS = frozenset(
                [
                    "should i",
                    "what do you think",
                    "your opinion",
                    "recommend",
                    "advice",
                    "capital of",
                    "who invented",
                    "who wrote",
                    "explain",
                    "define",
                ]
            )

            def __init__(self):
                import re

                self._compiled_tool_patterns = [
                    re.compile(p, re.IGNORECASE) for p in self.TOOL_REQUIRED_PATTERNS
                ]
                self._compiled_no_tool_patterns = [
                    re.compile(p, re.IGNORECASE) for p in self.NO_TOOL_PATTERNS
                ]

            def decide(self, message):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    TimingDecision,
                )

                text = message.message.lower()

                # Priority 1: Check for strong NO-TOOL patterns first (advice/opinion)
                # These override tool patterns because the question is fundamentally
                # asking for advice, not data retrieval
                no_tool_pattern_match = any(p.search(text) for p in self._compiled_no_tool_patterns)
                if no_tool_pattern_match:
                    # Even if there are tool-like keywords, the core question is advice
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=0.9,
                        reasoning="Strong pattern match for advice/opinion question (no tool needed)",
                    )

                # Priority 2: Check for strong TOOL patterns
                tool_pattern_match = any(p.search(text) for p in self._compiled_tool_patterns)
                if tool_pattern_match:
                    return TimingDecision(
                        should_call_tool=True,
                        confidence=0.95,
                        reasoning="Strong pattern match for tool invocation",
                    )

                # Priority 3: Weighted keyword analysis
                # Calculate weighted scores
                tool_score = sum(1 for kw in self.TOOL_KEYWORDS if kw in text)
                high_tool_score = sum(2 for kw in self.HIGH_WEIGHT_TOOL_KEYWORDS if kw in text)
                total_tool_score = tool_score + high_tool_score

                no_tool_score = sum(1 for kw in self.NO_TOOL_KEYWORDS if kw in text)
                high_no_tool_score = sum(
                    2 for kw in self.HIGH_WEIGHT_NO_TOOL_KEYWORDS if kw in text
                )
                total_no_tool_score = no_tool_score + high_no_tool_score

                # Decision based on weighted scores
                if total_tool_score > 0 and total_no_tool_score == 0:
                    confidence = min(0.7 + total_tool_score * 0.08, 0.95)
                    return TimingDecision(
                        should_call_tool=True,
                        confidence=confidence,
                        reasoning=f"Tool keywords detected (score: {total_tool_score})",
                    )
                elif total_no_tool_score > 0 and total_tool_score == 0:
                    confidence = min(0.7 + total_no_tool_score * 0.08, 0.95)
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=confidence,
                        reasoning=f"No-tool keywords detected (score: {total_no_tool_score})",
                    )
                elif total_tool_score > total_no_tool_score:
                    score_diff = total_tool_score - total_no_tool_score
                    confidence = min(0.55 + score_diff * 0.08, 0.85)
                    return TimingDecision(
                        should_call_tool=True,
                        confidence=confidence,
                        reasoning=f"More tool keywords ({total_tool_score} vs {total_no_tool_score})",
                    )
                elif total_no_tool_score > total_tool_score:
                    score_diff = total_no_tool_score - total_tool_score
                    confidence = min(0.55 + score_diff * 0.08, 0.85)
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=confidence,
                        reasoning=f"More no-tool keywords ({total_no_tool_score} vs {total_tool_score})",
                    )
                else:
                    # Ambiguous case: use heuristics
                    # Check for question words that might indicate knowledge queries
                    knowledge_indicators = ["what is", "who is", "where is", "when was"]
                    is_knowledge_query = any(ind in text for ind in knowledge_indicators)

                    if is_knowledge_query:
                        return TimingDecision(
                            should_call_tool=False,
                            confidence=0.55,
                            reasoning="Ambiguous - appears to be knowledge query, defaulting to no tool",
                        )

                    # Default: assume no tool needed for truly ambiguous cases
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=0.5,
                        reasoning="Ambiguous - defaulting to no tool",
                    )

        return TimingAdapter(RuleBasedDecider())

    def _create_hybrid_timing_decider(self, resources: Optional[Any] = None) -> TimingAdapter:
        """Create hybrid timing decider combining rule-based and LLM-based approaches."""

        class HybridDecider:
            """
            Hybrid timing decider.

            Uses rule-based detection first for high-confidence cases,
            falls back to LLM for ambiguous cases (if available).
            """

            def __init__(self, rule_decider, llm_decider=None, confidence_threshold=0.7):
                self._rule_decider = rule_decider
                self._llm_decider = llm_decider
                self._threshold = confidence_threshold

            def decide(self, message):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    TimingDecision,
                )

                # First try rule-based
                rule_decision = self._rule_decider.decide(message)

                # If high confidence, return rule-based result
                if rule_decision.confidence >= self._threshold:
                    return TimingDecision(
                        should_call_tool=rule_decision.should_call_tool,
                        confidence=rule_decision.confidence,
                        reasoning=f"[Rule-based] {rule_decision.reasoning}",
                    )

                # For low confidence, try LLM if available
                if self._llm_decider is not None:
                    try:
                        llm_decision = self._llm_decider.decide(message)
                        # Combine results
                        if rule_decision.should_call_tool == llm_decision.should_call_tool:
                            # Agreement - higher confidence
                            combined_conf = min(
                                (rule_decision.confidence + llm_decision.confidence) / 2 + 0.1, 1.0
                            )
                            return TimingDecision(
                                should_call_tool=rule_decision.should_call_tool,
                                confidence=combined_conf,
                                reasoning=f"[Hybrid-agree] Rule: {rule_decision.reasoning}, LLM: {llm_decision.reasoning}",
                            )
                        else:
                            # Disagreement - prefer higher confidence
                            if llm_decision.confidence > rule_decision.confidence:
                                return TimingDecision(
                                    should_call_tool=llm_decision.should_call_tool,
                                    confidence=llm_decision.confidence * 0.9,
                                    reasoning=f"[Hybrid-LLM] {llm_decision.reasoning}",
                                )
                            else:
                                return TimingDecision(
                                    should_call_tool=rule_decision.should_call_tool,
                                    confidence=rule_decision.confidence * 0.9,
                                    reasoning=f"[Hybrid-Rule] {rule_decision.reasoning}",
                                )
                    except Exception:
                        pass  # Fall back to rule-based

                # Return rule-based result
                return TimingDecision(
                    should_call_tool=rule_decision.should_call_tool,
                    confidence=rule_decision.confidence,
                    reasoning=f"[Rule-fallback] {rule_decision.reasoning}",
                )

        # Create rule-based decider
        rule_adapter = self._create_rule_based_decider(resources)
        rule_decider = rule_adapter.decider

        # Try to create LLM decider
        llm_decider = None
        try:
            llm_adapter = self._create_llm_timing_decider(resources)
            llm_decider = llm_adapter.decider
        except Exception:
            pass

        return TimingAdapter(HybridDecider(rule_decider, llm_decider))

    def _create_embedding_timing_decider(self, resources: Optional[Any] = None) -> TimingAdapter:
        """Create embedding-based timing decider using SAGE's EmbeddingService."""

        class EmbeddingTimingDecider:
            """
            Embedding-based timing decider using semantic similarity.

            Uses pre-computed embeddings of typical "tool-needed" and "no-tool-needed"
            messages to classify new queries via cosine similarity.
            """

            # Representative examples for each class
            TOOL_NEEDED_EXAMPLES = [
                "What's the weather like in New York right now?",
                "Search for the latest news about AI",
                "Calculate the compound interest on $10000",
                "What's the current stock price of AAPL?",
                "Send an email to my team",
                "Create a new spreadsheet with sales data",
                "What time is it in Tokyo?",
                "Book a flight from NYC to London",
                "Find restaurants near me",
                "Download the latest report",
            ]

            NO_TOOL_EXAMPLES = [
                "What is the capital of France?",
                "Explain quantum computing to me",
                "Who invented the telephone?",
                "What does photosynthesis mean?",
                "Write a poem about nature",
                "What are the pros and cons of remote work?",
                "How does machine learning work?",
                "Tell me a story about a brave knight",
                "What is 2 + 2?",
                "Thank you for your help!",
            ]

            def __init__(self):
                self._embedder = None
                self._tool_needed_embeddings = None
                self._no_tool_embeddings = None
                self._initialized = False

            def _ensure_initialized(self):
                """Lazy initialization of embedder and example embeddings."""
                if self._initialized:
                    return self._embedder is not None

                self._initialized = True
                try:
                    import os

                    from sage.common.components.sage_embedding import get_embedding_model

                    # Choose embedding method based on environment
                    method = os.getenv("SAGE_EMBEDDING_METHOD", "hash")

                    if method == "hf":
                        try:
                            self._embedder = get_embedding_model(
                                "hf", model="BAAI/bge-small-zh-v1.5"
                            )
                        except Exception:
                            self._embedder = get_embedding_model("hash", dim=384)
                    else:
                        self._embedder = get_embedding_model("hash", dim=384)

                    # Pre-compute example embeddings
                    self._tool_needed_embeddings = [
                        self._embedder.embed(ex) for ex in self.TOOL_NEEDED_EXAMPLES
                    ]
                    self._no_tool_embeddings = [
                        self._embedder.embed(ex) for ex in self.NO_TOOL_EXAMPLES
                    ]
                    return True
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Failed to initialize embedding decider: {e}"
                    )
                    self._embedder = None
                    return False

            def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
                """Compute cosine similarity between two vectors."""
                import math

                dot = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = math.sqrt(sum(a * a for a in vec1))
                norm2 = math.sqrt(sum(b * b for b in vec2))
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                return dot / (norm1 * norm2)

            def decide(self, message):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    TimingDecision,
                )

                if not self._ensure_initialized() or self._embedder is None:
                    # Fallback to simple rule-based
                    text = message.message.lower()
                    action_kws = ["search", "find", "weather", "stock", "current", "now"]
                    has_action = any(kw in text for kw in action_kws)
                    return TimingDecision(
                        should_call_tool=has_action,
                        confidence=0.5,
                        reasoning="[Fallback] Simple keyword match",
                    )

                try:
                    # Embed the query
                    query_embedding = self._embedder.embed(message.message)

                    # Compute average similarity to each class
                    tool_sims = [
                        self._cosine_similarity(query_embedding, ex_emb)
                        for ex_emb in self._tool_needed_embeddings
                    ]
                    no_tool_sims = [
                        self._cosine_similarity(query_embedding, ex_emb)
                        for ex_emb in self._no_tool_embeddings
                    ]

                    avg_tool_sim = sum(tool_sims) / len(tool_sims)
                    avg_no_tool_sim = sum(no_tool_sims) / len(no_tool_sims)

                    # Decision based on higher average similarity
                    should_call = avg_tool_sim > avg_no_tool_sim
                    confidence = abs(avg_tool_sim - avg_no_tool_sim) + 0.5
                    confidence = min(max(confidence, 0.5), 0.95)

                    return TimingDecision(
                        should_call_tool=should_call,
                        confidence=confidence,
                        reasoning=f"[Embedding] tool_sim={avg_tool_sim:.3f}, no_tool_sim={avg_no_tool_sim:.3f}",
                    )
                except Exception as e:
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=0.5,
                        reasoning=f"[Embedding-error] {str(e)[:50]}",
                    )

        return TimingAdapter(EmbeddingTimingDecider())

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

    def _create_simple_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """
        Create simple planner using embedding-based tool matching.

        Uses EmbeddingFactory for semantic similarity matching.
        """

        class EmbeddingBasedPlanner:
            """Planner using embedding similarity for tool selection."""

            def __init__(self):
                self._embedder = None
                self._tool_embeddings_cache: dict[str, list[float]] = {}

            def _get_embedder(self):
                """Lazy initialization of embedder."""
                if self._embedder is None:
                    try:
                        from sage.common.components.sage_embedding import get_embedding_model

                        # Try to use HF model, fallback to hash
                        try:
                            self._embedder = get_embedding_model(
                                "hf", model="BAAI/bge-small-zh-v1.5"
                            )
                        except Exception:
                            self._embedder = get_embedding_model("hash", dim=384)
                    except Exception:
                        pass
                return self._embedder

            def _compute_similarity(self, vec1: list[float], vec2: list[float]) -> float:
                """Compute cosine similarity."""
                import math

                dot = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = math.sqrt(sum(a * a for a in vec1))
                norm2 = math.sqrt(sum(b * b for b in vec2))
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                return dot / (norm1 * norm2)

            def plan(self, task):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                instruction = getattr(task, "instruction", "") or ""
                available_tools = getattr(task, "available_tools", []) or []

                if not available_tools:
                    return PlanningPrediction(steps=[], tool_sequence=[])

                embedder = self._get_embedder()

                # Decompose instruction into sub-tasks
                sub_tasks = self._decompose_instruction(instruction)

                steps = []
                tool_sequence = []
                used_tools = set()

                for i, sub_task in enumerate(sub_tasks):
                    best_tool = self._match_tool_semantic(
                        sub_task, available_tools, used_tools, embedder
                    )
                    if best_tool:
                        steps.append(
                            PlanStep(
                                step_id=i,
                                description=sub_task,
                                tool_id=best_tool,
                                confidence=0.7,
                            )
                        )
                        tool_sequence.append(best_tool)
                        used_tools.add(best_tool)

                return PlanningPrediction(steps=steps, tool_sequence=tool_sequence)

            def _decompose_instruction(self, instruction: str) -> list[str]:
                """Decompose instruction into sub-tasks."""
                delimiters = [", and ", " and ", ", then ", ", ", ". ", "; "]
                sub_tasks = [instruction]

                for delim in delimiters:
                    new_tasks = []
                    for task_item in sub_tasks:
                        parts = task_item.split(delim)
                        new_tasks.extend([p.strip() for p in parts if p.strip()])
                    sub_tasks = new_tasks

                sub_tasks = [t for t in sub_tasks if len(t) > 5]
                return sub_tasks[:10] if sub_tasks else [instruction]

            def _match_tool_semantic(
                self,
                sub_task: str,
                available_tools: list[str],
                used_tools: set[str],
                embedder,
            ) -> str | None:
                """Match sub-task to tool using semantic similarity."""
                if embedder is None:
                    # Fallback to keyword matching
                    return self._match_tool_keyword(sub_task, available_tools, used_tools)

                try:
                    # Get sub-task embedding
                    task_vec = embedder.embed(sub_task)

                    best_tool = None
                    best_score = -1.0

                    for tool in available_tools:
                        # Get tool embedding (with cache)
                        if tool not in self._tool_embeddings_cache:
                            # Create description from tool name
                            tool_desc = tool.replace("_", " ")
                            self._tool_embeddings_cache[tool] = embedder.embed(tool_desc)

                        tool_vec = self._tool_embeddings_cache[tool]
                        similarity = self._compute_similarity(task_vec, tool_vec)

                        # Penalty for already used tools
                        if tool in used_tools:
                            similarity *= 0.5

                        if similarity > best_score:
                            best_score = similarity
                            best_tool = tool

                    return best_tool
                except Exception:
                    return self._match_tool_keyword(sub_task, available_tools, used_tools)

            def _match_tool_keyword(
                self, sub_task: str, available_tools: list[str], used_tools: set[str]
            ) -> str | None:
                """Fallback keyword matching."""
                sub_task_lower = sub_task.lower()
                best_tool = None
                best_score = 0

                for tool in available_tools:
                    tool_lower = tool.lower()
                    score = 0

                    for part in tool_lower.split("_"):
                        if part in sub_task_lower and len(part) > 2:
                            score += 2

                    if tool in used_tools:
                        score *= 0.5

                    if score > best_score:
                        best_score = score
                        best_tool = tool

                if best_tool is None:
                    for tool in available_tools:
                        if tool not in used_tools:
                            return tool

                return best_tool

        return PlannerAdapter(EmbeddingBasedPlanner())

    def _create_hierarchical_planning_strategy(
        self, resources: Optional[Any] = None
    ) -> PlannerAdapter:
        """
        Create hierarchical planner for Challenge 2.

        Uses task decomposition and dependency analysis.
        """

        class HierarchicalPlanningStrategy:
            """Hierarchical planner with dependency management."""

            def plan(self, task):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                instruction = getattr(task, "instruction", "") or ""
                available_tools = getattr(task, "available_tools", []) or []

                if not available_tools:
                    return PlanningPrediction(steps=[], tool_sequence=[])

                # Decompose instruction into sub-tasks
                sub_tasks = self._decompose_instruction(instruction)

                # Map sub-tasks to tools
                steps = []
                tool_sequence = []
                used_tools = set()

                for i, sub_task in enumerate(sub_tasks):
                    best_tool = self._match_tool(sub_task, available_tools, used_tools)
                    if best_tool:
                        steps.append(
                            PlanStep(
                                step_id=i,
                                description=sub_task,
                                tool_id=best_tool,
                                confidence=0.75,
                            )
                        )
                        tool_sequence.append(best_tool)
                        used_tools.add(best_tool)

                return PlanningPrediction(steps=steps, tool_sequence=tool_sequence)

            def _decompose_instruction(self, instruction: str) -> list[str]:
                """Decompose instruction into sub-tasks."""
                # Split by common delimiters
                delimiters = [", and ", " and ", ", then ", ", ", ". ", "; "]
                sub_tasks = [instruction]

                for delim in delimiters:
                    new_tasks = []
                    for task in sub_tasks:
                        parts = task.split(delim)
                        new_tasks.extend([p.strip() for p in parts if p.strip()])
                    sub_tasks = new_tasks

                # Filter out very short tasks
                sub_tasks = [t for t in sub_tasks if len(t) > 5]

                # Limit to reasonable number
                return sub_tasks[:10] if sub_tasks else [instruction]

            def _match_tool(
                self, sub_task: str, available_tools: list[str], used_tools: set[str]
            ) -> str | None:
                """Match a sub-task to the best available tool."""
                sub_task_lower = sub_task.lower()

                # Tool type indicators
                type_keywords = {
                    "file_read": ["read", "load", "open file"],
                    "file_write": ["write", "save", "store file"],
                    "file_list": ["list files", "directory"],
                    "file_copy": ["copy", "backup"],
                    "file_delete": ["delete file", "remove file"],
                    "data_parse_json": ["parse", "json"],
                    "data_transform": ["transform", "convert data"],
                    "data_filter": ["filter", "select records"],
                    "data_aggregate": ["aggregate", "sum", "total"],
                    "data_validate": ["validate", "check schema"],
                    "http_get": ["fetch", "get data", "download", "api get"],
                    "http_post": ["post", "submit", "send data"],
                    "api_authenticate": ["authenticate", "login", "auth"],
                    "web_scrape": ["scrape", "extract from web"],
                    "db_connect": ["connect database", "db connect"],
                    "db_query": ["query", "select from", "database query"],
                    "db_insert": ["insert", "add record"],
                    "db_update": ["update record", "modify"],
                    "db_delete": ["delete record"],
                    "email_send": ["email", "send mail"],
                    "notification_send": ["notify", "notification"],
                    "slack_post": ["slack", "post message"],
                    "text_analyze": ["analyze text", "text analysis"],
                    "sentiment_analyze": ["sentiment"],
                    "stats_compute": ["statistics", "compute stats"],
                    "math_calculate": ["calculate", "math"],
                    "format_json": ["format json", "to json"],
                    "format_csv": ["csv", "format csv"],
                    "format_html": ["html", "format html", "report"],
                    "cache_get": ["get cache", "retrieve cache"],
                    "cache_set": ["cache", "set cache", "store cache"],
                    "log_write": ["log", "write log"],
                    "metrics_record": ["metrics", "record metric"],
                    "image_resize": ["resize", "thumbnail"],
                    "image_convert": ["convert image", "png", "jpg"],
                    "schedule_task": ["schedule"],
                    "get_calendar": ["calendar", "events"],
                    "code_lint": ["lint"],
                    "code_format": ["format code"],
                    "code_execute": ["execute", "run code"],
                    "search_web": ["search web", "web search"],
                    "search_documents": ["search document"],
                    "search_database": ["search database"],
                    "convert_units": ["convert units"],
                }

                best_tool = None
                best_score = 0

                for tool in available_tools:
                    if tool in used_tools:
                        # Prefer unused tools but allow reuse with penalty
                        penalty = 0.5
                    else:
                        penalty = 1.0

                    score = 0
                    tool_lower = tool.lower()

                    # Check against type keywords
                    if tool in type_keywords:
                        for kw in type_keywords[tool]:
                            if kw in sub_task_lower:
                                score += 3 * penalty

                    # Check tool name parts
                    for part in tool_lower.split("_"):
                        if part in sub_task_lower and len(part) > 2:
                            score += 2 * penalty

                    if score > best_score:
                        best_score = score
                        best_tool = tool

                # Fallback: pick first unused tool
                if best_tool is None:
                    for tool in available_tools:
                        if tool not in used_tools:
                            return tool

                return best_tool

        return PlannerAdapter(HierarchicalPlanningStrategy())

    def _create_llm_planning_strategy(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """
        Create LLM-based planner using IntelligentLLMClient.

        Uses real LLM for plan generation with semantic understanding.
        """

        class LLMPlanningStrategy:
            """LLM-based planner using IntelligentLLMClient."""

            def __init__(self, fallback_planner):
                self._fallback = fallback_planner
                self._llm_client = None
                self._client_initialized = False

            def _get_llm_client(self):
                """Lazy initialization of LLM client with local-first strategy.

                Priority:
                1. Embedded VLLMService (内嵌 vLLM，无需启动服务) - highest
                2. Local vLLM API service (localhost:8001 or 8000) - if already running
                3. Cloud API via SAGE_CHAT_* environment variables - fallback
                """
                if not self._client_initialized:
                    self._client_initialized = True
                    import os

                    # Step 1: Try embedded VLLMService (内嵌模式，无需单独启动服务)
                    try:
                        from sage.common.components.sage_llm import VLLMService

                        # Use a lightweight model for benchmark
                        model_id = os.getenv(
                            "SAGE_BENCHMARK_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"
                        )
                        self._vllm_service = VLLMService(
                            {
                                "model_id": model_id,
                                "auto_download": True,
                                "sampling": {"temperature": 0.2, "max_tokens": 1024},
                            }
                        )
                        self._vllm_service.setup()
                        self._use_embedded_vllm = True
                        print(f"✅ 使用内嵌 VLLMService: {model_id} (无需启动外部服务)")
                        return self  # Return self to use embedded mode
                    except Exception:
                        self._use_embedded_vllm = False
                        # VLLMService not available, try other options
                        pass

                    from sage.common.components.sage_llm.client import IntelligentLLMClient

                    # Step 2: Try local vLLM API service (如果已经在运行)
                    local_endpoints = [
                        ("http://localhost:8001/v1", 8001),
                        ("http://localhost:8000/v1", 8000),
                    ]

                    for endpoint, port in local_endpoints:
                        detected_model = IntelligentLLMClient._probe_vllm_service(
                            endpoint, timeout=1.0
                        )
                        if detected_model:
                            try:
                                self._llm_client = IntelligentLLMClient(
                                    model_name=detected_model,
                                    base_url=endpoint,
                                    api_key=os.getenv("VLLM_API_KEY", ""),
                                )
                                print(f"✅ 使用本地 vLLM API: {detected_model} @ port {port}")
                                return self._llm_client
                            except Exception:
                                pass

                    # Step 3: Fall back to cloud API
                    api_key = (
                        os.getenv("SAGE_CHAT_API_KEY")
                        or os.getenv("ALIBABA_API_KEY")
                        or os.getenv("OPENAI_API_KEY")
                    )

                    # Skip placeholder values
                    if api_key and "your_" in api_key.lower():
                        api_key = None

                    if api_key:
                        try:
                            self._llm_client = IntelligentLLMClient(
                                model_name=os.getenv("SAGE_CHAT_MODEL", "qwen-turbo-2025-02-11"),
                                base_url=os.getenv(
                                    "SAGE_CHAT_BASE_URL",
                                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                                ),
                                api_key=api_key,
                            )
                            print("☁️  本地 vLLM 不可用，使用云端 API")
                        except Exception:
                            pass
                    else:
                        print("⚠️  无可用 LLM 服务：本地 vLLM 未运行，云端 API Key 未配置")
                        print("   启动本地服务: sage studio start")
                        print("   或配置云端: export SAGE_CHAT_API_KEY=your_key")

                return self._llm_client

            def _generate_with_embedded_vllm(self, prompt: str) -> str:
                """Generate text using embedded VLLMService."""
                if not hasattr(self, "_vllm_service") or self._vllm_service is None:
                    return ""
                try:
                    results = self._vllm_service.generate(prompt)
                    if results and results[0].get("generations"):
                        return results[0]["generations"][0].get("text", "")
                except Exception:
                    pass
                return ""

            def plan(self, task):
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                instruction = getattr(task, "instruction", "") or ""
                available_tools = getattr(task, "available_tools", []) or []

                if not available_tools:
                    return PlanningPrediction(steps=[], tool_sequence=[])

                # Initialize LLM client (this also sets up embedded vLLM if available)
                self._get_llm_client()

                # Build prompt for plan generation
                tools_desc = ", ".join(available_tools[:20])  # Limit for prompt
                prompt = f"""Generate a step-by-step plan to accomplish this task.

Task: {instruction}

Available tools: {tools_desc}

Return a JSON array of steps, each with:
- "tool_id": the tool to use (must be from available tools)
- "description": brief description of what this step does

Return ONLY the JSON array, no explanation. Example:
[{{"tool_id": "file_read", "description": "Read config file"}}]"""

                response = None

                # Try embedded VLLMService first
                if getattr(self, "_use_embedded_vllm", False):
                    response = self._generate_with_embedded_vllm(prompt)

                # Try IntelligentLLMClient
                if not response and self._llm_client is not None:
                    try:
                        messages = [
                            {
                                "role": "system",
                                "content": "You are a task planning assistant. Return only valid JSON.",
                            },
                            {"role": "user", "content": prompt},
                        ]
                        response = self._llm_client.chat(messages, max_tokens=1024, temperature=0.2)
                    except Exception:
                        pass

                # Parse response if we got one
                if response:
                    try:
                        import json
                        import re

                        # Extract JSON from response
                        text = response if isinstance(response, str) else str(response)

                        # Try to find JSON array
                        json_match = re.search(r"\[.*\]", text, re.DOTALL)
                        if json_match:
                            plan_data = json.loads(json_match.group())

                            steps = []
                            tool_sequence = []
                            for i, step in enumerate(plan_data):
                                tool_id = step.get("tool_id", "")
                                # Validate tool is available
                                if tool_id in available_tools:
                                    steps.append(
                                        PlanStep(
                                            step_id=i,
                                            description=step.get("description", f"Step {i + 1}"),
                                            tool_id=tool_id,
                                            confidence=0.85,
                                        )
                                    )
                                    tool_sequence.append(tool_id)

                            if steps:
                                return PlanningPrediction(steps=steps, tool_sequence=tool_sequence)
                    except Exception:
                        pass

                # Fallback to hierarchical planner
                return self._fallback.plan(task)

        # Create hierarchical fallback
        hierarchical = self._create_hierarchical_planning_strategy(resources)
        return PlannerAdapter(LLMPlanningStrategy(hierarchical.planner))

    def _create_tot_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
        """
        Create Tree-of-Thoughts planner for Challenge 2.

        Uses tree search to explore multiple reasoning paths.
        Based on "Tree of Thoughts: Deliberate Problem Solving with LLMs" (Yao et al., 2023)
        """

        class ToTPlanningStrategy:
            """
            Tree-of-Thoughts planning strategy.

            Explores multiple reasoning paths via BFS/DFS tree search,
            using LLM to generate and evaluate thought candidates.
            """

            def __init__(self, fallback_planner):
                self._fallback = fallback_planner
                self._llm_client = None
                self._client_initialized = False
                # ToT configuration
                self._max_depth = 3
                self._branch_factor = 3
                self._beam_width = 5
                self._min_score = 0.3

            def _get_llm_client(self):
                """Lazy initialization of LLM client."""
                if self._client_initialized:
                    return self._llm_client

                self._client_initialized = True
                try:
                    from sage.common.components.sage_llm.client import IntelligentLLMClient

                    # Use singleton to avoid repeated model loading
                    self._llm_client = IntelligentLLMClient.get_instance(
                        cache_key="benchmark_planner", probe_timeout=1.0
                    )
                except Exception:
                    self._llm_client = None

                return self._llm_client

            def plan(self, task):
                """Generate plan using Tree-of-Thoughts search."""
                from sage.benchmark.benchmark_agent.experiments.base_experiment import (
                    PlanningPrediction,
                    PlanStep,
                )

                instruction = getattr(task, "instruction", "") or ""
                available_tools = getattr(task, "available_tools", []) or []

                if not available_tools:
                    return PlanningPrediction(steps=[], tool_sequence=[])

                # Get LLM client
                llm_client = self._get_llm_client()

                # If no LLM, fall back to hierarchical
                if llm_client is None:
                    return self._fallback.plan(task)

                try:
                    # Run ToT search
                    best_path = self._tot_search(instruction, available_tools, llm_client)

                    if best_path:
                        steps = []
                        tool_sequence = []
                        for i, (thought, tool_id) in enumerate(best_path):
                            if tool_id and tool_id in available_tools:
                                steps.append(
                                    PlanStep(
                                        step_id=i,
                                        description=thought,
                                        tool_id=tool_id,
                                        confidence=0.8,
                                    )
                                )
                                tool_sequence.append(tool_id)

                        if steps:
                            return PlanningPrediction(steps=steps, tool_sequence=tool_sequence)
                except Exception:
                    pass

                # Fallback to hierarchical planner
                return self._fallback.plan(task)

            def _tot_search(
                self, instruction: str, available_tools: list[str], llm_client
            ) -> list[tuple[str, str]]:
                """
                Perform Tree-of-Thoughts BFS search.

                Returns list of (thought, tool_id) tuples.
                """
                # Initialize queue with empty path
                queue: list[list[tuple[str, str, float]]] = [[]]  # Paths

                tools_str = ", ".join(available_tools[:15])

                for depth in range(self._max_depth):
                    next_queue: list[list[tuple[str, str, float]]] = []

                    for path in queue:
                        # Generate candidate thoughts
                        candidates = self._generate_thoughts(
                            instruction, path, available_tools, llm_client, tools_str
                        )

                        for thought, tool_id, score in candidates:
                            if score >= self._min_score:
                                new_path = path + [(thought, tool_id, score)]
                                next_queue.append(new_path)

                    if not next_queue:
                        break

                    # Keep top-k paths by average score
                    next_queue.sort(
                        key=lambda p: sum(s for _, _, s in p) / len(p) if p else 0, reverse=True
                    )
                    queue = next_queue[: self._beam_width]

                # Return best path
                if queue:
                    best_path = max(
                        queue, key=lambda p: sum(s for _, _, s in p) / len(p) if p else 0
                    )
                    return [(t, tid) for t, tid, _ in best_path]

                return []

            def _generate_thoughts(
                self,
                instruction: str,
                path: list[tuple[str, str, float]],
                available_tools: list[str],
                llm_client,
                tools_str: str,
            ) -> list[tuple[str, str, float]]:
                """Generate and evaluate candidate thoughts."""
                import json
                import re

                # Format current progress
                progress = ""
                if path:
                    progress = "\n".join(
                        f"Step {i + 1}: {t} (tool: {tid})" for i, (t, tid, _) in enumerate(path)
                    )
                else:
                    progress = "No steps taken yet."

                # Get used tools
                used_tools = {tid for _, tid, _ in path if tid}

                # Generate prompt
                prompt = f"""You are a planning assistant. Generate {self._branch_factor} different possible next steps.

Task: {instruction}
Available tools: {tools_str}
Current progress:
{progress}

Generate {self._branch_factor} different next steps. Each should use an available tool.
Avoid tools already used: {", ".join(used_tools) if used_tools else "none"}

Output as JSON array:
[{{"thought": "step description", "tool_id": "tool_name", "score": 0-10}}]

Only output JSON, nothing else."""

                try:
                    response = llm_client.chat(
                        [{"role": "user", "content": prompt}],
                        max_tokens=512,
                        temperature=0.7,
                    )

                    # Parse response
                    text = response if isinstance(response, str) else str(response)
                    json_match = re.search(r"\[.*\]", text, re.DOTALL)
                    if json_match:
                        candidates = json.loads(json_match.group())
                        result = []
                        for c in candidates:
                            thought = c.get("thought", "")
                            tool_id = c.get("tool_id", "")
                            score = c.get("score", 5) / 10.0

                            # Validate tool
                            if tool_id not in available_tools:
                                # Try to find closest match
                                for tool in available_tools:
                                    if tool not in used_tools:
                                        tool_id = tool
                                        break
                                else:
                                    continue

                            result.append((thought, tool_id, score))

                        return result[: self._branch_factor]
                except Exception:
                    pass

                # Fallback: return one thought per unused tool
                result = []
                for tool in available_tools:
                    if tool not in used_tools and len(result) < self._branch_factor:
                        result.append((f"Use {tool} for task", tool, 0.5))
                return result

        # Create hierarchical fallback
        hierarchical = self._create_hierarchical_planning_strategy(resources)
        return PlannerAdapter(ToTPlanningStrategy(hierarchical.planner))


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
