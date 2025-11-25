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
        # Mock the RAG Pipeline Service
        with patch("sage.gateway.rag_pipeline.RAGPipelineService"):
            adapter = OpenAIAdapter()

            # Mock the pipeline process method
            adapter.rag_pipeline.process = MagicMock(
                return_value={
                    "type": "chat",
                    "content": "I'm doing well, thank you!",
                    "sources": [],
                }
            )
            adapter._pipeline_started = True

            # 创建请求
            request = ChatCompletionRequest(
                model="sage-default",
                messages=[
                    ChatMessage(role="user", content="Hello, how are you?"),
                ],
                session_id="test-session",
            )

            # 获取会话
            session = adapter.session_manager.get_or_create(request.session_id)

            # 执行
            response = await adapter._execute_sage_pipeline(request, session)

            # 验证
            assert response == "I'm doing well, thank you!"
            adapter.rag_pipeline.process.assert_called_once()

    async def test_execute_without_api_key_dev_mode(self):
        """测试没有 API key 时进入开发模式"""
        with patch("sage.gateway.rag_pipeline.RAGPipelineService"):
            adapter = OpenAIAdapter()

            # Mock pipeline to simulate not started error
            adapter.rag_pipeline.process = MagicMock(
                side_effect=RuntimeError("RAG Pipeline not started")
            )
            adapter._pipeline_started = False

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

                # 验证返回配置错误响应（因为没有API key）
                assert "[配置错误]" in response or "[开发模式]" in response

    async def test_execute_with_multi_turn_conversation(self):
        """测试多轮对话"""
        with patch("sage.gateway.rag_pipeline.RAGPipelineService"):
            adapter = OpenAIAdapter()

            # Capture the messages passed to pipeline
            captured_messages = []

            def capture_process(request_data, **kwargs):
                captured_messages.extend(request_data.get("messages", []))
                return {
                    "type": "chat",
                    "content": "No, you don't need an umbrella today.",
                    "sources": [],
                }

            adapter.rag_pipeline.process = MagicMock(side_effect=capture_process)
            adapter._pipeline_started = True

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

            session = adapter.session_manager.get_or_create(request.session_id)
            response = await adapter._execute_sage_pipeline(request, session)

            assert response == "No, you don't need an umbrella today."

            # 验证传递了完整的对话历史（至少有最后一条消息）
            assert len(captured_messages) >= 1
            assert any("umbrella" in msg.get("content", "") for msg in captured_messages)

    async def test_execute_with_error_handling(self):
        """测试错误处理"""
        with patch("sage.gateway.rag_pipeline.RAGPipelineService"):
            adapter = OpenAIAdapter()

            # 模拟 Pipeline 调用失败
            adapter.rag_pipeline.process = MagicMock(side_effect=Exception("Network error"))
            adapter._pipeline_started = True

            request = ChatCompletionRequest(
                model="sage-default",
                messages=[ChatMessage(role="user", content="Test")],
                session_id="test-session",
            )

            # Mock the fallback LLM to avoid actual API calls
            with patch("sage.common.components.sage_llm.client.IntelligentLLMClient") as MockClient:
                mock_client = MagicMock()
                mock_client.generate.return_value = "抱歉，处理请求时出错：Network error"
                MockClient.return_value = mock_client

                test_api_key = "test-key"  # pragma: allowlist secret
                with patch.dict(os.environ, {"SAGE_CHAT_API_KEY": test_api_key}):
                    session = adapter.session_manager.get_or_create(request.session_id)

                    # The error should be caught and returned as a message
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

        with patch("sage.common.components.sage_llm.client.IntelligentLLMClient") as MockClient:
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
