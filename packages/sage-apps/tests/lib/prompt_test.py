
import pytest

from sage.apps.libs.rag.promptor import QAPromptor

@pytest.fixture
def config():
    return {}

# sage_tests/function_tests/rag_tests/prompt_test.py
def test_qapromptor_with_corpus(config):
    promptor = QAPromptor(config)
    input_data = ("What is AI?", ["AI is the field of study focused on making machines intelligent."])
    result = promptor.execute(input_data)
    query,prompt = result
    assert prompt[0]["role"] == "system"
    assert "Relevant corpus" in prompt[0]["content"]
    assert "AI is the field" in prompt[0]["content"]
    assert prompt[1]["content"] == "Question: What is AI?"

def test_qapromptor_without_corpus(config):
    promptor = QAPromptor(config)
    input_data = "What is AI?"
    result = promptor.execute(input_data)
    query,prompt = result
    assert "You are a helpful AI assistant" in prompt[0]["content"]
    assert prompt[1]["content"] == "Question: What is AI?"
