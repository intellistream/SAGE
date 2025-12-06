"""Unit tests for StreamHandler and SSEFormatter."""

import json
from dataclasses import dataclass
from typing import AsyncGenerator

import pytest
from starlette.responses import StreamingResponse

from sage.studio.services.stream_handler import SSEFormatter, StreamHandler, get_stream_handler


@dataclass
class MockAgentStep:
    """Mock AgentStep for testing."""

    step_id: str
    type: str
    content: str
    status: str = "completed"
    metadata: dict = None

    def to_dict(self):
        return {
            "step_id": self.step_id,
            "type": self.type,
            "content": self.content,
            "status": self.status,
            "metadata": self.metadata or {},
        }


class TestSSEFormatter:
    """Tests for SSEFormatter."""

    def test_format_event(self):
        """Test basic event formatting."""
        result = SSEFormatter.format_event("test_event", "test_data")
        assert result == "event: test_event\ndata: test_data\n\n"

    def test_format_step(self):
        """Test formatting AgentStep."""
        step = MockAgentStep(
            step_id="123", type="reasoning", content="Thinking...", metadata={"foo": "bar"}
        )
        result = SSEFormatter.format_step(step)

        assert result.startswith("event: step\n")
        assert result.endswith("\n\n")

        # Parse data part
        data_line = result.split("\n")[1]
        assert data_line.startswith("data: ")
        json_str = data_line[6:]
        data = json.loads(json_str)

        assert data["step_id"] == "123"
        assert data["type"] == "reasoning"
        assert data["content"] == "Thinking..."
        assert data["metadata"] == {"foo": "bar"}

    def test_format_text(self):
        """Test formatting text."""
        result = SSEFormatter.format_text("Hello World")
        assert result == "event: text\ndata: Hello World\n\n"

    def test_format_text_multiline(self):
        """Test formatting multiline text."""
        result = SSEFormatter.format_text("Hello\nWorld")
        assert result == "event: text\ndata: Hello\\nWorld\n\n"

    def test_format_error(self):
        """Test formatting error."""
        result = SSEFormatter.format_error("Something went wrong")
        assert "event: error" in result
        assert 'data: {"error": "Something went wrong"}' in result

    def test_format_done(self):
        """Test formatting done event."""
        result = SSEFormatter.format_done()
        assert result == "event: done\ndata: [DONE]\n\n"


class TestStreamHandler:
    """Tests for StreamHandler."""

    @pytest.fixture
    def handler(self):
        return StreamHandler()

    @pytest.mark.asyncio
    async def test_process_stream_mixed(self, handler):
        """Test processing a mixed stream of steps and text."""

        step = MockAgentStep("1", "reasoning", "Start")

        async def mock_generator() -> AsyncGenerator:
            yield step
            yield "Hello"
            yield " World"
            yield {"step_id": "2", "type": "tool", "content": "Search"}  # Dict support

        results = []
        async for item in handler.process_stream(mock_generator()):
            results.append(item)

        assert len(results) == 5  # step, text, text, step(dict), done

        # Check step
        assert "event: step" in results[0]
        assert '"content": "Start"' in results[0]

        # Check text
        assert "event: text" in results[1]
        assert "data: Hello" in results[1]

        # Check dict step
        assert "event: step" in results[3]
        assert '"content": "Search"' in results[3]

        # Check done
        assert "event: done" in results[4]

    @pytest.mark.asyncio
    async def test_process_stream_error(self, handler):
        """Test error handling in stream."""

        async def error_generator() -> AsyncGenerator:
            yield "Start"
            raise ValueError("Stream failed")

        results = []
        async for item in handler.process_stream(error_generator()):
            results.append(item)

        assert len(results) == 3  # text, error, done
        assert "event: text" in results[0]
        assert "event: error" in results[1]
        assert "Stream failed" in results[1]
        assert "event: done" in results[2]

    def test_create_response(self, handler):
        """Test creating StreamingResponse."""

        async def empty_gen():
            yield "test"

        response = handler.create_response(empty_gen())
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["X-Accel-Buffering"] == "no"

    def test_singleton(self):
        """Test singleton accessor."""
        h1 = get_stream_handler()
        h2 = get_stream_handler()
        assert h1 is h2
        assert isinstance(h1, StreamHandler)
