"""
Unit tests for sage.middleware.operators.rag.profiler module.
Tests Query_Profiler and QueryProfilerResult.
"""

import pytest

try:
    from sage.middleware.operators.rag.profiler import (
        Query_Profiler,
        QueryProfilerResult,
    )

    PROFILER_AVAILABLE = True
except ImportError as e:
    PROFILER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Profiler module not available: {e}")


@pytest.mark.unit
class TestQueryProfilerResult:
    """Test QueryProfilerResult dataclass validation."""

    def test_valid_initialization(self):
        """Test creating QueryProfilerResult with valid parameters."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        result = QueryProfilerResult(
            need_joint_reasoning=True,
            complexity="High",
            need_summarization=True,
            summarization_length=100,
            n_info_items=3,
        )

        assert result.need_joint_reasoning is True
        assert result.complexity == "High"
        assert result.need_summarization is True
        assert result.summarization_length == 100
        assert result.n_info_items == 3

    def test_invalid_complexity(self):
        """Test validation error for invalid complexity value."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        with pytest.raises(ValueError, match="complexity必须是'High'或'Low'"):
            QueryProfilerResult(
                need_joint_reasoning=False,
                complexity="Medium",  # Invalid
                need_summarization=False,
                summarization_length=50,
                n_info_items=2,
            )

    def test_invalid_summarization_length_too_low(self):
        """Test validation error for summarization_length < 30."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        with pytest.raises(ValueError, match="summarization_length必须在30-200之间"):
            QueryProfilerResult(
                need_joint_reasoning=False,
                complexity="Low",
                need_summarization=True,
                summarization_length=20,  # Too low
                n_info_items=1,
            )

    def test_invalid_summarization_length_too_high(self):
        """Test validation error for summarization_length > 200."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        with pytest.raises(ValueError, match="summarization_length必须在30-200之间"):
            QueryProfilerResult(
                need_joint_reasoning=False,
                complexity="Low",
                need_summarization=True,
                summarization_length=250,  # Too high
                n_info_items=1,
            )

    def test_invalid_n_info_items_too_low(self):
        """Test validation error for n_info_items < 1."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        with pytest.raises(ValueError, match="n_info_items必须在1-6之间"):
            QueryProfilerResult(
                need_joint_reasoning=False,
                complexity="Low",
                need_summarization=False,
                summarization_length=50,
                n_info_items=0,  # Too low
            )

    def test_invalid_n_info_items_too_high(self):
        """Test validation error for n_info_items > 6."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        with pytest.raises(ValueError, match="n_info_items必须在1-6之间"):
            QueryProfilerResult(
                need_joint_reasoning=False,
                complexity="Low",
                need_summarization=False,
                summarization_length=50,
                n_info_items=10,  # Too high
            )

    def test_boundary_values(self):
        """Test boundary values for summarization_length and n_info_items."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        # Min values
        result_min = QueryProfilerResult(
            need_joint_reasoning=False,
            complexity="Low",
            need_summarization=False,
            summarization_length=30,  # Min valid
            n_info_items=1,  # Min valid
        )
        assert result_min.summarization_length == 30
        assert result_min.n_info_items == 1

        # Max values
        result_max = QueryProfilerResult(
            need_joint_reasoning=True,
            complexity="High",
            need_summarization=True,
            summarization_length=200,  # Max valid
            n_info_items=6,  # Max valid
        )
        assert result_max.summarization_length == 200
        assert result_max.n_info_items == 6


@pytest.mark.unit
class TestQueryProfiler:
    """Test Query_Profiler operator."""

    def test_initialization(self):
        """Test Query_Profiler initialization."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        config = {}
        profiler = Query_Profiler(config)
        assert profiler is not None

    def test_execute_with_valid_json(self):
        """Test execute with valid JSON input."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        config = {}
        profiler = Query_Profiler(config)

        json_data = """
        {
            "need_joint_reasoning": true,
            "complexity": "High",
            "need_summarization": true,
            "summarization_length": 150,
            "n_info_items": 4
        }
        """

        # Should not raise error
        result = profiler.execute(json_data)
        # Result depends on logic, just test it runs
        assert result is not None

    def test_execute_with_default_values(self):
        """Test execute with missing fields uses defaults."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        config = {}
        profiler = Query_Profiler(config)

        # Empty JSON object - should use defaults
        json_data = "{}"

        result = profiler.execute(json_data)
        assert result is not None

    def test_execute_with_partial_data(self):
        """Test execute with partial JSON data."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        config = {}
        profiler = Query_Profiler(config)

        json_data = """
        {
            "need_joint_reasoning": false,
            "complexity": "Low"
        }
        """

        result = profiler.execute(json_data)
        assert result is not None

    def test_execute_invalid_json(self):
        """Test execute with invalid JSON raises error."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        config = {}
        profiler = Query_Profiler(config)

        invalid_json = "not a json"

        with pytest.raises((ValueError, TypeError)):  # JSONDecodeError is ValueError
            profiler.execute(invalid_json)

    def test_execute_with_invalid_values(self):
        """Test execute with invalid field values in JSON."""
        if not PROFILER_AVAILABLE:
            pytest.skip("Profiler not available")

        config = {}
        profiler = Query_Profiler(config)

        json_data = """
        {
            "complexity": "Invalid",
            "summarization_length": 300,
            "n_info_items": 10
        }
        """

        with pytest.raises(ValueError):
            profiler.execute(json_data)
