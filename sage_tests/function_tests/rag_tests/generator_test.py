import pytest
from sage_core.api.tuple import Data
from sage_common_funs.rag.generator import OpenAIGenerator,OpenAIGeneratorWithHistory
from dotenv import load_dotenv
import os
load_dotenv(override=False)
api_key = os.environ.get("ALIBABA_API_KEY")
@pytest.fixture
def config_openai():
    return {
        "method": "openai",
        "model_name": "qwen-turbo-0919",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": api_key,
        "seed": 42,
    }


def test_openai_generator(config_openai):
    gen = OpenAIGenerator(config_openai)
    query = "What is the capital of France?"
    input_data = Data([query, [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]])
    result = gen.execute(input_data)

    assert isinstance(result, Data)
    assert result.data[0] == "What is the capital of France?"

    assert "Paris" in result.data[1]



def test_openai_generator_history_state(config_openai):
    gen = OpenAIGeneratorWithHistory(config_openai)

    # 第一次用户提问
    query1 = "What is the capital of France?"
    input_data1 = Data([query1, [
        {"role": "user", "content": query1}
    ]])
    gen.execute(input_data1)

    # 第二次用户提问
    query2 = "Which river flows through it?"
    input_data2 = Data([query2, [
        {"role": "user", "content": query2}
    ]])
    gen.execute(input_data2)

    # 检查状态中的历史是否更新正确
    history = gen.dialogue_history

    assert len(history) == 4  # 2轮对话 = 2 user + 2 assistant
    assert history[0]["role"] == "user"
    assert history[0]["content"] == query1
    assert history[2]["role"] == "user"
    assert history[2]["content"] == query2
    assert history[1]["role"] == "assistant"
    assert isinstance(history[1]["content"], str)
    assert history[3]["role"] == "assistant"
