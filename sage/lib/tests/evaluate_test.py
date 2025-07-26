import pytest

from sage_libs.rag.evaluate import (
    F1Evaluate, BertRecallEvaluate, RougeLEvaluate, BRSEvaluate
)

@pytest.fixture
def test_data():
    reference = "The cat sits on the mat."
    generated = "A cat is sitting on a mat."
    return (reference, generated)

@pytest.fixture
def config():
    return {}

def test_f1_evaluate(config, test_data):
    evaluator = F1Evaluate(config)
    score = evaluator._f1_score(test_data[1], test_data[0])
    
    assert 0 <= score <= 1

def test_bert_recall(config, test_data):
    evaluator = BertRecallEvaluate(config)
    score = evaluator.bert_recall(test_data[0], test_data[1])
    
    assert 0 <= score <= 1

def test_rouge_l(config, test_data):
    evaluator = RougeLEvaluate(config)
    score = evaluator.rouge_l(test_data[0], test_data[1])

    assert 0 <= score <= 1

def test_brs(config, test_data):
    evaluator = BRSEvaluate(config)
    score = evaluator.BRS(test_data[0], test_data[1])

    assert 0 <= score <= 1