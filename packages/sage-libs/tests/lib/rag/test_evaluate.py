"""
测试 sage.libs.rag.evaluate 模块
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

# 尝试导入评估模块
pytest_plugins = []

try:
    from sage.libs.rag.evaluate import (
        AccuracyEvaluate,
        BertRecallEvaluate,
        BRSEvaluate,
        CompressionRateEvaluate,
        ContextRecallEvaluate,
        F1Evaluate,
        LatencyEvaluate,
        RecallEvaluate,
        RougeLEvaluate,
        TokenCountEvaluate,
        _normalize_data,
    )

    EVALUATE_AVAILABLE = True
except ImportError as e:
    EVALUATE_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Evaluate module not available: {e}")


@pytest.fixture
def sample_evaluation_data():
    """提供测试评估数据的fixture"""
    return {
        "query": "什么是机器学习？",
        "generated": "机器学习是人工智能的一个分支，它使计算机能够自动学习。",
        "references": [
            "机器学习是人工智能的子领域，专注于算法的开发。",
            "机器学习让计算机能够从数据中学习模式。",
        ],
    }


@pytest.mark.unit
class TestNormalizeData:
    """测试_normalize_data函数"""

    def test_normalize_data_with_tuple_input(self):
        """测试tuple输入的数据标准化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 测试标准的(question, answer)元组
        input_data = ("什么是机器学习？", "机器学习是一种人工智能技术")
        result = _normalize_data(input_data)

        expected = {
            "query": "什么是机器学习？",
            "generated": "机器学习是一种人工智能技术",
            "references": [],
        }
        assert result == expected

    def test_normalize_data_with_empty_tuple(self):
        """Test empty tuple input"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = ()
        result = _normalize_data(input_data)

        expected = {"query": None, "generated": "", "references": []}
        assert result == expected

    def test_normalize_data_with_single_element_tuple(self):
        """测试单元素元组输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = ("What is AI?",)
        result = _normalize_data(input_data)

        expected = {"query": "What is AI?", "generated": "", "references": []}
        assert result == expected

    def test_normalize_data_with_non_string_tuple(self):
        """测试包含非字符串的元组输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = ("What is ML?", 123)
        result = _normalize_data(input_data)

        expected = {"query": "What is ML?", "generated": "123", "references": []}
        assert result == expected

    def test_normalize_data_with_complete_dict(self):
        """测试包含完整字段的字典输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {
            "query": "What is AI?",
            "generated": "AI is artificial intelligence.",
            "references": ["AI is machine intelligence.", "AI mimics human cognition."],
            "extra_field": "additional information",
        }
        result = _normalize_data(input_data)

        # 应该保留所有原始字段
        assert result == input_data

    def test_normalize_data_with_pred_golds_dict(self):
        """测试包含pred和golds的字典输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {
            "query": "What is machine learning?",
            "pred": "ML is a subset of AI",
            "golds": [
                "Machine learning is an AI technique",
                "ML enables computers to learn",
            ],
        }
        result = _normalize_data(input_data)

        # _normalize_data 对字典输入直接返回，不做转换
        expected = {
            "query": "What is machine learning?",
            "pred": "ML is a subset of AI",
            "golds": [
                "Machine learning is an AI technique",
                "ML enables computers to learn",
            ],
        }
        assert result == expected

    def test_normalize_data_with_missing_fields_dict(self):
        """测试缺少字段的字典输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {
            "query": "What is deep learning?",
            "other_field": "additional information",
        }
        result = _normalize_data(input_data)

        # _normalize_data 对字典输入直接返回，不添加字段
        expected = {
            "query": "What is deep learning?",
            "other_field": "additional information",
        }
        assert result == expected
        """测试缺少字段的字典输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {
            "query": "What is deep learning?",
            "other_field": "additional information",
        }
        result = _normalize_data(input_data)

        expected = {
            "query": "What is deep learning?",
            "other_field": "additional information",
            "generated": "",
            "references": [],
        }
        assert result == expected

    def test_normalize_data_with_non_list_references(self):
        """测试references不是列表的情况"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {
            "query": "What is neural networks?",
            "generated": "Neural networks are computing systems.",
            "references": "Neural networks mimic biological neurons",
        }
        result = _normalize_data(input_data)

        # _normalize_data 对字典输入直接返回，不做转换
        expected = {
            "query": "What is neural networks?",
            "generated": "Neural networks are computing systems.",
            "references": "Neural networks mimic biological neurons",
        }
        assert result == expected

    def test_normalize_data_with_golds_non_list(self):
        """测试golds不是列表的情况"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {"golds": "单个标准答案"}
        result = _normalize_data(input_data)

        # _normalize_data 对字典输入直接返回
        expected = {
            "golds": "单个标准答案",
        }
        assert result == expected

    def test_normalize_data_with_string_input(self):
        """测试字符串输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = "这是一个测试答案"
        result = _normalize_data(input_data)

        expected = {"query": None, "generated": "这是一个测试答案", "references": []}
        assert result == expected

    def test_normalize_data_with_number_input(self):
        """测试数字输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = 42
        result = _normalize_data(input_data)

        expected = {"query": None, "generated": "42", "references": []}
        assert result == expected

    def test_normalize_data_with_none_input(self):
        """测试None输入"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = None
        result = _normalize_data(input_data)

        expected = {"query": None, "generated": "None", "references": []}
        assert result == expected

    def test_normalize_data_preserves_extra_fields(self):
        """测试保留额外字段"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        input_data = {
            "query": "测试问题",
            "generated": "测试答案",
            "references": ["参考答案"],
            "metadata": {"source": "test"},
            "timestamp": "2025-09-22",
            "score": 0.85,
        }
        result = _normalize_data(input_data)

        # 所有字段都应该被保留
        assert result == input_data

    def test_normalize_data_with_query_references(self):
        """测试从query.references中提取参考答案（实际pipeline数据格式）"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 模拟实际pipeline中的数据结构（已更新为新格式）
        input_data = {
            "query": "Who has the highest goals in world football?",
            "references": [
                "Ali Dael has the highest goals in men's world international football with 109 goals.",
                "The players with the highest all-time goals differ.",
            ],
            "retrieval_results": [{"text": "some retrieval result"}],
            "generated": "The highest goalscorer in FIFA World Cup history is Gerd Müller with 10 goals.",
        }
        result = _normalize_data(input_data)

        # _normalize_data 对字典直接返回
        assert isinstance(result, dict)
        assert result["query"] == "Who has the highest goals in world football?"
        assert len(result["references"]) == 2

    def test_normalize_data_with_openai_generator_tuple(self):
        """测试OpenAIGenerator输出的tuple格式（实际pipeline数据格式）"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 模拟OpenAIGenerator的实际输出格式（tuple）
        input_data = (
            "Who has the highest goals in world football?",
            "Gerd Müller",
        )
        result = _normalize_data(input_data)

        # tuple输入转换为字典
        assert isinstance(result, dict)
        assert result["query"] == "Who has the highest goals in world football?"
        assert result["generated"] == "Gerd Müller"
        assert result["references"] == []

    def test_normalize_data_references_priority(self):
        """测试references字段优先级处理"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 现在统一格式，直接返回字典，不做转换
        input_data1 = {
            "references": ["main ref"],
            "generated": "answer",
        }
        result1 = _normalize_data(input_data1)
        assert result1["references"] == ["main ref"]

        # 带其他字段
        input_data2 = {
            "golds": ["golds ref"],
            "references": [],  # 空的顶级references
            "generated": "answer",
        }
        result2 = _normalize_data(input_data2)
        # 字典直接返回
        assert result2["references"] == []


@pytest.mark.unit
class TestF1Evaluate:
    """测试F1Evaluate类"""

    def test_f1_evaluate_initialization(self):
        """测试F1Evaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = F1Evaluate()
        assert hasattr(evaluator, "_get_tokens")
        assert hasattr(evaluator, "_f1_score")
        assert hasattr(evaluator, "execute")

    def test_get_tokens(self):
        """测试token提取"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = F1Evaluate()
        tokens = evaluator._get_tokens("Hello World Test")

        assert tokens == ["hello", "world", "test"]

    def test_f1_score_calculation(self):
        """测试F1分数计算"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = F1Evaluate()

        # 完全匹配
        score = evaluator._f1_score("hello world", "hello world")
        assert score == 1.0

        # 部分匹配
        score = evaluator._f1_score("hello world", "hello test")
        assert 0 < score < 1

        # 完全不匹配
        score = evaluator._f1_score("hello world", "test case")
        assert score == 0.0

    def test_f1_execute(self, sample_evaluation_data):
        """测试F1Evaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = F1Evaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            # 验证返回原始数据
            assert result == sample_evaluation_data

            # 验证打印了F1分数
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "F1" in call_args


@pytest.mark.unit
class TestRecallEvaluate:
    """测试RecallEvaluate类"""

    def test_recall_evaluate_initialization(self):
        """测试RecallEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = RecallEvaluate()
        assert hasattr(evaluator, "_get_tokens")
        assert hasattr(evaluator, "_recall")

    def test_recall_calculation(self):
        """测试Recall计算"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = RecallEvaluate()

        # 完全召回
        recall = evaluator._recall("hello world test", "hello world")
        assert recall == 1.0

        # 部分召回
        recall = evaluator._recall("hello", "hello world")
        assert recall == 0.5

        # 无召回
        recall = evaluator._recall("test", "hello world")
        assert recall == 0.0

    def test_recall_execute(self, sample_evaluation_data):
        """测试RecallEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = RecallEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Recall" in call_args


@pytest.mark.unit
class TestBertRecallEvaluate:
    """测试BertRecallEvaluate类"""

    @patch("sage.libs.rag.evaluate.AutoTokenizer")
    @patch("sage.libs.rag.evaluate.AutoModel")
    def test_bert_recall_initialization(self, mock_model, mock_tokenizer):
        """测试BertRecallEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 模拟BERT模型和tokenizer
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()

        evaluator = BertRecallEvaluate()

        assert evaluator.tokenizer is not None
        assert evaluator.model is not None
        mock_tokenizer.from_pretrained.assert_called_with("bert-base-uncased")
        mock_model.from_pretrained.assert_called_with("bert-base-uncased")

    @patch("sage.libs.rag.evaluate.AutoTokenizer")
    @patch("sage.libs.rag.evaluate.AutoModel")
    @patch("sage.libs.rag.evaluate.cosine_similarity")
    def test_bert_recall_execute(
        self,
        mock_cosine,
        mock_model_class,
        mock_tokenizer_class,
        sample_evaluation_data,
    ):
        """测试BertRecallEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 模拟tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {"input_ids": Mock(), "attention_mask": Mock()}
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        # 模拟model
        mock_model = Mock()
        mock_output = Mock()
        mock_embeddings = Mock()
        # 返回两个embeddings，一个用于pred，一个用于gold
        mock_embeddings.detach.return_value.numpy.return_value = np.array(
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        mock_output.last_hidden_state.mean.return_value = mock_embeddings
        mock_model.return_value = mock_output
        mock_model_class.from_pretrained.return_value = mock_model

        # 模拟余弦相似度
        mock_cosine.return_value = np.array([[0.85]])

        evaluator = BertRecallEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "BertRecall" in call_args


@pytest.mark.unit
class TestRougeLEvaluate:
    """测试RougeLEvaluate类"""

    @patch("sage.libs.rag.evaluate.Rouge")
    def test_rouge_l_initialization(self, mock_rouge_class):
        """测试RougeLEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        mock_rouge_instance = Mock()
        mock_rouge_class.return_value = mock_rouge_instance

        evaluator = RougeLEvaluate()

        assert evaluator.rouge is not None
        mock_rouge_class.assert_called_once()

    @patch("sage.libs.rag.evaluate.Rouge")
    def test_rouge_l_execute(self, mock_rouge_class, sample_evaluation_data):
        """测试RougeLEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 模拟Rouge结果
        mock_rouge_instance = Mock()
        mock_rouge_instance.get_scores.return_value = [{"rouge-l": {"f": 0.75}}]
        mock_rouge_class.return_value = mock_rouge_instance

        evaluator = RougeLEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "ROUGE-L" in call_args


@pytest.mark.unit
class TestBRSEvaluate:
    """测试BRSEvaluate类"""

    def test_brs_evaluate_initialization(self):
        """测试BRSEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = BRSEvaluate()
        assert hasattr(evaluator, "execute")

    def test_brs_execute(self, sample_evaluation_data):
        """测试BRSEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = BRSEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "BRS" in call_args


@pytest.mark.unit
class TestAccuracyEvaluate:
    """测试AccuracyEvaluate类"""

    def test_accuracy_evaluate_initialization(self):
        """测试AccuracyEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = AccuracyEvaluate()
        assert hasattr(evaluator, "execute")

    def test_accuracy_execute(self, sample_evaluation_data):
        """测试AccuracyEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = AccuracyEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Acc" in call_args


@pytest.mark.unit
class TestTokenCountEvaluate:
    """测试TokenCountEvaluate类"""

    def test_token_count_evaluate_initialization(self):
        """测试TokenCountEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = TokenCountEvaluate()
        assert hasattr(evaluator, "execute")

    def test_token_count_execute(self, sample_evaluation_data):
        """测试TokenCountEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = TokenCountEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Token Count" in call_args


@pytest.mark.unit
class TestLatencyEvaluate:
    """测试LatencyEvaluate类"""

    def test_latency_evaluate_initialization(self):
        """测试LatencyEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = LatencyEvaluate()
        assert hasattr(evaluator, "execute")

    def test_latency_execute(self, sample_evaluation_data):
        """测试LatencyEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = LatencyEvaluate()

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(sample_evaluation_data)

            assert result == sample_evaluation_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Latency" in call_args


@pytest.mark.unit
class TestContextRecallEvaluate:
    """测试ContextRecallEvaluate类"""

    def test_context_recall_evaluate_initialization(self):
        """测试ContextRecallEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = ContextRecallEvaluate()
        assert hasattr(evaluator, "execute")

    def test_context_recall_execute(self, sample_evaluation_data):
        """测试ContextRecallEvaluate执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = ContextRecallEvaluate()

        # ContextRecallEvaluate需要metadata字段
        test_data = sample_evaluation_data.copy()
        test_data["metadata"] = {
            "supporting_facts": {"sent_id": [0, 1]},
            "retrieved_contexts": [
                {"content": "机器学习是人工智能的子领域", "sent_id": 0},
                {"content": "它专注于算法的开发", "sent_id": 1},
            ],
        }

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(test_data)

            assert result == test_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Context Recall" in call_args


@pytest.mark.unit
class TestCompressionRateEvaluate:
    """测试CompressionRateEvaluate类"""

    def test_compression_rate_evaluate_initialization(self):
        """测试CompressionRateEvaluate初始化"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = CompressionRateEvaluate()
        assert hasattr(evaluator, "execute")

    def test_compression_rate_execute(self):
        """测试CompressionRateEvaluate基本执行功能"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = CompressionRateEvaluate()

        test_data = {
            "query": "What is artificial intelligence?",
            "generated": "AI is a field of computer science.",
            "references": [
                "Artificial intelligence is the simulation of human intelligence."
            ],
            "retrieved_docs": ["Original document content about AI"],
            "refined_docs": ["Compressed document content"],
        }

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(test_data)

            assert result == test_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Compression Rate" in call_args

    def test_compression_rate_execute_with_empty_docs(self):
        """测试CompressionRateEvaluate在空文档情况下的执行"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = CompressionRateEvaluate()

        test_data = {
            "query": "What is machine learning?",
            "generated": "Machine learning is a subset of AI.",
            "references": ["Machine learning is a method of data analysis."],
            "retrieved_docs": [],
            "refined_docs": [],
        }

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(test_data)

            assert result == test_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Compression Rate" in call_args
            assert "0.00" in call_args

    def test_compression_rate_calculate_correctly(self):
        """Test CompressionRateEvaluate compression rate calculation accuracy"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        evaluator = CompressionRateEvaluate()

        # Test specific compression rate calculation
        test_data = {
            "query": "What is deep learning?",
            "generated": "Deep learning uses neural networks.",
            "references": ["Deep learning is a machine learning technique."],
            "retrieval_docs": [
                "Original document containing ten words about deep learning neural networks technology"
            ],  # 11 tokens
            "refining_docs": ["Compressed neural networks document"],  # 4 tokens
        }

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(test_data)

            assert result == test_data
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Compression Rate" in call_args
            # Compression rate should be 11/4 = 2.75
            assert "2.75" in call_args


@pytest.mark.integration
class TestEvaluateIntegration:
    """评估模块集成测试"""

    def test_multiple_evaluators_pipeline(self, sample_evaluation_data):
        """测试多个评估器管道"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 创建评估器链
        evaluators = [F1Evaluate(), RecallEvaluate(), BRSEvaluate(), AccuracyEvaluate()]

        result = sample_evaluation_data

        with patch("builtins.print"):
            for evaluator in evaluators:
                result = evaluator.execute(result)

        # 数据应该在管道中保持不变
        assert result == sample_evaluation_data

    def test_evaluators_with_different_data_formats(self):
        """测试不同数据格式的评估器"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 测试数据格式1：标准格式
        data1 = {
            "query": "测试问题1",
            "generated": "生成回答1",
            "references": ["参考答案1", "参考答案2"],
        }

        # 测试数据格式2：无参考答案
        data2 = {"query": "测试问题2", "generated": "生成回答2", "references": []}

        evaluator = F1Evaluate()

        with patch("builtins.print"):
            result1 = evaluator.execute(data1)
            result2 = evaluator.execute(data2)

        assert result1 == data1
        assert result2 == data2


@pytest.mark.slow
class TestEvaluatePerformance:
    """评估性能测试"""

    def test_large_data_evaluation(self):
        """测试大数据量评估"""
        if not EVALUATE_AVAILABLE:
            pytest.skip("Evaluate module not available")

        # 创建大量数据
        large_data = {
            "query": "性能测试问题",
            "generated": " ".join([f"词{i}" for i in range(1000)]),
            "references": [" ".join([f"参考词{i}" for i in range(500)])],
        }

        evaluator = F1Evaluate()

        import time

        start_time = time.time()

        with patch("builtins.print"):
            result = evaluator.execute(large_data)

        end_time = time.time()

        # 验证结果正确性
        assert result == large_data

        # 验证性能（应该在合理时间内完成）
        assert end_time - start_time < 5.0  # 应该在5秒内完成


@pytest.mark.unit
class TestEvaluateFallback:
    """评估模块降级测试"""

    def test_evaluate_module_fallback(self):
        """测试评估模块降级"""

        # 模拟评估器基类
        class MockEvaluator:
            def __init__(self, name):
                self.name = name

            def execute(self, data):
                print(f"[{self.name}] : 0.8500")
                return data

        evaluator = MockEvaluator("MockF1")
        data = {"query": "test", "generated": "answer", "references": ["ref"]}

        with patch("builtins.print") as mock_print:
            result = evaluator.execute(data)

            assert result == data
            mock_print.assert_called_once_with("[MockF1] : 0.8500")

    def test_basic_evaluation_concepts(self):
        """测试基本评估概念"""

        # 测试基本的F1计算逻辑
        def simple_f1(pred_tokens, ref_tokens):
            pred_set = set(pred_tokens)
            ref_set = set(ref_tokens)

            if not pred_set and not ref_set:
                return 1.0
            if not pred_set or not ref_set:
                return 0.0

            intersection = pred_set & ref_set
            precision = len(intersection) / len(pred_set)
            recall = len(intersection) / len(ref_set)

            if precision + recall == 0:
                return 0.0

            return 2 * precision * recall / (precision + recall)

        # 测试完全匹配
        f1 = simple_f1(["hello", "world"], ["hello", "world"])
        assert f1 == 1.0

        # 测试部分匹配
        f1 = simple_f1(["hello", "test"], ["hello", "world"])
        assert 0 < f1 < 1

        # 测试无匹配
        f1 = simple_f1(["test"], ["hello", "world"])
        assert 0 <= f1 < 1
