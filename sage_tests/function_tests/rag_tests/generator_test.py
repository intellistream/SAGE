import pytest

from sage_libs.rag import OpenAIGenerator,OpenAIGeneratorWithHistory
from dotenv import load_dotenv
import os
import time
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

@pytest.fixture
def ctx(tmp_path):
    """
    模拟 RuntimeContext，只要提供 name、env_name、session_folder、create_logger() 即可。
    """
    class Ctx:
        def __init__(self, name: str, folder: str):
            self.name = name
            self.env_name = "test"
            self.session_folder = folder

    folder = tmp_path / "session"
    folder.mkdir()
    return Ctx(name="gen1", folder=str(folder))

def test_openai_generator(config_openai):
    gen = OpenAIGenerator(config_openai)
    query = "What is the capital of France?"
    input_data = [query, [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]]
    result = gen.execute(input_data)
    assert result[0] == "What is the capital of France?"

    assert "Paris" in result[1]



def test_openai_generator_history_state(config_openai, ctx):
    gen = OpenAIGeneratorWithHistory(config_openai, ctx = ctx)

    # 第一次用户提问
    query1 = "What is the capital of France?"
    input_data1 = [query1, [{"role": "user", "content": query1}]]
    gen.execute(input_data1)
    time.sleep(5)

    # 第二次用户提问
    query2 = "Which river flows through it?"
    input_data2 = [query2, [{"role": "user", "content": query2}]]
    gen.execute(input_data2)

    # 检查内存中状态是否更新正确
    history = gen.dialogue_history
    assert len(history) == 4  # 2 轮对话 = 2 user + 2 assistant
    assert history[0]["role"] == "user"
    assert history[0]["content"] == query1
    assert history[2]["role"] == "user"
    assert history[2]["content"] == query2
    assert history[1]["role"] == "assistant"
    assert isinstance(history[1]["content"], str)
    assert history[3]["role"] == "assistant"

    gen.save_state()

    gen2 = OpenAIGeneratorWithHistory(config_openai, ctx = ctx)
    history2 = gen2.dialogue_history
    
    assert history2 == history
