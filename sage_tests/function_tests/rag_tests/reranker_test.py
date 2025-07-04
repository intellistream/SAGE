import pytest
from unittest.mock import patch, MagicMock
from sage_core.api.tuple import Data
from sage_common_funs.rag.reranker import BGEReranker, LLMbased_Reranker
import torch

@pytest.fixture
def test_input():
    query = "What is the capital of France?"
    docs = [
        "Paris is the capital of France.",
        "Berlin is a city in Germany.",
        "The Eiffel Tower is located in Paris.",
        "France is a country in Western Europe.",
        "Madrid is the capital of Spain."
    ]
    return Data((query, docs))

@pytest.fixture
def config_bge():
    return {
        "reranker": {
            "model_name": "BAAI/bge-reranker-v2-m3",
            "top_k": 3
        }
    }

@pytest.fixture
def config_llm():
    return {
        "reranker": {
            "model_name": "BAAI/bge-reranker-v2-gemma",
            "top_k": 3
        }
    }

def mock_tokenizer_encode(pairs, **kwargs):
    # Fake tokenizer output
    return {
        "input_ids": [[1, 2, 3]] * len(pairs),
        "attention_mask": [[1, 1, 1]] * len(pairs)
    }

def mock_model_logits(*args, **kwargs):
    # Fake logits with increasing scores
    class Output:
        def __init__(self):
            self.logits = torch.tensor([[i] for i in range(5)])
    return Output()

@patch("sage_common_funs.rag.reranker.AutoTokenizer.from_pretrained")
@patch("sage_common_funs.rag.reranker.AutoModelForSequenceClassification.from_pretrained")
def test_bge_reranker(mock_model_cls, mock_tokenizer_cls, config_bge, test_input):
    # Setup mocks
    mock_tokenizer = MagicMock()
    mock_tokenizer.return_value = mock_tokenizer
    mock_tokenizer.side_effect = mock_tokenizer_encode

    mock_tokenizer_cls.return_value = mock_tokenizer

    mock_model = MagicMock()
    mock_model.return_value = mock_model
    mock_model.side_effect = mock_model_logits
    mock_model_cls.return_value = mock_model

    reranker = BGEReranker(config_bge)
    result = reranker.execute(test_input)

    assert isinstance(result, Data)
    assert result.data[0] == test_input.data[0]
    assert isinstance(result.data[1], list)
    assert len(result.data[1]) <= config_bge["reranker"]["top_k"]

@patch("sage_common_funs.rag.reranker.AutoTokenizer.from_pretrained")
@patch("sage_common_funs.rag.reranker.AutoModelForCausalLM.from_pretrained")
def test_llm_reranker(mock_model_cls, mock_tokenizer_cls, config_llm, test_input):
    # Setup tokenizer mock
    # mock tokenizer
    mock_tokenizer = MagicMock()
    mock_tokenizer.encode.return_value = [1, 2, 3]
    mock_tokenizer.pad.return_value = {
        "input_ids": torch.tensor([[1, 2, 3], [4, 5, 6]]),
        "attention_mask": torch.tensor([[1, 1, 1], [1, 1, 1]])
    }
    mock_tokenizer.__getitem__.return_value = [42]  # for yes_loc

    mock_tokenizer_cls.return_value = mock_tokenizer

    # Setup model mock
    mock_model = MagicMock()
    mock_model.return_value = mock_model
    # reranker_test.py 第 90 行左右：
    kwargs_for_model = {
        "input_ids": torch.tensor([[1, 2, 3]]),
        "attention_mask": torch.tensor([[1, 1, 1]])
    }
    mock_model(**kwargs_for_model).logits = torch.randn(2, 1000, 200)

    mock_model_cls.return_value = mock_model

    # patch inference to return fake scores
    with patch("torch.no_grad"):
        reranker = LLMbased_Reranker(config_llm)
        reranker.model = MagicMock()
        reranker.model(**kwargs_for_model).logits = torch.rand(5, 128, 500)
        reranker.yes_loc = 42
        reranker.tokenizer = mock_tokenizer
        reranker.get_inputs = MagicMock(return_value={
            "input_ids": torch.randint(0, 1000, (5, 100)),
            "attention_mask": torch.ones(5, 100)
        })


        result = reranker.execute(test_input)
        assert isinstance(result, Data)
        assert result.data[0] == test_input.data[0]
        assert isinstance(result.data[1], list)
        assert len(result.data[1]) <= config_llm["reranker"]["top_k"]
