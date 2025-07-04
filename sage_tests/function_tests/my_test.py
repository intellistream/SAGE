
import pytest
from sage_common_funs.rag.promptor import QAPromptor
from sage_core.api.tuple import Data
import sys
print(sys.path)
@pytest.fixture
def config():
    return {}

def test_qapromptor_with_corpus(config):
    promptor = QAPromptor(config)
    input_data = Data(("What is AI?", ["AI is the field of study focused on making machines intelligent."]))
    result = promptor.execute(input_data)

    assert result.data[0]["role"] == "system"
    assert "Relevant corpus" in result.data[0]["content"]
    assert "AI is the field" in result.data[0]["content"]
    assert result.data[1]["content"] == "Question: What is AI?"

def test_qapromptor_without_corpus(config):
    promptor = QAPromptor(config)
    input_data = Data("What is AI?")
    result = promptor.execute(input_data)

    assert "You are a helpful AI assistant" in result.data[0]["content"]
    assert result.data[1]["content"] == "Question: What is AI?"

from sage_core.api.tuple import Data
from sage_common_funs.rag.generator import OpenAIGenerator, HFGenerator

@pytest.fixture
def config_openai():
    return {
        "method": "openai",
        "model_name": "qwen-turbo-0919",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-b21a67cf99d14ead9d1c5bf8c2eb90ef",
        "seed": 42,
    }

@pytest.fixture
def config_hf():
    return {
        "method": "hf",
        "model_name": "meta-llama/Llama-2-13b-chat-hf"
    }

def test_openai_generator(config_openai):
    gen = OpenAIGenerator(config_openai)
    input_data = Data([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ])
    result = gen.execute(input_data)

    assert isinstance(result, Data)
    assert result.data[0] == "What is the capital of France?"
    assert "Paris" in result.data[1]

def test_hf_generator(config_hf):
    gen = HFGenerator(config_hf)
    input_data = Data([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ])
    result = gen.execute(input_data)

    assert isinstance(result, Data)
    # assert result.data[0] == "What is the capital of France?"
    assert "Paris" in result.data[1]

