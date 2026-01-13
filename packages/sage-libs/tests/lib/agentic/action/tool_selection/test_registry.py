"""
Tests for selector registry.
"""

from dataclasses import dataclass

import pytest
from sage_libs.sage_agentic.agents.action.tool_selection.base import SelectorResources
from sage_libs.sage_agentic.agents.action.tool_selection.keyword_selector import KeywordSelector
from sage_libs.sage_agentic.agents.action.tool_selection.registry import (
    SelectorRegistry,
)
from sage_libs.sage_agentic.agents.action.tool_selection.schemas import (
    KeywordSelectorConfig,
)


@dataclass
class MockTool:
    """Mock tool object."""

    tool_id: str
    name: str
    description: str
    capabilities: list[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class MockToolsLoader:
    """Mock tool loader for testing."""

    def __init__(self):
        self.tools = {
            "search": MockTool("search", "Search", "Search tool", ["search"]),
        }

    def get_tool(self, tool_id):
        return self.tools.get(tool_id)

    def get_all_tools(self):
        return list(self.tools.values())

    def iter_all(self):
        yield from self.tools.values()


class TestSelectorRegistry:
    """Tests for selector registry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry instance."""
        return SelectorRegistry()

    @pytest.fixture
    def resources(self):
        """Create test resources."""
        return SelectorResources(tools_loader=MockToolsLoader())

    def test_register_selector(self, registry):
        """Test registering a selector class."""
        registry.register("keyword", KeywordSelector)

        assert registry.get_class("keyword") == KeywordSelector

    def test_get_selector_class(self, registry):
        """Test getting registered selector class."""
        registry.register("keyword", KeywordSelector)

        cls = registry.get_class("keyword")
        assert cls == KeywordSelector

    def test_get_unregistered_selector_class_returns_none(self, registry):
        """Test that getting unregistered selector class returns None."""
        cls = registry.get_class("nonexistent")
        assert cls is None

    def test_get_selector_instance(self, registry, resources):
        """Test getting selector instance."""
        registry.register("keyword", KeywordSelector)

        config = KeywordSelectorConfig()
        selector = registry.get("keyword", config=config, resources=resources)

        assert isinstance(selector, KeywordSelector)
        assert selector.name == "keyword"

    def test_list_selectors(self, registry):
        """Test listing all registered selectors."""
        registry.register("keyword", KeywordSelector)
        registry.register("keyword_v2", KeywordSelector)

        # Check classes are registered
        assert registry.get_class("keyword") is not None
        assert registry.get_class("keyword_v2") is not None

    def test_singleton_instance(self):
        """Test that get_instance returns singleton."""
        instance1 = SelectorRegistry.get_instance()
        instance2 = SelectorRegistry.get_instance()

        assert instance1 is instance2


class TestRegistryIntegration:
    """Integration tests for registry with real selectors."""

    def test_full_workflow(self):
        """Test complete workflow: register -> configure -> create -> select."""
        from sage_libs.sage_agentic.agents.action.tool_selection.schemas import ToolSelectionQuery

        # Setup
        registry = SelectorRegistry()
        registry.register("keyword", KeywordSelector)

        config = KeywordSelectorConfig(top_k=3)
        resources = SelectorResources(tools_loader=MockToolsLoader())

        # Get selector from registry
        selector = registry.get("keyword", config=config, resources=resources)

        # Execute selection
        query = ToolSelectionQuery(
            sample_id="test", instruction="Search for information", candidate_tools=["search"]
        )

        results = selector.select(query)

        # Verify results
        assert isinstance(results, list)
