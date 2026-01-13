"""
Tests for HierarchicalPlanner module.
"""

from sage_libs.sage_agentic.agents.planning import (
    HierarchicalPlanner,
    PlannerConfig,
    PlanRequest,
    PlanResult,
    ToolMetadata,
)


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, response=None):
        self.response = response or self._default_response()
        self.call_count = 0

    def _default_response(self):
        return """[
            {
                "id": 1,
                "action": "Search for information",
                "tool_id": "search",
                "inputs": {"query": "test"},
                "depends_on": [],
                "expected_outputs": ["results"],
                "description": "Search step"
            },
            {
                "id": 2,
                "action": "Process results",
                "tool_id": "processor",
                "inputs": {"data": "results"},
                "depends_on": [1],
                "expected_outputs": ["processed"],
                "description": "Process step"
            }
        ]"""

    def chat(self, messages, temperature=0.7, max_tokens=2000):
        self.call_count += 1
        return self.response


class MockToolSelector:
    """Mock tool selector for testing."""

    def select(self, query, top_k=1):
        # Return mock predictions
        class MockPrediction:
            def __init__(self, tool_id):
                self.tool_id = tool_id
                self.score = 0.9

        return [MockPrediction("mock_tool")]


class TestHierarchicalPlanner:
    """Test hierarchical planner functionality."""

    def test_create_planner(self):
        """Test creating hierarchical planner."""
        config = PlannerConfig()
        llm_client = MockLLMClient()

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        assert planner.name == "hierarchical_planner"
        assert planner.llm_client is not None

    def test_from_config(self):
        """Test creating planner from config."""
        config = PlannerConfig(min_steps=3, max_steps=7)
        llm_client = MockLLMClient()

        planner = HierarchicalPlanner.from_config(config=config, llm_client=llm_client)

        assert planner.config.min_steps == 3
        assert planner.config.max_steps == 7

    def test_plan_basic(self):
        """Test basic plan generation."""
        config = PlannerConfig(min_steps=2)  # Mock returns 2 steps
        llm_client = MockLLMClient()

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        request = PlanRequest(
            goal="Test goal",
            tools=[
                ToolMetadata(
                    tool_id="search",
                    name="Search",
                    description="Search tool",
                    category="search",
                    capabilities=["search"],
                )
            ],
            max_steps=10,
        )

        result = planner.plan(request)

        assert isinstance(result, PlanResult)
        assert result.success is True
        assert len(result.steps) >= 2
        assert llm_client.call_count == 1

    def test_plan_with_malformed_llm_output(self):
        """Test plan generation with malformed LLM output."""
        config = PlannerConfig(enable_repair=True)
        llm_client = MockLLMClient(response="This is not valid JSON at all!")

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        request = PlanRequest(goal="Test goal", tools=[], max_steps=10)

        result = planner.plan(request)

        # Should use fallback plan
        assert isinstance(result, PlanResult)
        assert result.success is True
        assert len(result.steps) > 0  # Fallback plan

    def test_plan_without_llm_client_fails(self):
        """Test planning without LLM client fails gracefully."""
        config = PlannerConfig()

        planner = HierarchicalPlanner(config=config, llm_client=None)

        request = PlanRequest(goal="Test goal", tools=[], max_steps=10)

        result = planner.plan(request)

        assert isinstance(result, PlanResult)
        assert result.success is False
        assert "LLM client not configured" in result.error_message

    def test_plan_with_tool_selector(self):
        """Test plan generation with tool selector."""
        config = PlannerConfig()

        # Mock response without tool_id
        response = """[
            {
                "id": 1,
                "action": "Do something",
                "inputs": {},
                "depends_on": [],
                "expected_outputs": [],
                "description": "Test"
            }
        ]"""

        llm_client = MockLLMClient(response=response)
        tool_selector = MockToolSelector()

        planner = HierarchicalPlanner(
            config=config, llm_client=llm_client, tool_selector=tool_selector
        )

        request = PlanRequest(
            goal="Test goal",
            tools=[
                ToolMetadata(
                    tool_id="tool1",
                    name="Tool 1",
                    description="Test tool",
                    category="test",
                    capabilities=[],
                )
            ],
            max_steps=10,
        )

        result = planner.plan(request)

        assert result.success is True
        # Tool selector should have assigned a tool
        if len(result.steps) > 0:
            # At least one step should have a tool assigned
            assert any(step.tool_id for step in result.steps)

    def test_plan_with_retry(self):
        """Test plan generation with retry on failure."""
        config = PlannerConfig(max_retries=2, min_steps=2)  # Mock returns 2 steps

        # First call fails, second succeeds
        call_count = [0]

        class RetryMockClient:
            def chat(self, messages, temperature=0.7, max_tokens=2000):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise RuntimeError("First call failed")
                return MockLLMClient()._default_response()

        llm_client = RetryMockClient()

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        request = PlanRequest(goal="Test goal", tools=[], max_steps=10)

        result = planner.plan(request)

        # Should succeed on second attempt
        assert call_count[0] == 2
        assert result.success is True

    def test_plan_max_retries_exceeded(self):
        """Test plan generation fails after max retries."""
        config = PlannerConfig(max_retries=1)

        class FailingClient:
            def chat(self, messages, temperature=0.7, max_tokens=2000):
                raise RuntimeError("Always fails")

        llm_client = FailingClient()

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        request = PlanRequest(goal="Test goal", tools=[], max_steps=10)

        result = planner.plan(request)

        assert result.success is False
        assert "failed after" in result.error_message.lower()

    def test_get_stats(self):
        """Test getting planner statistics."""
        config = PlannerConfig()
        llm_client = MockLLMClient()

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        # Generate a few plans
        request = PlanRequest(goal="Test", tools=[], max_steps=10)

        planner.plan(request)
        planner.plan(request)

        stats = planner.get_stats()

        assert stats["total_plans"] == 2
        assert stats["failed_plans"] >= 0
        assert "success_rate" in stats
        assert "repair_rate" in stats

    def test_dependency_validation(self):
        """Test dependency validation in planning."""
        config = PlannerConfig(enable_dependency_check=True)

        # Response with cycle
        response = """[
            {
                "id": 1,
                "action": "Step 1",
                "depends_on": [2],
                "expected_outputs": []
            },
            {
                "id": 2,
                "action": "Step 2",
                "depends_on": [1],
                "expected_outputs": []
            }
        ]"""

        llm_client = MockLLMClient(response=response)

        planner = HierarchicalPlanner(config=config, llm_client=llm_client)

        request = PlanRequest(goal="Test", tools=[], max_steps=10)
        result = planner.plan(request)

        # Should detect and repair cycle
        assert result.success is True

        # Verify no cycles in final plan
        from sage_libs.sage_agentic.agents.planning import DependencyGraph

        if len(result.steps) > 0:
            graph = DependencyGraph(result.steps)
            assert not graph.has_cycle()
