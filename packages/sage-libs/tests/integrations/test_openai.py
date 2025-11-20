"""
Tests for OpenAI integration module

Tests cover:
- Client initialization with different base URLs
- Message format handling (dict and list)
- Chat completion generation
- Streaming responses
- Error handling
"""

from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestOpenAIClientInitialization:
    """Test OpenAI client initialization"""

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_init_with_qwen_max(self, mock_openai_class):
        """测试使用Qwen Max模型初始化"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="qwen-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="test-key-123",  # pragma: allowlist secret
        )

        assert client.model_name == "qwen-max"
        assert client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert client.api_key == "test-key-123"  # pragma: allowlist secret
        mock_openai_class.assert_called_once_with(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="test-key-123",  # pragma: allowlist secret
        )

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_init_with_ollama(self, mock_openai_class):
        """测试使用Ollama本地模型初始化"""
        from sage.libs.integrations.openai import OpenAIClient

        client = OpenAIClient(
            model_name="llama3.1:8b",
            base_url="http://localhost:11434/v1",
            api_key="empty",  # pragma: allowlist secret
        )

        assert client.model_name == "llama3.1:8b"
        assert client.base_url == "http://localhost:11434/v1"

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_init_with_vllm(self, mock_openai_class):
        """测试使用vLLM初始化"""
        from sage.libs.integrations.openai import OpenAIClient

        client = OpenAIClient(
            model_name="meta-llama/Llama-2-13b-chat-hf",
            base_url="http://localhost:8000/v1",
            api_key="empty",  # pragma: allowlist secret
        )

        assert client.model_name == "meta-llama/Llama-2-13b-chat-hf"

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_init_with_seed(self, mock_openai_class):
        """测试带随机种子初始化"""
        from sage.libs.integrations.openai import OpenAIClient

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
            seed=42,
        )

        assert client.seed == 42


@pytest.mark.unit
class TestOpenAIClientGenerate:
    """Test chat completion generation"""

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_with_dict_message(self, mock_openai_class):
        """测试使用字典格式消息生成"""
        from sage.libs.integrations.openai import OpenAIClient

        # Mock OpenAI client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Hello! How can I help you?"
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        # Test with dict message
        message = {"role": "user", "content": "Hello"}
        result = client.generate(message)

        # Verify
        assert result == "Hello! How can I help you?"
        mock_client.chat.completions.create.assert_called_once()

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"
        assert call_kwargs["messages"] == [message]

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_with_list_messages(self, mock_openai_class):
        """测试使用列表格式消息生成"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "The answer is 42"
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        # Test with list of messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the answer to everything?"},
        ]

        result = client.generate(messages)

        assert result == "The answer is 42"

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == messages

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_with_custom_parameters(self, mock_openai_class):
        """测试使用自定义参数生成"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Generated text"
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        # Generate with custom parameters
        message = {"role": "user", "content": "Test"}
        _ = client.generate(message, max_tokens=500, temperature=0.7, top_p=0.9)

        # Verify parameters were passed
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["top_p"] == 0.9

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_with_default_max_tokens(self, mock_openai_class):
        """测试默认max_tokens参数"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Response"
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        message = {"role": "user", "content": "Test"}
        client.generate(message)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        # Default should be 3000
        assert call_kwargs["max_tokens"] == 3000


@pytest.mark.unit
class TestOpenAIClientStreaming:
    """Test streaming responses"""

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_streaming_mode(self, mock_openai_class):
        """测试流式生成模式"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Mock streaming response
        mock_stream = Mock()
        mock_client.chat.completions.create.return_value = mock_stream

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        # Request streaming
        message = {"role": "user", "content": "Tell me a story"}
        result = client.generate(message, stream=True)

        # Should return the stream object directly
        assert result == mock_stream

        # Note: stream parameter might not be passed based on current implementation
        # but the function should return the stream


@pytest.mark.unit
class TestOpenAIClientErrorHandling:
    """Test error handling"""

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_with_invalid_message_type(self, mock_openai_class):
        """测试无效消息类型的错误处理"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        # Invalid message type (string instead of dict/list)
        with pytest.raises(RuntimeError, match="Response generation failed"):
            client.generate("This is not a valid message format")

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_generate_api_error(self, mock_openai_class):
        """测试API错误"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Simulate API error
        mock_client.chat.completions.create.side_effect = Exception(
            "API Error: Rate limit exceeded"
        )

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        message = {"role": "user", "content": "Test"}

        with pytest.raises(Exception, match="API Error: Rate limit exceeded"):
            client.generate(message)


@pytest.mark.integration
class TestOpenAIClientIntegration:
    """Integration tests"""

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_multi_turn_conversation(self, mock_openai_class):
        """测试多轮对话"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Mock responses for each turn
        responses = ["Hello!", "I'm doing well, thanks!", "Goodbye!"]
        mock_choices = []
        for resp in responses:
            mock_choice = Mock()
            mock_choice.message.content = resp
            mock_choices.append(mock_choice)

        call_count = 0

        def mock_create(**kwargs):
            nonlocal call_count
            mock_response = Mock()
            mock_response.choices = [mock_choices[call_count]]
            call_count += 1
            return mock_response

        mock_client.chat.completions.create.side_effect = mock_create

        client = OpenAIClient(
            model_name="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        # Simulate conversation
        conversation = []

        # Turn 1
        conversation.append({"role": "user", "content": "Hi!"})
        response1 = client.generate(conversation.copy())
        assert response1 == "Hello!"
        conversation.append({"role": "assistant", "content": response1})

        # Turn 2
        conversation.append({"role": "user", "content": "How are you?"})
        response2 = client.generate(conversation.copy())
        assert response2 == "I'm doing well, thanks!"
        conversation.append({"role": "assistant", "content": response2})

        # Turn 3
        conversation.append({"role": "user", "content": "Bye!"})
        response3 = client.generate(conversation.copy())
        assert response3 == "Goodbye!"

        assert mock_client.chat.completions.create.call_count == 3
