import pytest
from unittest.mock import patch, Mock

from sage.lib.rag.generator import OpenAIGenerator,OpenAIGeneratorWithHistory
from dotenv import load_dotenv
import os
import time

import test
load_dotenv(override=False)

@pytest.fixture
def config_openai():
    return {
        "method": "openai",
        "model_name": "meta-llama/Llama-2-13b-chat-hf",
        "base_url": "http://localhost:8000/v1",
        "api_key": "token-abc123",  # 使用配置中的固定token
        "seed": 42,
        "max_tokens": 3000
    }

@pytest.fixture
def config_vllm():
    """VLLM配置 - 根据config.yaml中的vllm配置"""
    return {
        "method": "openai",
        "model_name": "meta-llama/Llama-2-13b-chat-hf",
        "base_url": "http://localhost:8000/v1",
        "api_key": "token-abc123",
        "seed": 42,
        "max_tokens": 3000
    }

@pytest.fixture
def config_remote():
    """远程配置 - 根据config.yaml中的remote配置"""
    return {
        "method": "openai",
        "model_name": "qwen-turbo-0919",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "",  # 空的api_key用于测试
        "seed": 42,
        "max_tokens": 3000
    }

# 

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
            self.env_base_dir = str(tmp_path)  # 添加 env_base_dir 属性

    folder = tmp_path / "session"
    folder.mkdir()
    return Ctx(name="gen1", folder=str(folder))

@patch('sage.utils.clients.openaiclient.OpenAI')
def test_openai_generator(mock_openai_class, config_openai):
    """测试OpenAI生成器基本功能"""
    # Mock OpenAI client
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # Mock chat completion response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Paris is the capital of France."
    mock_client.chat.completions.create.return_value = mock_response
    
    gen = OpenAIGenerator(config_openai)
    query = "What is the capital of France?"
    input_data = [query, [
        {"role": "system", "content": "You are a helpful assistant. Answer the question in a few words"},
        {"role": "user", "content": "What is the capital of France?"}
    ]]
    result = gen.execute(input_data)
    assert result[0] == "What is the capital of France?"
    assert "Paris" in result[1]


@patch('sage.utils.clients.openaiclient.OpenAI')
def test_openai_generator_vllm(mock_openai_class, config_vllm):
    """测试使用VLLM配置的OpenAI生成器"""
    # Mock OpenAI client
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # Mock VLLM response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Paris"
    mock_client.chat.completions.create.return_value = mock_response
    
    gen = OpenAIGenerator(config_vllm)
    query = "What is the capital of France?"
    input_data = [query, [
        {"role": "system", "content": "You are a helpful assistant. Answer the question in a few words"},
        {"role": "user", "content": "What is the capital of France?"}
    ]]
    result = gen.execute(input_data)
    assert result[0] == "What is the capital of France?"
    assert "Paris" in result[1]
    
    # 验证VLLM特定配置
    mock_openai_class.assert_called_with(
        api_key="token-abc123",
        base_url="http://localhost:8000/v1"
    )


def test_openai_generator_missing_api_key(config_remote):
    """测试缺少API key时的错误处理"""
    with pytest.raises(Exception):  # 应该抛出OpenAI API key相关的异常
        gen = OpenAIGenerator(config_remote)
        query = "What is the capital of France?"
        input_data = [query, [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "What is the capital of France?"}
        ]]
        gen.execute(input_data)