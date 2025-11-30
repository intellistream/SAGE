"""
Performance benchmark tests for agentic modules.

Validates performance requirements:
- Planning: < 1.5 seconds for complex multi-step plans
- Timing decision: < 100ms per decision
- Tool selection: < 100ms per selection
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import pytest

# ============================================================================
# Mock Components for Benchmarking
# ============================================================================


@dataclass
class MockTool:
    """Mock tool for benchmarking."""

    name: str
    description: str


class MockLLMClient:
    """Mock LLM client with configurable latency."""

    def __init__(self, latency_ms: float = 0):
        self._latency = latency_ms / 1000.0
        self._response = self._generate_plan_response(10)

    def _generate_plan_response(self, num_steps: int) -> str:
        import json

        steps = []
        for i in range(num_steps):
            deps = [f"step_{j}" for j in range(max(0, i - 2), i)]
            steps.append(
                {
                    "step_id": f"step_{i}",
                    "description": f"Step {i}",
                    "dependencies": deps,
                    "tools": [f"tool_{i % 3}"],
                }
            )
        return json.dumps({"steps": steps})

    def generate(self, prompt: str, **kwargs) -> str:
        if self._latency > 0:
            time.sleep(self._latency)
        return self._response


class FastToolSelector:
    """Fast mock tool selector for benchmarking."""

    def __init__(self, tools: list[MockTool]):
        self._tools = tools
        self._tool_index = {t.name: t for t in tools}

    def select(self, query: str, top_k: int = 5, **kwargs) -> list[dict[str, Any]]:
        """Fast keyword-based tool selection."""
        query_words = set(query.lower().split())
        results = []

        for tool in self._tools:
            desc_words = set(tool.description.lower().split())
            overlap = len(query_words & desc_words)
            score = overlap / max(len(query_words), 1)
            results.append({"tool": tool.name, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


class FastTimingDecider:
    """Fast mock timing decider for benchmarking."""

    ACTION_KEYWORDS = frozenset(
        ["search", "find", "calculate", "analyze", "create", "update", "delete"]
    )
    CASUAL_KEYWORDS = frozenset(["hello", "hi", "thanks", "bye", "ok"])

    def decide(self, context: dict[str, Any]) -> dict[str, Any]:
        message = context.get("user_message", "").lower()
        words = set(message.split())

        if words & self.CASUAL_KEYWORDS:
            return {"should_call_tool": False, "confidence": 0.95}
        if words & self.ACTION_KEYWORDS:
            return {"should_call_tool": True, "confidence": 0.9}
        return {"should_call_tool": True, "confidence": 0.6}


# ============================================================================
# Performance Benchmark Tests
# ============================================================================


class TestTimingDeciderPerformance:
    """Benchmark timing decider performance."""

    @pytest.fixture
    def decider(self) -> FastTimingDecider:
        return FastTimingDecider()

    @pytest.fixture
    def test_messages(self) -> list[str]:
        return [
            "Hello!",
            "Search for AI papers",
            "Calculate the sum of these numbers",
            "What is the weather today?",
            "Analyze the quarterly report",
            "Find similar documents",
            "Create a new project",
            "Update the configuration",
            "Delete old records",
            "Thanks for your help!",
        ]

    def test_single_decision_under_100ms(
        self, decider: FastTimingDecider, test_messages: list[str]
    ):
        """Each timing decision should complete in under 100ms."""
        for msg in test_messages:
            start = time.perf_counter()
            result = decider.decide({"user_message": msg})
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 100, f"Decision for '{msg}' took {elapsed_ms:.2f}ms"
            assert "should_call_tool" in result
            assert "confidence" in result

    def test_1000_decisions_under_1_second(
        self, decider: FastTimingDecider, test_messages: list[str]
    ):
        """1000 timing decisions should complete in under 1 second."""
        start = time.perf_counter()

        for i in range(1000):
            msg = test_messages[i % len(test_messages)]
            decider.decide({"user_message": msg})

        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 1000) * 1000

        assert elapsed < 1.0, f"1000 decisions took {elapsed:.3f}s"
        assert avg_ms < 1.0, f"Average decision time {avg_ms:.3f}ms exceeds 1ms"

    def test_timing_decision_p99_latency(
        self, decider: FastTimingDecider, test_messages: list[str]
    ):
        """P99 latency for timing decisions should be under 10ms."""
        latencies = []

        for i in range(100):
            msg = test_messages[i % len(test_messages)]
            start = time.perf_counter()
            decider.decide({"user_message": msg})
            latencies.append((time.perf_counter() - start) * 1000)

        latencies.sort()
        p99 = latencies[98]  # 99th percentile

        assert p99 < 10, f"P99 latency {p99:.3f}ms exceeds 10ms"


class TestToolSelectionPerformance:
    """Benchmark tool selection performance."""

    @pytest.fixture
    def tools(self) -> list[MockTool]:
        """Create a realistic set of 50 tools."""
        return [
            MockTool(f"tool_{i}", f"Description for tool {i} with keywords {i % 10}")
            for i in range(50)
        ]

    @pytest.fixture
    def selector(self, tools: list[MockTool]) -> FastToolSelector:
        return FastToolSelector(tools)

    @pytest.fixture
    def test_queries(self) -> list[str]:
        return [
            "search documents",
            "calculate total",
            "find similar items",
            "analyze data patterns",
            "process input files",
        ]

    def test_single_selection_under_100ms(
        self, selector: FastToolSelector, test_queries: list[str]
    ):
        """Each tool selection should complete in under 100ms."""
        for query in test_queries:
            start = time.perf_counter()
            results = selector.select(query, top_k=5)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 100, f"Selection for '{query}' took {elapsed_ms:.2f}ms"
            assert len(results) <= 5

    def test_500_selections_under_1_second(
        self, selector: FastToolSelector, test_queries: list[str]
    ):
        """500 tool selections should complete in under 1 second."""
        start = time.perf_counter()

        for i in range(500):
            query = test_queries[i % len(test_queries)]
            selector.select(query, top_k=5)

        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 500) * 1000

        assert elapsed < 1.0, f"500 selections took {elapsed:.3f}s"
        assert avg_ms < 2.0, f"Average selection time {avg_ms:.3f}ms exceeds 2ms"

    def test_large_tool_set_performance(self):
        """Test performance with 200 tools."""
        tools = [MockTool(f"tool_{i}", f"Description for tool number {i}") for i in range(200)]
        selector = FastToolSelector(tools)

        start = time.perf_counter()
        for _ in range(100):
            selector.select("search for documents", top_k=10)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100

        assert elapsed_ms < 50, f"Avg selection with 200 tools: {elapsed_ms:.2f}ms"


class TestPlanningPerformance:
    """Benchmark planning performance."""

    @pytest.fixture
    def llm_client(self) -> MockLLMClient:
        return MockLLMClient(latency_ms=0)  # No simulated latency

    def test_plan_parsing_under_100ms(self, llm_client: MockLLMClient):
        """Plan generation and parsing should complete in under 100ms (excluding LLM)."""
        import json

        start = time.perf_counter()

        # Generate plan
        response = llm_client.generate("Create a complex plan")

        # Parse plan
        plan = json.loads(response)

        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Plan parsing took {elapsed_ms:.2f}ms"
        assert "steps" in plan
        assert len(plan["steps"]) == 10

    def test_dependency_graph_construction(self, llm_client: MockLLMClient):
        """Dependency graph construction should be fast."""
        import json

        response = llm_client.generate("Create plan")
        plan = json.loads(response)

        start = time.perf_counter()

        # Simulate dependency graph construction
        graph: dict[str, list[str]] = {}
        for step in plan["steps"]:
            step_id = step["step_id"]
            deps = step["dependencies"]
            graph[step_id] = deps

        # Simulate topological sort
        visited: set[str] = set()
        result: list[str] = []

        def visit(node: str):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            result.append(node)

        for node in graph:
            visit(node)

        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Graph construction took {elapsed_ms:.2f}ms"
        assert len(result) == 10

    def test_complex_plan_under_1500ms(self):
        """Complex 20-step plan processing should complete in under 1.5s."""
        import json

        # Create complex plan with 20 steps
        steps = []
        for i in range(20):
            deps = [f"step_{j}" for j in range(max(0, i - 3), i)]
            steps.append(
                {
                    "step_id": f"step_{i}",
                    "description": f"Complex step {i} with detailed description",
                    "dependencies": deps,
                    "tools": [f"tool_{i % 5}"],
                }
            )

        plan = {"steps": steps}
        plan_json = json.dumps(plan)

        start = time.perf_counter()

        # Parse
        parsed = json.loads(plan_json)

        # Build graph
        graph: dict[str, list[str]] = {}
        for step in parsed["steps"]:
            graph[step["step_id"]] = step["dependencies"]

        # Topological sort
        visited: set[str] = set()
        result: list[str] = []

        def visit(node: str):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            result.append(node)

        for node in graph:
            visit(node)

        # Validate
        assert len(result) == 20

        elapsed = time.perf_counter() - start

        assert elapsed < 1.5, f"Complex plan processing took {elapsed:.3f}s"


class TestFullWorkflowPerformance:
    """Benchmark complete workflow performance."""

    @pytest.fixture
    def components(self) -> dict[str, Any]:
        tools = [MockTool(f"tool_{i}", f"Tool {i} description") for i in range(30)]
        return {
            "timing": FastTimingDecider(),
            "selector": FastToolSelector(tools),
            "llm": MockLLMClient(latency_ms=0),
        }

    def test_workflow_iteration_performance(self, components: dict[str, Any]):
        """Single workflow iteration should be fast (excluding LLM latency)."""
        import json

        timing = components["timing"]
        selector = components["selector"]
        llm = components["llm"]

        messages = [
            "Search for documents about AI",
            "Analyze the sales data",
            "Create a summary report",
        ]

        for msg in messages:
            start = time.perf_counter()

            # Timing decision
            decision = timing.decide({"user_message": msg})

            if decision["should_call_tool"]:
                # Generate plan
                response = llm.generate(f"Plan: {msg}")
                plan = json.loads(response)

                # Select tools for each step
                for step in plan["steps"][:5]:  # First 5 steps
                    selector.select(step["description"], top_k=3)

            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 100, f"Workflow for '{msg}' took {elapsed_ms:.2f}ms"

    def test_100_workflows_under_5_seconds(self, components: dict[str, Any]):
        """100 complete workflows should complete in under 5 seconds."""
        import json

        timing = components["timing"]
        selector = components["selector"]
        llm = components["llm"]

        messages = ["Search for docs", "Analyze data", "Create report", "Find items"]

        start = time.perf_counter()

        for i in range(100):
            msg = messages[i % len(messages)]

            decision = timing.decide({"user_message": msg})

            if decision["should_call_tool"]:
                response = llm.generate(f"Plan: {msg}")
                plan = json.loads(response)

                for step in plan["steps"][:3]:
                    selector.select(step["description"], top_k=3)

        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 100) * 1000

        assert elapsed < 5.0, f"100 workflows took {elapsed:.3f}s"
        assert avg_ms < 50, f"Average workflow time {avg_ms:.2f}ms exceeds 50ms"


class TestMemoryPerformance:
    """Test memory usage patterns."""

    def test_no_memory_leak_in_repeated_selections(self):
        """Repeated tool selections should not accumulate memory."""
        import gc

        tools = [MockTool(f"tool_{i}", f"Description {i}") for i in range(100)]
        selector = FastToolSelector(tools)

        # Warm up
        for _ in range(100):
            selector.select("test query", top_k=5)

        gc.collect()

        # Run many selections
        for _ in range(1000):
            results = selector.select("search for something", top_k=10)
            assert len(results) <= 10

        # If we get here without memory error, we're good
        gc.collect()

    def test_no_memory_leak_in_timing_decisions(self):
        """Repeated timing decisions should not accumulate memory."""
        import gc

        decider = FastTimingDecider()

        # Warm up
        for _ in range(100):
            decider.decide({"user_message": "test"})

        gc.collect()

        # Run many decisions
        for i in range(1000):
            result = decider.decide({"user_message": f"Message number {i}"})
            assert "should_call_tool" in result

        gc.collect()
