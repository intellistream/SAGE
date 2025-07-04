import pytest
from sage_core.api.tuple import Data
from sage_common_funs.rag.generator import OpenAIGenerator, HFGenerator
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
    input_data = Data([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ])
    result = gen.execute(input_data)

    assert isinstance(result, Data)
    assert result.data[0] == "What is the capital of France?"

    assert "Paris" in result.data[1]


