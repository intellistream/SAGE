"""Tests for the internal PrintSink utility."""

import logging

import pytest

from sage.common.components.debug.print_sink import PrintSink


@pytest.mark.unit
class TestPrintSink:
    """Unit tests covering PrintSink behaviors."""

    def test_execute_prints_first_output(self, capsys):
        """First execution should print a helpful banner with prefix."""

        sink = PrintSink(prefix="[Test]", separator=": ")

        sink.execute("hello world")

        captured = capsys.readouterr()
        assert "🔍 Stream output: [Test]: hello world" in captured.out
        assert "Further outputs logged" in captured.out

    def test_execute_logs_after_first_output(self, caplog):
        """Subsequent executions should go to the logger."""

        sink = PrintSink(quiet=True)
        sink.execute("first message")

        with caplog.at_level(logging.DEBUG):
            sink.execute("second message")

        assert "Stream output: second message" in caplog.text

    def test_format_data_handles_various_inputs(self):
        """The private formatter should gracefully handle common types."""

        sink = PrintSink(quiet=True)

        assert sink._format_data(None) == "None"
        assert sink._format_data("text") == "text"
        assert sink._format_data(42) == "42"

        dict_result = sink._format_data({"a": 1, "b": 2})
        assert "a=1" in dict_result and "b=2" in dict_result

        long_list_result = sink._format_data([1, 2, 3, 4, 5, 6])
        assert long_list_result.startswith("[1, 2, 3, 4, 5")
        assert "+1 more" in long_list_result

        class Dummy:
            def __init__(self):
                self.foo = "bar"
                self.count = 3

        object_result = sink._format_data(Dummy())
        assert object_result.startswith("Dummy(")
        assert "foo=bar" in object_result
