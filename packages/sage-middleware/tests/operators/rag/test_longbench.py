"""
LongBench Integration Tests

测试 LongBench 相关组件：
- LongBenchBatch: 数据加载
- LongBenchPromptor: Prompt 构建
- LongBenchEvaluator: 评估指标
"""

import pytest

# =============================================================================
# Test LongBenchBatch
# =============================================================================


class TestLongBenchBatch:
    """测试 LongBenchBatch 数据加载器"""

    def test_import(self):
        """测试导入"""
        from sage.libs.foundation.io import LongBenchBatch

        assert LongBenchBatch is not None

    def test_init_requires_config(self):
        """测试必须提供 config"""
        from sage.libs.foundation.io import LongBenchBatch

        with pytest.raises(ValueError, match="config is required"):
            LongBenchBatch(config=None)

    def test_init_requires_hf_dataset_name(self):
        """测试必须提供 hf_dataset_name"""
        from sage.libs.foundation.io import LongBenchBatch

        with pytest.raises(KeyError):
            LongBenchBatch(config={"hf_split": "test"})

    def test_parse_dataset_name(self):
        """测试数据集名称解析"""
        from sage.libs.foundation.io import LongBenchBatch

        # 标准版
        batch = LongBenchBatch(
            config={
                "hf_dataset_name": "THUDM/LongBench",
                "hf_dataset_config": "hotpotqa",
            }
        )
        assert batch._dataset_name == "hotpotqa"
        assert batch._is_longbench_e is False

        # LongBench-E 版本
        batch_e = LongBenchBatch(
            config={
                "hf_dataset_name": "THUDM/LongBench",
                "hf_dataset_config": "hotpotqa_e",
            }
        )
        assert batch_e._dataset_name == "hotpotqa"
        assert batch_e._is_longbench_e is True

    def test_transform_example(self):
        """测试字段转换"""
        from sage.libs.foundation.io import LongBenchBatch

        batch = LongBenchBatch(
            config={
                "hf_dataset_name": "THUDM/LongBench",
                "hf_dataset_config": "hotpotqa",
            }
        )

        # 模拟 LongBench 原始数据
        raw_example = {
            "input": "What is the capital of France?",
            "context": "Paris is the capital and most populous city of France...",
            "answers": ["Paris"],
            "all_classes": None,
            "length": 1500,
        }

        result = batch._transform_example(raw_example)

        # 验证 SAGE RAG 标准字段
        assert result["query"] == "What is the capital of France?"
        assert result["context"] == "Paris is the capital and most populous city of France..."
        assert result["references"] == ["Paris"]
        assert result["retrieval_results"] == []  # LongBench 跳过检索

        # 验证 LongBench 专用字段
        assert result["_dataset"] == "hotpotqa"
        assert result["_is_longbench_e"] is False
        assert result["length"] == 1500


# =============================================================================
# Test LongBenchPromptor
# =============================================================================


class TestLongBenchPromptor:
    """测试 LongBenchPromptor"""

    def test_import(self):
        """测试导入"""
        from sage.middleware.operators.rag import LongBenchPromptor

        assert LongBenchPromptor is not None

    def test_init(self):
        """测试初始化"""
        from sage.middleware.operators.rag import LongBenchPromptor

        promptor = LongBenchPromptor(config={"max_input_tokens": 4096})
        assert promptor.max_input_tokens == 4096

    def test_get_prompt_template(self):
        """测试获取 prompt 模板（静态方法）"""
        from sage.middleware.operators.rag import LongBenchPromptor

        # 测试已知数据集
        template = LongBenchPromptor.get_prompt_template("hotpotqa")
        assert "Answer the question based on the given passages" in template

        # 测试未知数据集（应返回默认模板）
        default_template = LongBenchPromptor.get_prompt_template("unknown_dataset")
        assert "{context}" in default_template
        assert "{input}" in default_template

    def test_build_prompt(self):
        """测试构建 prompt"""
        from sage.middleware.operators.rag import LongBenchPromptor

        promptor = LongBenchPromptor(config={})

        data = {
            "query": "What is 2+2?",
            "context": "Basic arithmetic: 2+2=4",
            "_dataset": "hotpotqa",
        }

        # execute 返回 [data, prompt]
        result = promptor.execute(data)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == data  # 原始数据
        assert isinstance(result[1], str)  # prompt 字符串
        assert "2+2" in result[1] or "What is" in result[1]

    def test_get_max_gen_length(self):
        """测试获取最大生成长度（静态方法）"""
        from sage.middleware.operators.rag import LongBenchPromptor

        # QA 任务应该是 32
        assert LongBenchPromptor.get_max_gen_length("hotpotqa") == 32
        # 摘要任务应该是 512
        assert LongBenchPromptor.get_max_gen_length("multi_news") == 512
        # 未知数据集应该是默认值 128
        assert LongBenchPromptor.get_max_gen_length("unknown") == 128


# =============================================================================
# Test LongBenchEvaluator
# =============================================================================


class TestLongBenchEvaluator:
    """测试 LongBenchEvaluator"""

    def test_import(self):
        """测试导入"""
        from sage.middleware.operators.rag import LongBenchEvaluator

        assert LongBenchEvaluator is not None

    def test_init(self):
        """测试初始化"""
        from sage.middleware.operators.rag import LongBenchEvaluator

        evaluator = LongBenchEvaluator(config={"longbench_e_buckets": True})
        assert evaluator.longbench_e_buckets is True

    def test_qa_f1_score(self):
        """测试 QA F1 分数计算"""
        from sage.middleware.operators.rag.evaluate import longbench_qa_f1_score

        # 完全匹配
        score = longbench_qa_f1_score("Paris", "Paris")
        assert score == 1.0

        # 部分匹配
        score = longbench_qa_f1_score("The capital is Paris", "Paris")
        assert 0 < score < 1

        # 不匹配
        score = longbench_qa_f1_score("London", "Paris")
        assert score == 0.0

    def test_rouge_score(self):
        """测试 ROUGE 分数计算"""
        from sage.middleware.operators.rag.evaluate import longbench_rouge_score

        # 相同文本（允许浮点精度误差）
        score = longbench_rouge_score(
            "The quick brown fox jumps over the lazy dog",
            "The quick brown fox jumps over the lazy dog",
        )
        assert score > 0.99  # 接近 1.0

        # 部分重叠
        score = longbench_rouge_score(
            "The quick brown fox",
            "The quick brown fox jumps over the lazy dog",
        )
        assert 0 < score < 1

    def test_classification_score(self):
        """测试分类分数计算"""
        from sage.middleware.operators.rag.evaluate import longbench_classification_score

        all_classes = ["positive", "negative", "neutral"]

        # 完全匹配（使用 keyword argument）
        score = longbench_classification_score("positive", "positive", all_classes=all_classes)
        assert score == 1.0

        # 不匹配
        score = longbench_classification_score("something", "positive", all_classes=all_classes)
        assert score == 0.0

    def test_count_score(self):
        """测试计数分数计算"""
        from sage.middleware.operators.rag.evaluate import longbench_count_score

        # 完全正确
        score = longbench_count_score("5", "5")
        assert score == 1.0

        # 错误
        score = longbench_count_score("5", "10")
        assert score == 0.0

    def test_retrieval_score(self):
        """测试检索分数计算"""
        from sage.middleware.operators.rag.evaluate import longbench_retrieval_score

        # 完全正确
        score = longbench_retrieval_score("Paragraph 3", "Paragraph 3")
        assert score == 1.0

        # 错误
        score = longbench_retrieval_score("Paragraph 1", "Paragraph 3")
        assert score == 0.0

    def test_evaluator_execute(self):
        """测试评估器执行"""
        from sage.middleware.operators.rag import LongBenchEvaluator

        evaluator = LongBenchEvaluator(config={})

        data = {
            "query": "What is the capital?",
            "generated": "Paris",
            "references": ["Paris", "paris"],
            "_dataset": "hotpotqa",
            "all_classes": None,
            "length": 1000,
        }

        result = evaluator.execute(data)

        assert "longbench_score" in result
        assert "longbench_score_percent" in result
        assert "longbench_metric" in result
        assert result["longbench_score"] == 1.0  # 完全匹配
        assert result["longbench_metric"] == "qa_f1"

    def test_dataset_to_metric_mapping(self):
        """测试数据集到指标的映射"""
        from sage.middleware.operators.rag.evaluate import LONGBENCH_DATASET_TO_METRIC

        # QA 类应该使用 qa_f1
        assert LONGBENCH_DATASET_TO_METRIC["hotpotqa"] == "qa_f1"
        assert LONGBENCH_DATASET_TO_METRIC["2wikimqa"] == "qa_f1"

        # 摘要类应该使用 rouge
        assert LONGBENCH_DATASET_TO_METRIC["multi_news"] == "rouge"
        assert LONGBENCH_DATASET_TO_METRIC["gov_report"] == "rouge"

        # 分类类应该使用 classification
        assert LONGBENCH_DATASET_TO_METRIC["trec"] == "classification"
        assert LONGBENCH_DATASET_TO_METRIC["lsht"] == "classification"

        # 代码类应该使用 code_sim
        assert LONGBENCH_DATASET_TO_METRIC["lcc"] == "code_sim"
        assert LONGBENCH_DATASET_TO_METRIC["repobench-p"] == "code_sim"


# =============================================================================
# Test Pipeline Integration (暂时跳过 - pipeline 文件已迁移)
# =============================================================================

# NOTE: TestLongBenchPipeline 测试类已移除，因为 benchmarks/ 目录已被删除
# 相关 pipeline 实现将在 sage-examples 或其他仓库中维护
