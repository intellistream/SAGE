"""
Tests for F1 Score metric
"""

import pytest
from sage.benchmark.benchmark_memory.evaluation.accuracy.f1_score import F1Score


class TestF1Score:
    """Test cases for F1Score metric"""

    def setup_method(self):
        """Setup test fixture"""
        self.metric = F1Score()

    def test_initialization(self):
        """Test metric initialization"""
        assert self.metric.name == "F1"
        assert "F1 Score" in self.metric.description

    def test_perfect_match(self):
        """Test F1 score with perfect match"""
        pred = "The answer is 42"
        ref = "The answer is 42"
        score = self.metric.compute_single_question(pred, ref)
        assert score == 1.0

    def test_partial_match(self):
        """Test F1 score with partial match"""
        pred = "The answer is 42"
        ref = "The correct answer is 42"
        score = self.metric.compute_single_question(pred, ref)
        # Common tokens: "the", "answer", "is", "42" = 4
        # Pred tokens: 4, Ref tokens: 5
        # Precision = 4/4 = 1.0, Recall = 4/5 = 0.8
        # F1 = 2 * (1.0 * 0.8) / (1.0 + 0.8) = 0.888...
        assert 0.88 < score < 0.89

    def test_no_match(self):
        """Test F1 score with no match"""
        pred = "The answer is 42"
        ref = "Wrong response"
        score = self.metric.compute_single_question(pred, ref)
        assert score == 0.0

    def test_empty_predicted_answer(self):
        """Test F1 score with empty predicted answer"""
        pred = ""
        ref = "The answer is 42"
        score = self.metric.compute_single_question(pred, ref)
        assert score == 0.0

    def test_empty_reference_answer(self):
        """Test F1 score with empty reference answer"""
        pred = "The answer is 42"
        ref = ""
        score = self.metric.compute_single_question(pred, ref)
        assert score == 0.0

    def test_both_empty_answers(self):
        """Test F1 score with both answers empty"""
        pred = ""
        ref = ""
        score = self.metric.compute_single_question(pred, ref)
        assert score == 0.0

    def test_case_insensitive(self):
        """Test F1 score is case insensitive"""
        pred = "The Answer Is 42"
        ref = "the answer is 42"
        score = self.metric.compute_single_question(pred, ref)
        assert score == 1.0

    def test_non_string_answers(self):
        """Test F1 score with non-string answers"""
        pred = 42
        ref = "42"
        score = self.metric.compute_single_question(pred, ref)  # type: ignore[arg-type]
        assert score == 1.0

    def test_compute_test_round(self):
        """Test computing F1 score for a test round"""
        questions = [
            {"predicted_answer": "answer 1", "reference_answer": "answer 1"},
            {"predicted_answer": "answer 2", "reference_answer": "answer 2 correct"},
            {"predicted_answer": "answer 3", "reference_answer": "answer 3"},
        ]
        score = self.metric.compute_test_round(questions)
        # First and third are perfect (1.0), second is partial
        assert 0.8 < score < 1.0

    def test_compute_test_round_empty(self):
        """Test computing F1 score for empty test round"""
        questions = []
        score = self.metric.compute_test_round(questions)
        assert score == 0.0

    def test_compute_all_rounds(self):
        """Test computing F1 score for all rounds"""
        test_results = [
            {
                "test_index": 1,
                "questions": [
                    {"predicted_answer": "answer 1", "reference_answer": "answer 1"},
                ],
            },
            {
                "test_index": 2,
                "questions": [
                    {"predicted_answer": "answer 2", "reference_answer": "wrong"},
                ],
            },
        ]
        scores = self.metric.compute_all_rounds(test_results)
        assert len(scores) == 2
        assert scores[0] == 1.0
        assert scores[1] == 0.0

    def test_compute_overall(self):
        """Test computing overall statistics"""
        test_results = [
            {
                "test_index": 1,
                "questions": [
                    {"predicted_answer": "answer 1", "reference_answer": "answer 1"},
                ],
            },
            {
                "test_index": 2,
                "questions": [
                    {"predicted_answer": "answer 2", "reference_answer": "answer 2"},
                ],
            },
        ]
        stats = self.metric.compute_overall(test_results)
        assert stats["mean"] == 1.0
        assert stats["max"] == 1.0
        assert stats["min"] == 1.0
        assert stats["std"] == 0.0

    def test_compute_overall_empty(self):
        """Test computing overall statistics with empty results"""
        test_results = []
        stats = self.metric.compute_overall(test_results)
        assert stats["mean"] == 0.0
        assert stats["max"] == 0.0
        assert stats["min"] == 0.0
        assert stats["std"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
