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

    def test_format_data_empty_list(self):
        """Test formatting empty list returns '[]' (line 119)"""
        sink = PrintSink(quiet=True)
        assert sink._format_data([]) == "[]"

    def test_format_data_short_list(self):
        """Test formatting short list (<=5 elements) returns str(data) (line 121)"""
        sink = PrintSink(quiet=True)
        short_list = [1, 2, 3]
        result = sink._format_data(short_list)
        assert result == str(short_list)

    def test_format_data_object_without_attributes(self):
        """Test formatting object without __dict__ attributes (lines 134-140)"""
        sink = PrintSink(quiet=True)

        # Object with empty __dict__
        class EmptyObject:
            pass

        obj = EmptyObject()
        result = sink._format_data(obj)
        assert result == "EmptyObject()"

    def test_format_data_unprintable_object(self):
        """Test handling of objects that raise exception in str() (lines 137-139)"""
        sink = PrintSink(quiet=True)

        # Object without __dict__ that raises exception in str()
        class UnprintableObject:
            __slots__ = ()  # No __dict__

            def __str__(self):
                raise ValueError("Cannot convert to string")

        obj = UnprintableObject()
        result = sink._format_data(obj)
        assert result == "<Unprintable: UnprintableObject>"

    def test_repr_method(self):
        """Test __repr__ method returns proper representation (line 144)"""
        sink = PrintSink(prefix="MyPrefix")
        assert repr(sink) == "InternalPrintSink(prefix='MyPrefix')"

    def test_execute_with_empty_prefix(self):
        """Test execute with no prefix"""
        sink = PrintSink(prefix="", quiet=True)
        sink.execute("test")  # Should not crash

    def test_execute_quiet_mode_first_output(self, capsys):
        """Test quiet mode still prints first output without banner"""
        sink = PrintSink(prefix="Test", quiet=True)
        sink.execute("message")

        captured = capsys.readouterr()
        assert "Test | message" in captured.out
        assert "🔍 Stream output" not in captured.out
        assert "Further outputs" not in captured.out
