"""
Tests for DependencyGraph module.
"""

import pytest
from sage_libs.sage_agentic.agents.planning import DependencyGraph, PlanStep


class TestDependencyGraph:
    """Test dependency graph functionality."""

    def test_create_empty_graph(self):
        """Test creating empty dependency graph."""
        steps = []
        with pytest.raises((ValueError, AssertionError)):
            # Should fail validation - no steps
            graph = DependencyGraph(steps)
            graph.validate()

    def test_create_simple_graph(self):
        """Test creating simple linear dependency graph."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[1]),
            PlanStep(id=3, action="step3", depends_on=[2]),
        ]

        graph = DependencyGraph(steps)
        assert graph.validate()

    def test_detect_no_cycles(self):
        """Test cycle detection on acyclic graph."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[1]),
            PlanStep(id=3, action="step3", depends_on=[1, 2]),
        ]

        graph = DependencyGraph(steps)
        assert not graph.has_cycle()
        assert graph.detect_cycles() is None

    def test_detect_simple_cycle(self):
        """Test cycle detection on graph with simple cycle."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[2]),
            PlanStep(id=2, action="step2", depends_on=[1]),
        ]

        graph = DependencyGraph(steps)
        assert graph.has_cycle()
        cycle = graph.detect_cycles()
        assert cycle is not None
        assert len(cycle) >= 2

    def test_topological_sort_linear(self):
        """Test topological sort on linear graph."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[1]),
            PlanStep(id=3, action="step3", depends_on=[2]),
        ]

        graph = DependencyGraph(steps)
        sorted_steps = graph.topological_sort()

        assert len(sorted_steps) == 3
        assert sorted_steps[0].id == 1
        assert sorted_steps[1].id == 2
        assert sorted_steps[2].id == 3

    def test_topological_sort_parallel(self):
        """Test topological sort with parallel branches."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[]),
            PlanStep(id=3, action="step3", depends_on=[1, 2]),
        ]

        graph = DependencyGraph(steps)
        sorted_steps = graph.topological_sort()

        assert len(sorted_steps) == 3
        # Steps 1 and 2 should come before 3
        step3_idx = next(i for i, s in enumerate(sorted_steps) if s.id == 3)
        step1_idx = next(i for i, s in enumerate(sorted_steps) if s.id == 1)
        step2_idx = next(i for i, s in enumerate(sorted_steps) if s.id == 2)
        assert step1_idx < step3_idx
        assert step2_idx < step3_idx

    def test_topological_sort_fails_on_cycle(self):
        """Test topological sort raises error on cyclic graph."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[2]),
            PlanStep(id=2, action="step2", depends_on=[1]),
        ]

        graph = DependencyGraph(steps)
        with pytest.raises(ValueError, match="cycle"):
            graph.topological_sort()

    def test_get_root_steps(self):
        """Test getting root steps (no dependencies)."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[]),
            PlanStep(id=3, action="step3", depends_on=[1, 2]),
        ]

        graph = DependencyGraph(steps)
        roots = graph.get_root_steps()

        assert len(roots) == 2
        assert all(step.id in [1, 2] for step in roots)

    def test_get_leaf_steps(self):
        """Test getting leaf steps (no dependents)."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[1]),
            PlanStep(id=3, action="step3", depends_on=[1]),
        ]

        graph = DependencyGraph(steps)
        leaves = graph.get_leaf_steps()

        assert len(leaves) == 2
        assert all(step.id in [2, 3] for step in leaves)

    def test_execution_levels(self):
        """Test getting execution levels for parallelization."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[]),
            PlanStep(id=2, action="step2", depends_on=[]),
            PlanStep(id=3, action="step3", depends_on=[1]),
            PlanStep(id=4, action="step4", depends_on=[2]),
            PlanStep(id=5, action="step5", depends_on=[3, 4]),
        ]

        graph = DependencyGraph(steps)
        levels = graph.get_execution_levels()

        # Level 0: steps 1, 2 (no deps)
        # Level 1: steps 3, 4 (depend on level 0)
        # Level 2: step 5 (depends on level 1)
        assert len(levels) == 3
        assert len(levels[0]) == 2
        assert len(levels[1]) == 2
        assert len(levels[2]) == 1

    def test_validate_too_many_steps(self):
        """Test validation fails when too many steps."""
        steps = [PlanStep(id=i, action=f"step{i}", depends_on=[]) for i in range(1, 15)]

        graph = DependencyGraph(steps)
        assert not graph.validate(max_steps=10)

    def test_validate_missing_dependency(self):
        """Test validation fails for missing dependency."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[999]),  # Non-existent step
        ]

        graph = DependencyGraph(steps)
        assert not graph.validate()

    def test_validate_self_dependency(self):
        """Test validation fails for self-dependency."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[1]),
        ]

        graph = DependencyGraph(steps)
        assert not graph.validate()

    def test_repair_removes_self_dependency(self):
        """Test repair removes self-dependencies."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[1]),
        ]

        graph = DependencyGraph(steps)
        repaired = graph.repair_dependencies()

        assert len(repaired) == 1
        assert repaired[0].depends_on == []

    def test_repair_removes_invalid_dependencies(self):
        """Test repair removes dependencies on non-existent steps."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[999]),
            PlanStep(id=2, action="step2", depends_on=[1, 888]),
        ]

        graph = DependencyGraph(steps)
        repaired = graph.repair_dependencies()

        assert repaired[0].depends_on == []
        assert repaired[1].depends_on == [1]

    def test_repair_breaks_cycles(self):
        """Test repair breaks cycles by removing edges."""
        steps = [
            PlanStep(id=1, action="step1", depends_on=[2]),
            PlanStep(id=2, action="step2", depends_on=[1]),
        ]

        graph = DependencyGraph(steps)
        repaired = graph.repair_dependencies()

        # After repair, should be acyclic
        repaired_graph = DependencyGraph(repaired)
        assert not repaired_graph.has_cycle()
