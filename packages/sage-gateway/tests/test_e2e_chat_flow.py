"""
End-to-end integration tests for the complete chat flow.
Tests gateway, kernel integration, session management, and NeuroMem storage.
"""

import tempfile

import pytest

from sage.gateway.adapters import ChatCompletionRequest, ChatMessage, OpenAIAdapter
from sage.gateway.session.neuromem_storage import NeuroMemSessionStorage


class TestE2EChatFlow:
    """Test complete chat flow from request to response"""

    @pytest.mark.asyncio
    async def test_complete_chat_flow_dev_mode(self, monkeypatch):
        """Test full chat flow in development mode (no API key)"""
        # Clear API keys to use dev mode
        monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
        monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

        adapter = OpenAIAdapter()

        # Create a chat request
        request = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="What is 2+2?")],
            session_id="e2e-test-session",
            stream=False,
        )

        # Execute the chat
        response = await adapter.chat_completions(request)

        # Verify response structure
        assert response.model == "sage-default"
        assert len(response.choices) == 1
        assert response.choices[0].message.role == "assistant"
        assert len(response.choices[0].message.content) > 0

        # Verify session was created and persisted
        session = adapter.session_manager.get("e2e-test-session")
        assert session is not None
        assert len(session.messages) >= 2  # user + assistant messages

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, monkeypatch):
        """Test multi-turn conversation with context"""
        monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
        monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

        adapter = OpenAIAdapter()
        session_id = "multi-turn-test"

        # First turn
        request1 = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="My name is Alice")],
            session_id=session_id,
            stream=False,
        )
        await adapter.chat_completions(request1)

        # Second turn
        request2 = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="What is my name?")],
            session_id=session_id,
            stream=False,
        )
        await adapter.chat_completions(request2)

        # Verify session has both turns
        session = adapter.session_manager.get(session_id)
        assert len(session.messages) >= 4  # 2 user messages + 2 assistant messages

        # Verify messages are in correct order
        messages = session.messages
        assert messages[0].role == "user"
        assert "Alice" in messages[0].content
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"
        assert "name" in messages[2].content
        assert messages[3].role == "assistant"

    @pytest.mark.asyncio
    async def test_streaming_chat_flow(self, monkeypatch):
        """Test streaming chat responses"""
        monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
        monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

        adapter = OpenAIAdapter()

        request = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="Count to 5")],
            stream=True,
        )

        response = await adapter.chat_completions(request)

        # Collect stream chunks
        chunks = []
        async for chunk in response:
            chunks.append(chunk)

        # Verify streaming format
        assert len(chunks) > 0
        assert any("data:" in chunk for chunk in chunks)
        assert any("[DONE]" in chunk for chunk in chunks)

    @pytest.mark.asyncio
    async def test_neuromem_backend_config(self, monkeypatch):
        """Test that NeuroMem backend can be configured via environment"""
        # This test validates NeuroMem backend configuration works
        # Note: Due to singleton pattern, we test storage creation directly

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create NeuroMem storage directly
            storage = NeuroMemSessionStorage(data_dir=tmpdir)

            # Verify it implements required methods
            assert hasattr(storage, "save")
            assert hasattr(storage, "load")
            assert hasattr(storage, "clear")
            assert hasattr(storage, "get_stats")

            # Test save/load cycle
            test_data = {
                "id": "test-session",
                "messages": [{"role": "user", "content": "test"}],
                "created_at": "2025-11-17T00:00:00",
                "last_active": "2025-11-17T00:00:00",
                "metadata": {},
            }

            storage.save([test_data])
            loaded = list(storage.load())
            assert len(loaded) == 1
            assert loaded[0]["id"] == "test-session"

    @pytest.mark.asyncio
    async def test_session_persistence_across_adapters(self, monkeypatch):
        """Test that sessions persist across different adapter instances"""
        monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
        monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

        session_id = "persistence-test"

        # First adapter creates session
        adapter1 = OpenAIAdapter()
        request1 = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="Remember: blue")],
            session_id=session_id,
            stream=False,
        )
        await adapter1.chat_completions(request1)

        # Second adapter should see the same session
        adapter2 = OpenAIAdapter()
        request2 = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="What color?")],
            session_id=session_id,
            stream=False,
        )
        await adapter2.chat_completions(request2)

        # Verify both adapters see the same session
        session1 = adapter1.session_manager.get(session_id)
        session2 = adapter2.session_manager.get(session_id)

        assert len(session1.messages) == len(session2.messages)
        assert len(session1.messages) >= 4  # 2 turns × 2 messages

    @pytest.mark.asyncio
    async def test_error_handling_in_chat_flow(self, monkeypatch):
        """Test error handling in chat flow"""
        # Set invalid API configuration to trigger error
        monkeypatch.setenv("SAGE_CHAT_API_KEY", "invalid-key-123")
        monkeypatch.setenv("SAGE_CHAT_BASE_URL", "http://invalid-url:9999/v1")

        adapter = OpenAIAdapter()

        request = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="This will fail")],
            stream=False,
        )

        # Should not raise exception, but return error message
        response = await adapter.chat_completions(request)

        # Verify error is handled gracefully
        assert response.choices[0].message.role == "assistant"
        assert (
            "错误" in response.choices[0].message.content
            or "error" in response.choices[0].message.content.lower()
        )

    @pytest.mark.asyncio
    async def test_session_stats_accuracy(self, monkeypatch):
        """Test session statistics are accurate"""
        monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
        monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

        adapter = OpenAIAdapter()
        session_id = "stats-test"

        # Send 3 messages
        for i in range(3):
            request = ChatCompletionRequest(
                model="sage-default",
                messages=[ChatMessage(role="user", content=f"Message {i}")],
                session_id=session_id,
                stream=False,
            )
            await adapter.chat_completions(request)

        # Check stats
        stats = adapter.session_manager.get_stats()
        assert "total_sessions" in stats
        assert "total_messages" in stats
        assert stats["total_messages"] >= 6  # 3 user + 3 assistant

        # Verify session exists and has correct message count
        session = adapter.session_manager.get(session_id)
        assert len(session.messages) >= 6
