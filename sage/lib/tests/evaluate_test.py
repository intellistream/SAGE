import pytest

from sage.lib.rag.evaluate import (
    F1Evaluate, BertRecallEvaluate, RougeLEvaluate, BRSEvaluate
)

@pytest.fixture
def test_data():
    """准备测试数据，格式与实际使用的格式匹配"""
    return {
        "references": ["The cat sits on the mat."],
        "generated": "A cat is sitting on a mat."
    }

@pytest.fixture
def config():
    return {}

def test_f1_evaluate(config, test_data):
    evaluator = F1Evaluate(config)
    
    # 测试内部的 _f1_score 方法
    score = evaluator._f1_score(test_data["generated"], test_data["references"][0])
    assert 0 <= score <= 1
    
    # 测试 execute 方法
    result = evaluator.execute(test_data)
    assert result == test_data  # execute 方法应该返回原始数据

def test_bert_recall(config, test_data):
    evaluator = BertRecallEvaluate(config)
    
    # 测试 execute 方法
    result = evaluator.execute(test_data)
    assert result == test_data  # execute 方法应该返回原始数据

def test_rouge_l(config, test_data):
    evaluator = RougeLEvaluate(config)
    
    # 测试 execute 方法
    result = evaluator.execute(test_data)
    assert result == test_data  # execute 方法应该返回原始数据

def test_brs(config, test_data):
    evaluator = BRSEvaluate(config)
    
    # 测试 execute 方法
    result = evaluator.execute(test_data)
    assert result == test_data  # execute 方法应该返回原始数据

def test_f1_evaluate_with_multiple_references():
    """测试多个参考答案的情况"""
    evaluator = F1Evaluate({})
    test_data = {
        "references": [
            "The cat sits on the mat.",
            "A cat is on the mat.",
            "The feline sits on the rug."
        ],
        "generated": "A cat is sitting on a mat."
    }
    
    result = evaluator.execute(test_data)
    assert result == test_data

def test_f1_evaluate_empty_references():
    """测试空参考答案的情况"""
    evaluator = F1Evaluate({})
    test_data = {
        "references": [],
        "generated": "A cat is sitting on a mat."
    }
    
    result = evaluator.execute(test_data)
    assert result == test_data

def test_f1_evaluate_no_generated():
    """测试没有生成文本的情况"""
    evaluator = F1Evaluate({})
    test_data = {
        "references": ["The cat sits on the mat."],
        "generated": ""
    }
    
    result = evaluator.execute(test_data)
    assert result == test_data

def test_f1_score_calculation():
    """测试F1分数计算的正确性"""
    evaluator = F1Evaluate({})
    
    # 完全匹配
    score = evaluator._f1_score("hello world", "hello world")
    assert score == 1.0
    
    # 完全不匹配
    score = evaluator._f1_score("hello world", "foo bar")
    assert score == 0.0
    
    # 部分匹配
    score = evaluator._f1_score("hello world", "hello")
    assert 0 < score < 1

def test_recall_calculation():
    """测试RecallEvaluate类"""
    from sage.lib.rag.evaluate import RecallEvaluate
    
    evaluator = RecallEvaluate({})
    test_data = {
        "references": ["The cat sits on the mat."],
        "generated": "A cat is sitting on a mat."
    }
    
    result = evaluator.execute(test_data)
    assert result == test_data
    
    # 测试内部方法
    score = evaluator._recall("hello world", "hello")
    assert score == 1.0  # 所有参考词汇都在预测中

def test_accuracy_evaluate():
    """测试AccuracyEvaluate类"""
    from sage.lib.rag.evaluate import AccuracyEvaluate
    
    evaluator = AccuracyEvaluate({})
    
    # 完全匹配
    test_data = {
        "references": ["The cat sits on the mat."],
        "generated": "The cat sits on the mat."
    }
    result = evaluator.execute(test_data)
    assert result == test_data
    
    # 不匹配
    test_data = {
        "references": ["The cat sits on the mat."],
        "generated": "A dog runs in the park."
    }
    result = evaluator.execute(test_data)
    assert result == test_data