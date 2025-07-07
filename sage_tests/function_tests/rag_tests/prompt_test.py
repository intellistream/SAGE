import pytest
from sage_common_funs.rag.promptor import QAPromptor
from sage_core.api.tuple import Data
@pytest.fixture
def config():
    return {}

def test_qapromptor_with_corpus(config):
    promptor = QAPromptor(config)
    input_data = Data(("What is AI?", ["AI is the field of study focused on making machines intelligent."]))
    result = promptor.execute(input_data)
    query,prompt = result.data
    assert prompt[0]["role"] == "system"
    assert "Relevant corpus" in prompt[0]["content"]
    assert "AI is the field" in prompt[0]["content"]
    assert prompt[1]["content"] == "Question: What is AI?"

def test_qapromptor_without_corpus(config):
    promptor = QAPromptor(config)
    input_data = Data("What is AI?")
    result = promptor.execute(input_data)
    query,prompt = result.data
    assert "You are a helpful AI assistant" in prompt[0]["content"]
    assert prompt[1]["content"] == "Question: What is AI?"
