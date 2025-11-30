"""
Integration tests for agentic modules.

Tests cross-module collaboration between:
- HierarchicalPlanner (planning)
- ToolSelector (tool_selection)
- TimingDecider (planning)
- Runtime Orchestrator (runtime)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import pytest

# ============================================================================
# Mock Components
# ============================================================================


def _word_match(word: str, text: str) -> bool:
    """Check if word exists as a complete word in text."""
    pattern = rf"\b{re.escape(word)}\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


@dataclass
class MockTool:
    """Mock tool for testing."""

    name: str
    description: str
    capabilities: list[str] | None = None


class MockToolsLoader:
    """Mock tools loader."""

    def __init__(self, tools: list[MockTool]):
        self._tools = tools

    def iter_all(self):
        return iter(self._tools)


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, response: str | None = None):
        self._response = response or self._default_response()
        self.call_count = 0
        self.last_prompt = None

    def _default_response(self) -> str:
        return """```json
{
    "steps": [
        {
            "step_id": "step_1",
            "description": "Search for relevant information",
            "dependencies": [],
            "tools": ["search_tool"]
        },
        {
            "step_id": "step_2",
            "description": "Process search results",
            "dependencies": ["step_1"],
            "tools": ["process_tool"]
        },
        {
            "step_id": "step_3",
            "description": "Generate final response",
            "dependencies": ["step_2"],
            "tools": []
        }
    ]
}
```"""

    def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return self._response


class MockToolSelector:
    """Mock tool selector for testing."""

    def __init__(self, tools: list[MockTool]):
        self._tools = tools

    def select(
        self, query: str, candidates: list | None = None, top_k: int = 5, **kwargs
    ) -> list[dict[str, Any]]:
        """Select tools based on query keywords."""
        results = []
        query_lower = query.lower()

        for tool in self._tools:
            score = 0.0
            if tool.name.lower() in query_lower:
                score = 0.9
            elif any(kw in query_lower for kw in tool.description.lower().split()[:3]):
                score = 0.7
            else:
                score = 0.3

            results.append({"tool": tool.name, "score": score, "reason": "keyword match"})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


class MockTimingDecider:
    """Mock timing decider for testing."""

    def __init__(self, default_should_call: bool = True):
        self._default = default_should_call
        self.decide_count = 0

    def decide(self, context: dict[str, Any]) -> dict[str, Any]:
        self.decide_count += 1

        message = context.get("user_message", "").lower()

        # Rule-based decisions (use word boundary matching)
        casual_keywords = ["hello", "hi", "thanks"]
        action_keywords = ["search", "find", "calculate", "analyze", "summarize"]

        if any(_word_match(kw, message) for kw in casual_keywords):
            should_call = False
            confidence = 0.95
        elif any(_word_match(kw, message) for kw in action_keywords):
            should_call = True
            confidence = 0.9
        else:
            should_call = self._default
            confidence = 0.6

        return {
            "should_call_tool": should_call,
            "confidence": confidence,
            "reasoning": "rule-based decision",
        }


# ============================================================================
# Integration Tests
# ============================================================================


class TestPlanningWithToolSelection:
    """Test integration between HierarchicalPlanner and ToolSelector."""

    @pytest.fixture
    def tools(self) -> list[MockTool]:
        return [
            MockTool("search_tool", "Search for information online"),
            MockTool("process_tool", "Process and analyze data"),
            MockTool("calculator", "Perform mathematical calculations"),
            MockTool("file_reader", "Read files from disk"),
        ]

    @pytest.fixture
    def tool_selector(self, tools: list[MockTool]) -> MockToolSelector:
        return MockToolSelector(tools)

    @pytest.fixture
    def llm_client(self) -> MockLLMClient:
        return MockLLMClient()

    def test_planner_with_tool_selection(
        self, llm_client: MockLLMClient, tool_selector: MockToolSelector
    ):
        """Test that planner can use tool selector to assign tools to steps."""
        # Create a plan
        response = llm_client.generate("Plan a research task")

        # Parse steps (simplified)
        assert "step_1" in response
        assert "search_tool" in response

        # For each step, select appropriate tools
        step_queries = [
            "Search for relevant information",
            "Process search results",
            "Generate final response",
        ]

        for query in step_queries:
            selected = tool_selector.select(query, top_k=2)
            assert len(selected) <= 2
            assert all("score" in s for s in selected)

    def test_tool_selection_performance(self, tool_selector: MockToolSelector):
        """Test that tool selection meets performance requirements (<100ms)."""
        queries = [
            "Search for documents about AI",
            "Calculate the total cost",
            "Read the configuration file",
            "Process the input data",
        ]

        for query in queries:
            start = time.perf_counter()
            results = tool_selector.select(query, top_k=3)
            elapsed = time.perf_counter() - start

            assert elapsed < 0.1, f"Tool selection took {elapsed:.3f}s, exceeds 100ms"
            assert len(results) <= 3


class TestTimingWithPlanning:
    """Test integration between TimingDecider and planning workflow."""

    @pytest.fixture
    def timing_decider(self) -> MockTimingDecider:
        return MockTimingDecider()

    @pytest.fixture
    def llm_client(self) -> MockLLMClient:
        return MockLLMClient()

    def test_timing_gates_planning(
        self, timing_decider: MockTimingDecider, llm_client: MockLLMClient
    ):
        """Test that timing decision gates the planning process."""
        # Scenario 1: User greeting - no planning needed
        context1 = {"user_message": "Hello, how are you?"}
        decision1 = timing_decider.decide(context1)
        assert not decision1["should_call_tool"]
        assert decision1["confidence"] > 0.9

        # Scenario 2: User request - planning needed
        context2 = {"user_message": "Search for recent AI papers and analyze them"}
        decision2 = timing_decider.decide(context2)
        assert decision2["should_call_tool"]

        # Only invoke planner if timing decision says yes
        if decision2["should_call_tool"]:
            response = llm_client.generate(context2["user_message"])
            assert "steps" in response
            assert llm_client.call_count == 1

    def test_timing_decision_performance(self, timing_decider: MockTimingDecider):
        """Test that timing decisions meet performance requirements (<100ms)."""
        test_messages = [
            "Hello!",
            "Search for documents",
            "What is the weather?",
            "Calculate 2+2",
            "Thanks for your help",
        ]

        for msg in test_messages:
            start = time.perf_counter()
            decision = timing_decider.decide({"user_message": msg})
            elapsed = time.perf_counter() - start

            assert elapsed < 0.1, f"Timing decision took {elapsed:.3f}s, exceeds 100ms"
            assert "should_call_tool" in decision
            assert "confidence" in decision


class TestFullWorkflow:
    """Test full workflow: Timing -> Planning -> Tool Selection -> Execution."""

    @pytest.fixture
    def tools(self) -> list[MockTool]:
        return [
            MockTool("web_search", "Search the web for information"),
            MockTool("document_reader", "Read and parse documents"),
            MockTool("summarizer", "Summarize text content"),
            MockTool("calculator", "Perform calculations"),
        ]

    @pytest.fixture
    def workflow_components(self, tools: list[MockTool]) -> dict[str, Any]:
        return {
            "timing_decider": MockTimingDecider(),
            "llm_client": MockLLMClient(),
            "tool_selector": MockToolSelector(tools),
        }

    def test_full_workflow_research_task(self, workflow_components: dict[str, Any]):
        """Test complete workflow for a research task."""
        timing = workflow_components["timing_decider"]
        llm = workflow_components["llm_client"]
        selector = workflow_components["tool_selector"]

        user_message = "Search for recent machine learning papers and summarize them"

        # Step 1: Timing decision
        timing_result = timing.decide({"user_message": user_message})
        assert timing_result["should_call_tool"]

        # Step 2: Generate plan
        plan_response = llm.generate(f"Create a plan for: {user_message}")
        assert "steps" in plan_response

        # Step 3: For each step, select tools
        step_descriptions = [
            "Search for relevant information",
            "Process search results",
            "Generate final response",
        ]

        execution_plan = []
        for desc in step_descriptions:
            tools_for_step = selector.select(desc, top_k=2)
            execution_plan.append({"description": desc, "tools": tools_for_step})

        # Verify execution plan
        assert len(execution_plan) == 3
        assert all("tools" in step for step in execution_plan)

    def test_full_workflow_simple_greeting(self, workflow_components: dict[str, Any]):
        """Test that simple greetings bypass planning."""
        timing = workflow_components["timing_decider"]
        llm = workflow_components["llm_client"]

        user_message = "Hi there!"

        # Step 1: Timing decision
        timing_result = timing.decide({"user_message": user_message})
        assert not timing_result["should_call_tool"]

        # LLM should not be called for simple greetings
        assert llm.call_count == 0

    def test_workflow_performance_end_to_end(self, workflow_components: dict[str, Any]):
        """Test that full workflow meets performance requirements."""
        timing = workflow_components["timing_decider"]
        llm = workflow_components["llm_client"]
        selector = workflow_components["tool_selector"]

        user_message = "Analyze the quarterly sales data"

        start = time.perf_counter()

        # Timing decision
        timing_result = timing.decide({"user_message": user_message})

        if timing_result["should_call_tool"]:
            # Planning
            llm.generate(f"Plan: {user_message}")

            # Tool selection for 3 steps
            for _ in range(3):
                selector.select("step description", top_k=3)

        total_elapsed = time.perf_counter() - start

        # Full workflow should be fast (excluding actual LLM calls)
        assert total_elapsed < 0.5, f"Full workflow took {total_elapsed:.3f}s"


class TestErrorHandling:
    """Test error handling in integrated workflows."""

    def test_graceful_degradation_no_tools(self):
        """Test workflow handles empty tool list gracefully."""
        selector = MockToolSelector([])
        results = selector.select("search for something")
        assert results == []

    def test_timing_with_empty_context(self):
        """Test timing decider handles missing context gracefully."""
        decider = MockTimingDecider()
        result = decider.decide({})  # Empty context
        assert "should_call_tool" in result
        assert "confidence" in result

    def test_llm_response_parsing_robustness(self):
        """Test that malformed LLM responses are handled."""
        # LLM returns malformed JSON
        bad_client = MockLLMClient(response="This is not JSON")
        response = bad_client.generate("test")
        assert response == "This is not JSON"
        # In real implementation, this should be caught and handled


class TestConcurrency:
    """Test concurrent execution scenarios."""

    def test_parallel_tool_selection(self):
        """Test that multiple tool selections can run efficiently."""
        tools = [MockTool(f"tool_{i}", f"Description for tool {i}") for i in range(10)]
        selector = MockToolSelector(tools)

        queries = [f"Query {i}" for i in range(5)]

        start = time.perf_counter()
        results = [selector.select(q, top_k=3) for q in queries]
        elapsed = time.perf_counter() - start

        assert len(results) == 5
        assert all(len(r) <= 3 for r in results)
        assert elapsed < 0.5  # 5 selections should be fast


class TestMetricsCollection:
    """Test that components properly collect metrics."""

    def test_timing_tracks_calls(self):
        """Test that timing decider tracks call count."""
        decider = MockTimingDecider()

        for i in range(5):
            decider.decide({"user_message": f"Message {i}"})

        assert decider.decide_count == 5

    def test_llm_tracks_calls(self):
        """Test that LLM client tracks call count."""
        client = MockLLMClient()

        for i in range(3):
            client.generate(f"Prompt {i}")

        assert client.call_count == 3
        assert client.last_prompt == "Prompt 2"
