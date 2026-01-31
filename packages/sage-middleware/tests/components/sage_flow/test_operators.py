"""
Unit tests for SageFlow operators
"""

import numpy as np
import pytest

from sage.middleware.components.sage_flow.operators import (
    SageFlowAggregationOperator,
    SageFlowContextSource,
    SageFlowJoinOperator,
    VectorJoinResult,
)


@pytest.mark.unit
class TestVectorJoinResult:
    """Tests for VectorJoinResult dataclass"""

    def test_vectorjoinresult_creation(self):
        """Test VectorJoinResult can be created"""
        result = VectorJoinResult(
            query_id=1,
            query_vector=np.array([1.0, 2.0, 3.0]),
            matched_doc_ids=[10, 20],
            matched_vectors=[np.array([1.0, 2.0, 3.0]), np.array([2.0, 3.0, 4.0])],
            similarity_scores=[0.9, 0.8],
            metadata={"key": "value"},
        )

        assert result.query_id == 1
        assert len(result.query_vector) == 3
        assert len(result.matched_doc_ids) == 2
        assert result.metadata["key"] == "value"

    def test_vectorjoinresult_defaults(self):
        """Test VectorJoinResult with default values"""
        result = VectorJoinResult(
            query_id=1,
            query_vector=np.array([1.0, 2.0]),
        )

        assert result.matched_doc_ids == []
        assert result.matched_vectors == []
        assert result.similarity_scores == []
        assert result.metadata == {}


@pytest.mark.unit
class TestSageFlowJoinOperator:
    """Tests for SageFlowJoinOperator"""

    def test_operator_init(self):
        """Test operator initialization"""
        doc_vectors = np.random.rand(10, 128).astype(np.float32)
        doc_ids = list(range(10))

        operator = SageFlowJoinOperator(
            dim=128,
            doc_vectors=doc_vectors,
            doc_ids=doc_ids,
            similarity_threshold=0.7,
        )

        assert operator.dim == 128
        assert operator.similarity_threshold == 0.7
        assert len(operator.doc_ids) == 10
        assert operator.doc_vectors.shape == (10, 128)

    def test_operator_init_with_list_vectors(self):
        """Test operator initialization with list vectors"""
        doc_vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]

        operator = SageFlowJoinOperator(
            dim=3,
            doc_vectors=doc_vectors,
            similarity_threshold=0.5,
        )

        assert operator.doc_vectors.shape == (2, 3)
        assert operator.doc_vectors.dtype == np.float32

    def test_operator_auto_doc_ids(self):
        """Test automatic doc_ids generation"""
        doc_vectors = np.random.rand(5, 64).astype(np.float32)

        operator = SageFlowJoinOperator(
            dim=64,
            doc_vectors=doc_vectors,
        )

        assert operator.doc_ids == [0, 1, 2, 3, 4]

    def test_operator_lazy_initialization(self):
        """Test operator lazy initialization flag"""
        doc_vectors = np.random.rand(3, 32).astype(np.float32)

        operator = SageFlowJoinOperator(
            dim=32,
            doc_vectors=doc_vectors,
        )

        assert not operator._initialized
        assert operator._env is None
        assert operator._pipeline is None


@pytest.mark.unit
class TestSageFlowAggregationOperator:
    """Tests for SageFlowAggregationOperator"""

    def test_aggregation_operator_init(self):
        """Test aggregation operator initialization"""
        operator = SageFlowAggregationOperator(
            dim=128,
            similarity_threshold=0.85,
            aggregation_window_ms=5000,
            min_group_size=2,
        )

        assert operator.dim == 128
        assert operator.similarity_threshold == 0.85
        assert operator.aggregation_window_ms == 5000
        assert operator.min_group_size == 2

    def test_aggregation_operator_default_params(self):
        """Test aggregation operator with default parameters"""
        operator = SageFlowAggregationOperator(dim=64)

        # Check defaults
        assert operator.dim == 64
        assert operator.similarity_threshold == 0.85  # default
        assert operator.aggregation_window_ms == 5000  # default
        assert operator.min_group_size == 1  # default


@pytest.mark.unit
class TestSageFlowContextSource:
    """Tests for SageFlowContextSource"""

    def test_context_source_class_attributes(self):
        """Test context source class exists and has correct signature"""
        import inspect

        # Verify class exists
        assert hasattr(SageFlowContextSource, "__init__")

        # Verify signature
        sig = inspect.signature(SageFlowContextSource.__init__)
        assert "dim" in sig.parameters
        assert "output_format" in sig.parameters

        # Verify default values
        assert sig.parameters["dim"].default == 128
        assert sig.parameters["output_format"].default == "dict"

    def test_context_source_methods_exist(self):
        """Test context source has required methods"""
        # Verify methods exist
        assert hasattr(SageFlowContextSource, "push")
        assert hasattr(SageFlowContextSource, "execute")
        assert hasattr(SageFlowContextSource, "_setup_sink")

    def test_context_source_inherits_from_source_function(self):
        """Test context source inherits from SourceFunction"""
        from sage.common.core.functions.source_function import SourceFunction

        assert issubclass(SageFlowContextSource, SourceFunction)


@pytest.mark.unit
class TestOperatorIntegration:
    """Integration tests for operator components"""

    def test_join_operator_vectorization(self):
        """Test vector input handling"""
        doc_vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

        operator = SageFlowJoinOperator(
            dim=2,
            doc_vectors=doc_vectors,
        )

        # Verify vectors are properly normalized to float32
        assert operator.doc_vectors.dtype == np.float32
        assert operator.doc_vectors.shape == (2, 2)

    def test_multiple_operators_creation(self):
        """Test creating multiple operators doesn't conflict"""
        doc_vectors_1 = np.random.rand(5, 32).astype(np.float32)
        doc_vectors_2 = np.random.rand(10, 64).astype(np.float32)

        op1 = SageFlowJoinOperator(dim=32, doc_vectors=doc_vectors_1)
        op2 = SageFlowJoinOperator(dim=64, doc_vectors=doc_vectors_2)

        assert op1.dim == 32
        assert op2.dim == 64
        assert op1.doc_vectors.shape[0] == 5
        assert op2.doc_vectors.shape[0] == 10
