"""
Tests for Tree-of-Thoughts (ToT) Planner module.
"""

from sage.libs.agentic.agents.planning import (
    PlanRequest,
    SearchMethod,
    ThoughtNode,
    ToolMetadata,
    ToTConfig,
    TreeOfThoughtsPlanner,
)


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    def chat(self, messages, temperature=0.7, max_tokens=512):
        self.call_count += 1
        if self.responses:
            return self.responses[min(self.call_count - 1, len(self.responses) - 1)]
        return self._default_response()

    def _default_response(self):
        return """[
            {"thought": "Search for information", "tool_id": "search", "reasoning": "Need data first"},
            {"thought": "Process the results", "tool_id": "processor", "reasoning": "Transform data"},
            {"thought": "Save output", "tool_id": "file_write", "reasoning": "Store results"}
        ]"""


class TestToTConfig:
    """Test ToTConfig configuration class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ToTConfig()

        assert config.max_depth == 3
        assert config.branch_factor == 3
        assert config.search_method == SearchMethod.BFS
        assert config.beam_width == 5
        assert config.min_thought_score == 0.3
        assert config.early_stop_score == 0.9

    def test_custom_config(self):
        """Test custom configuration."""
        config = ToTConfig(
            max_depth=5,
            branch_factor=4,
            search_method=SearchMethod.DFS,
            beam_width=10,
            min_thought_score=0.5,
        )

        assert config.max_depth == 5
        assert config.branch_factor == 4
        assert config.search_method == SearchMethod.DFS
        assert config.beam_width == 10
        assert config.min_thought_score == 0.5

    def test_config_inherits_from_planner_config(self):
        """Test that ToTConfig inherits from PlannerConfig."""
        config = ToTConfig(min_steps=3, max_steps=8)

        assert config.min_steps == 3
        assert config.max_steps == 8


class TestThoughtNode:
    """Test ThoughtNode dataclass."""

    def test_create_root_node(self):
        """Test creating a root node."""
        root = ThoughtNode(thought="", score=1.0)

        assert root.thought == ""
        assert root.score == 1.0
        assert root.parent is None
        assert root.depth == 0
        assert root.children == []

    def test_create_child_node(self):
        """Test creating child nodes."""
        root = ThoughtNode(thought="", score=1.0)
        child = ThoughtNode(
            thought="Search for data",
            score=0.8,
            parent=root,
            tool_id="search",
        )

        assert child.thought == "Search for data"
        assert child.score == 0.8
        assert child.parent is root
        assert child.depth == 1
        assert child.tool_id == "search"

    def test_get_path(self):
        """Test getting path from root to node."""
        root = ThoughtNode(thought="", score=1.0)
        child1 = ThoughtNode(thought="Step 1", score=0.8, parent=root)
        child2 = ThoughtNode(thought="Step 2", score=0.7, parent=child1)

        root.children.append(child1)
        child1.children.append(child2)

        path = child2.get_path()

        assert len(path) == 3
        assert path[0] is root
        assert path[1] is child1
        assert path[2] is child2

    def test_get_path_thoughts(self):
        """Test getting thoughts along path."""
        root = ThoughtNode(thought="", score=1.0)
        child1 = ThoughtNode(thought="Step 1", score=0.8, parent=root)
        child2 = ThoughtNode(thought="Step 2", score=0.7, parent=child1)

        thoughts = child2.get_path_thoughts()

        # Should skip empty root thought, returning only non-empty thoughts
        assert len(thoughts) == 2
        assert thoughts[0] == "Step 1"
        assert thoughts[1] == "Step 2"

    def test_get_cumulative_score(self):
        """Test cumulative score calculation."""
        root = ThoughtNode(thought="", score=1.0)
        child1 = ThoughtNode(thought="Step 1", score=0.8, parent=root)
        child2 = ThoughtNode(thought="Step 2", score=0.6, parent=child1)

        avg_score = child2.get_cumulative_score()

        # (1.0 + 0.8 + 0.6) / 3 = 0.8
        assert abs(avg_score - 0.8) < 0.001


class TestTreeOfThoughtsPlanner:
    """Test TreeOfThoughtsPlanner class."""

    def test_create_planner(self):
        """Test creating ToT planner."""
        config = ToTConfig()
        planner = TreeOfThoughtsPlanner(config=config)

        assert planner.name == "tree_of_thoughts_planner"
        assert planner.config.max_depth == 3
        assert planner.llm_client is None

    def test_create_planner_with_llm(self):
        """Test creating planner with LLM client."""
        config = ToTConfig()
        llm_client = MockLLMClient()

        planner = TreeOfThoughtsPlanner(config=config, llm_client=llm_client)

        assert planner.llm_client is llm_client

    def test_from_config(self):
        """Test creating planner from config."""
        config = ToTConfig(max_depth=5, search_method=SearchMethod.DFS)
        llm_client = MockLLMClient()

        planner = TreeOfThoughtsPlanner.from_config(config=config, llm_client=llm_client)

        assert planner.config.max_depth == 5
        assert planner.config.search_method == SearchMethod.DFS

    def test_plan_without_llm_uses_fallback(self):
        """Test planning without LLM uses heuristic fallback."""
        config = ToTConfig(max_depth=2, branch_factor=2)
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        tools = [
            ToolMetadata(
                tool_id="search",
                name="search",
                description="Search for information",
                category="retrieval",
            ),
            ToolMetadata(
                tool_id="process",
                name="process",
                description="Process data",
                category="transform",
            ),
        ]

        request = PlanRequest(
            goal="Find and process data",
            tools=tools,
            min_steps=2,
            max_steps=5,
        )

        result = planner.plan(request)

        assert result is not None
        assert result.success
        assert len(result.steps) >= request.min_steps

    def test_plan_with_mock_llm(self):
        """Test planning with mock LLM client."""
        config = ToTConfig(max_depth=2, branch_factor=2)

        # Mock responses for thought generation and evaluation
        llm_client = MockLLMClient(
            responses=[
                # Thought generation response
                """[
                    {"thought": "Search for data", "tool_id": "search", "reasoning": "Need data"},
                    {"thought": "Process results", "tool_id": "process", "reasoning": "Transform"}
                ]""",
                # Evaluation response
                '{"score": 8, "reasoning": "Good step"}',
                '{"score": 7, "reasoning": "Reasonable step"}',
                # More thought generation
                """[
                    {"thought": "Save output", "tool_id": "file_write", "reasoning": "Store"}
                ]""",
            ]
        )

        planner = TreeOfThoughtsPlanner(config=config, llm_client=llm_client)

        tools = [
            ToolMetadata(
                tool_id="search",
                name="search",
                description="Search for information",
                category="retrieval",
            ),
            ToolMetadata(
                tool_id="process",
                name="process",
                description="Process data",
                category="transform",
            ),
            ToolMetadata(
                tool_id="file_write",
                name="file_write",
                description="Write to file",
                category="io",
            ),
        ]

        request = PlanRequest(
            goal="Find, process, and save data",
            tools=tools,
            min_steps=2,
            max_steps=5,
        )

        result = planner.plan(request)

        assert result is not None
        assert llm_client.call_count > 0  # LLM was called

    def test_plan_result_has_metadata(self):
        """Test that plan result includes ToT metadata."""
        config = ToTConfig(max_depth=2, search_method=SearchMethod.BFS)
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        tools = [
            ToolMetadata(
                tool_id="search",
                name="search",
                description="Search",
                category="retrieval",
            ),
        ]

        request = PlanRequest(goal="Test", tools=tools, min_steps=1, max_steps=3)

        result = planner.plan(request)

        assert "search_method" in result.metadata
        assert result.metadata["search_method"] == "bfs"

    def test_bfs_search_method(self):
        """Test BFS search produces valid results."""
        config = ToTConfig(max_depth=2, search_method=SearchMethod.BFS, beam_width=3)
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        tools = [
            ToolMetadata(
                tool_id=f"tool_{i}",
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="test",
            )
            for i in range(5)
        ]

        request = PlanRequest(goal="Use tools", tools=tools, min_steps=2, max_steps=4)

        result = planner.plan(request)

        assert result.success
        assert len(result.steps) >= 2

    def test_dfs_search_method(self):
        """Test DFS search produces valid results."""
        config = ToTConfig(max_depth=2, search_method=SearchMethod.DFS)
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        tools = [
            ToolMetadata(
                tool_id=f"tool_{i}",
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="test",
            )
            for i in range(3)
        ]

        request = PlanRequest(goal="Use tools", tools=tools, min_steps=2, max_steps=4)

        result = planner.plan(request)

        assert result.success
        assert len(result.steps) >= 2

    def test_get_statistics(self):
        """Test getting planner statistics."""
        config = ToTConfig(max_depth=2, branch_factor=3)
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        # Run a plan to generate statistics
        tools = [
            ToolMetadata(
                tool_id="search",
                name="search",
                description="Search",
                category="retrieval",
            ),
        ]
        request = PlanRequest(goal="Test", tools=tools, min_steps=1, max_steps=2)
        planner.plan(request)

        stats = planner.get_statistics()

        assert "total_nodes_generated" in stats
        assert "total_nodes_evaluated" in stats
        assert "config" in stats
        assert stats["config"]["max_depth"] == 2
        assert stats["config"]["branch_factor"] == 3

    def test_empty_tools_returns_empty_plan(self):
        """Test that empty tools returns result with no steps."""
        config = ToTConfig()
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        request = PlanRequest(goal="Do something", tools=[], min_steps=1, max_steps=5)

        result = planner.plan(request)

        # Should still return a result, but may not be "successful"
        assert result is not None

    def test_plan_respects_max_steps(self):
        """Test that plan respects max_steps constraint."""
        config = ToTConfig(max_depth=5)  # Allow deep search
        planner = TreeOfThoughtsPlanner(config=config, llm_client=None)

        tools = [
            ToolMetadata(
                tool_id=f"tool_{i}",
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="test",
            )
            for i in range(10)
        ]

        request = PlanRequest(goal="Use tools", tools=tools, min_steps=1, max_steps=3)

        result = planner.plan(request)

        assert len(result.steps) <= request.max_steps


class TestSearchMethod:
    """Test SearchMethod enum."""

    def test_search_method_values(self):
        """Test search method enum values."""
        assert SearchMethod.BFS.value == "bfs"
        assert SearchMethod.DFS.value == "dfs"

    def test_search_method_from_string(self):
        """Test creating search method from string."""
        assert SearchMethod("bfs") == SearchMethod.BFS
        assert SearchMethod("dfs") == SearchMethod.DFS
