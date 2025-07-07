import pytest
from sage_common_funs.rag.promptor import QAPromptor
from sage_core.api.tuple import Data
@pytest.fixture
def config():
    return {}

# sage_tests/function_tests/rag_tests/prompt_test.py
def test_qapromptor_with_corpus(config):
    promptor = QAPromptor(config)
    input_data = Data(("What is AI?", ["AI is the field of study focused on making machines intelligent."]))
    result = promptor.execute(input_data)
    
    # 适应 promptor 返回的 Data([query, prompt]) 格式
    assert isinstance(result.data, list)
    assert len(result.data) == 2
    
    query, prompt = result.data  # 解包 [query, prompt]
    
    # 验证 query 部分
    assert query == "What is AI?"
    
    # 验证 prompt 部分（应该是消息数组）
    assert isinstance(prompt, list)
    assert len(prompt) == 2
    assert prompt[0]["role"] == "system"
    assert prompt[1]["role"] == "user"
    assert "AI is the field of study" in prompt[0]["content"]


def test_qapromptor_without_corpus(config):
    promptor = QAPromptor(config)
    input_data = Data("What is AI?")
    result = promptor.execute(input_data)
    
    # 适应 promptor 返回的 Data([query, prompt]) 格式
    assert isinstance(result.data, list)
    assert len(result.data) == 2
    
    query, prompt = result.data  # 解包 [query, prompt]
    
    # 验证 query 部分
    assert query == "What is AI?"
    
    # 验证 prompt 部分（应该是消息数组）
    assert isinstance(prompt, list)
    assert len(prompt) == 2
    assert prompt[0]["role"] == "system"
    assert prompt[1]["role"] == "user"
    assert "You are a helpful AI assistant" in prompt[0]["content"] or "intelligent assistant" in prompt[0]["content"]