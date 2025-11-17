"""
测试 SAGE Kernel 集成
验证 gateway 能够调用真实的 LLM 后端
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from sage.gateway.adapters.openai import (
    ChatCompletionRequest,
    ChatMessage,
    OpenAIAdapter,
)


@pytest.mark.asyncio
class TestKernelIntegration:
    """测试 Kernel 集成"""

    async def test_execute_with_mock_llm(self):
        """测试使用 mock LLM 客户端执行"""
        adapter = OpenAIAdapter()

        # 创建请求
        request = ChatCompletionRequest(
            model="sage-default",
            messages=[
                ChatMessage(role="user", content="Hello, how are you?"),
            ],
            session_id="test-session",
        )

        # Mock OpenAIClient (需要patch导入它的模块，而不是定义它的模块)
        with patch("sage.libs.integrations.openaiclient.OpenAIClient") as MockClient:
            mock_client = MagicMock()
            mock_client.generate.return_value = "I'm doing well, thank you!"
            MockClient.return_value = mock_client

            # Mock 环境变量
            test_api_key = "test-key"  # pragma: allowlist secret
            with patch.dict(os.environ, {"SAGE_CHAT_API_KEY": test_api_key}):
                # 获取会话
                session = adapter.session_manager.get_or_create(request.session_id)

                # 执行
                response = await adapter._execute_sage_pipeline(request, session)

                # 验证
                assert response == "I'm doing well, thank you!"
                mock_client.generate.assert_called_once()

                # 验证调用参数
                call_args = mock_client.generate.call_args
                messages = call_args[0][0]
                assert len(messages) == 1
                assert messages[0]["role"] == "user"
                assert messages[0]["content"] == "Hello, how are you?"

    async def test_execute_without_api_key_dev_mode(self):
        """测试没有 API key 时进入开发模式"""
        adapter = OpenAIAdapter()

        request = ChatCompletionRequest(
            model="sage-default",
            messages=[
                ChatMessage(role="user", content="Test message"),
            ],
            session_id="test-session",
        )

        # 确保没有 API key
        with patch.dict(os.environ, {}, clear=True):
            session = adapter.session_manager.get_or_create(request.session_id)
            response = await adapter._execute_sage_pipeline(request, session)

            # 验证返回开发模式响应
            assert "[开发模式]" in response
            assert "Test message" in response
            assert "SAGE_CHAT_API_KEY" in response

    async def test_execute_with_multi_turn_conversation(self):
        """测试多轮对话"""
        adapter = OpenAIAdapter()

        # 多轮消息
        request = ChatCompletionRequest(
            model="sage-default",
            messages=[
                ChatMessage(role="user", content="What's the weather?"),
                ChatMessage(role="assistant", content="It's sunny."),
                ChatMessage(role="user", content="Should I bring an umbrella?"),
            ],
            session_id="test-session",
        )

        with patch("sage.libs.integrations.openaiclient.OpenAIClient") as MockClient:
            mock_client = MagicMock()
            mock_client.generate.return_value = "No, you don't need an umbrella today."
            MockClient.return_value = mock_client

            test_api_key = "test-key"  # pragma: allowlist secret
            with patch.dict(os.environ, {"SAGE_CHAT_API_KEY": test_api_key}):
                session = adapter.session_manager.get_or_create(request.session_id)
                response = await adapter._execute_sage_pipeline(request, session)

                assert response == "No, you don't need an umbrella today."

                # 验证传递了完整的对话历史
                call_args = mock_client.generate.call_args
                messages = call_args[0][0]
                assert len(messages) == 3
                assert messages[0]["content"] == "What's the weather?"
                assert messages[1]["content"] == "It's sunny."
                assert messages[2]["content"] == "Should I bring an umbrella?"

    async def test_execute_with_error_handling(self):
        """测试错误处理"""
        adapter = OpenAIAdapter()

        request = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="Test")],
            session_id="test-session",
        )

        with patch("sage.libs.integrations.openaiclient.OpenAIClient") as MockClient:
            # 模拟 LLM 调用失败
            MockClient.side_effect = Exception("Network error")

            test_api_key = "test-key"  # pragma: allowlist secret
            with patch.dict(os.environ, {"SAGE_CHAT_API_KEY": test_api_key}):
                session = adapter.session_manager.get_or_create(request.session_id)
                response = await adapter._execute_sage_pipeline(request, session)

                # 验证返回友好的错误信息
                assert "抱歉" in response or "错误" in response
                assert "Network error" in response

    async def test_llm_config_from_environment(self):
        """测试从环境变量读取 LLM 配置"""
        adapter = OpenAIAdapter()

        request = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="Test")],
            session_id="test-session",
        )

        custom_env = {
            "SAGE_CHAT_MODEL": "custom-model",
            "SAGE_CHAT_BASE_URL": "http://custom-url:8000/v1",
            "SAGE_CHAT_API_KEY": "custom-key",  # pragma: allowlist secret
        }

        with patch("sage.libs.integrations.openaiclient.OpenAIClient") as MockClient:
            mock_client = MagicMock()
            mock_client.generate.return_value = "Response"
            MockClient.return_value = mock_client

            with patch.dict(os.environ, custom_env):
                session = adapter.session_manager.get_or_create(request.session_id)
                await adapter._execute_sage_pipeline(request, session)

                # 验证使用了自定义配置
                MockClient.assert_called_once_with(
                    model_name="custom-model",
                    base_url="http://custom-url:8000/v1",
                    api_key="custom-key",  # pragma: allowlist secret
                    seed=42,
                )
