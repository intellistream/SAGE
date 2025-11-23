"""
Tests for BaseMetric interface
"""

import pytest
from sage.benchmark.benchmark_memory.evaluation.core.metric_interface import BaseMetric


class DummyMetric(BaseMetric):
    """Dummy metric for testing base class functionality"""

    def compute_single_question(self, predicted_answer, reference_answer, metadata=None):
        """Simple dummy implementation: return 1.0 if answers match, 0.0 otherwise"""
        return 1.0 if predicted_answer == reference_answer else 0.0


class TestBaseMetric:
    """Test cases for BaseMetric interface"""

    def setup_method(self):
        """Setup test fixture"""
        self.metric = DummyMetric(name="Dummy", description="Test metric")

    def test_initialization(self):
        """Test metric initialization"""
        assert self.metric.name == "Dummy"
        assert self.metric.description == "Test metric"

    def test_str_representation(self):
        """Test string representation"""
        assert str(self.metric) == "Metric(Dummy)"

    def test_repr_representation(self):
        """Test repr representation"""
        assert repr(self.metric) == "Metric(name='Dummy', description='Test metric')"

    def test_compute_test_round_perfect(self):
        """Test compute_test_round with all perfect matches"""
        questions = [
            {"predicted_answer": "answer1", "reference_answer": "answer1"},
            {"predicted_answer": "answer2", "reference_answer": "answer2"},
            {"predicted_answer": "answer3", "reference_answer": "answer3"},
        ]
        score = self.metric.compute_test_round(questions)
        assert score == 1.0

    def test_compute_test_round_partial(self):
        """Test compute_test_round with partial matches"""
        questions = [
            {"predicted_answer": "answer1", "reference_answer": "answer1"},
            {"predicted_answer": "answer2", "reference_answer": "wrong2"},
            {"predicted_answer": "answer3", "reference_answer": "answer3"},
        ]
        score = self.metric.compute_test_round(questions)
        # 2 out of 3 correct = 0.666...
        assert abs(score - 2 / 3) < 0.01

    def test_compute_test_round_empty(self):
        """Test compute_test_round with empty questions"""
        questions = []
        score = self.metric.compute_test_round(questions)
        assert score == 0.0

    def test_compute_test_round_missing_fields(self):
        """Test compute_test_round with missing fields"""
        questions = [
            {"predicted_answer": "answer1"},  # Missing reference_answer
            {"reference_answer": "answer2"},  # Missing predicted_answer
        ]
        score = self.metric.compute_test_round(questions)
        # Both should return 0.0
        assert score == 0.0

    def test_compute_all_rounds(self):
        """Test compute_all_rounds"""
        test_results = [
            {
                "test_index": 1,
                "questions": [
                    {"predicted_answer": "a1", "reference_answer": "a1"},
                    {"predicted_answer": "a2", "reference_answer": "a2"},
                ],
            },
            {
                "test_index": 2,
                "questions": [
                    {"predicted_answer": "a1", "reference_answer": "wrong"},
                ],
            },
        ]
        scores = self.metric.compute_all_rounds(test_results)
        assert len(scores) == 2
        assert scores[0] == 1.0
        assert scores[1] == 0.0

    def test_compute_all_rounds_empty(self):
        """Test compute_all_rounds with empty results"""
        test_results = []
        scores = self.metric.compute_all_rounds(test_results)
        assert scores == []

    def test_compute_overall_statistics(self):
        """Test compute_overall with various scores"""
        test_results = [
            {
                "test_index": 1,
                "questions": [
                    {"predicted_answer": "a1", "reference_answer": "a1"},
                    {"predicted_answer": "a2", "reference_answer": "a2"},
                ],
            },
            {
                "test_index": 2,
                "questions": [
                    {"predicted_answer": "a1", "reference_answer": "a1"},
                    {"predicted_answer": "a2", "reference_answer": "wrong"},
                ],
            },
            {
                "test_index": 3,
                "questions": [
                    {"predicted_answer": "a1", "reference_answer": "wrong"},
                ],
            },
        ]
        stats = self.metric.compute_overall(test_results)

        # Round 1: 1.0, Round 2: 0.5, Round 3: 0.0
        assert abs(stats["mean"] - 0.5) < 0.01
        assert stats["max"] == 1.0
        assert stats["min"] == 0.0
        assert stats["std"] > 0  # Should have some variance

    def test_compute_overall_single_round(self):
        """Test compute_overall with single round (std should be 0)"""
        test_results = [
            {
                "test_index": 1,
                "questions": [
                    {"predicted_answer": "a1", "reference_answer": "a1"},
                ],
            },
        ]
        stats = self.metric.compute_overall(test_results)
        assert stats["mean"] == 1.0
        assert stats["max"] == 1.0
        assert stats["min"] == 1.0
        assert stats["std"] == 0.0

    def test_compute_overall_empty(self):
        """Test compute_overall with empty results"""
        test_results = []
        stats = self.metric.compute_overall(test_results)
        assert stats["mean"] == 0.0
        assert stats["max"] == 0.0
        assert stats["min"] == 0.0
        assert stats["std"] == 0.0

    def test_abstract_method_enforcement(self):
        """Test that BaseMetric cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseMetric(name="Invalid", description="Should fail")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
