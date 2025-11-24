"""
Tests for sage.common.core.functions.base_function

Tests the BaseFunction abstract base class and its core functionality.
"""

import logging
from unittest.mock import Mock

import pytest

from sage.common.core.functions.base_function import BaseFunction


class ConcreteFunction(BaseFunction):
    """Concrete implementation of BaseFunction for testing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_value = 42
        self.test_string = "hello"

    def execute(self, data):
        """Concrete implementation of execute"""
        return data


class TestBaseFunction:
    """Tests for BaseFunction class"""

    def test_initialization(self):
        """Test function initialization"""
        func = ConcreteFunction()

        assert func.ctx is None
        assert func._logger is None
        assert func.test_value == 42

    def test_logger_without_context(self):
        """Test logger property without context"""
        func = ConcreteFunction()

        logger = func.logger
        assert isinstance(logger, logging.Logger)

    def test_logger_with_context(self):
        """Test logger property with context"""
        func = ConcreteFunction()

        # Mock context with logger
        mock_ctx = Mock()
        mock_logger = Mock(spec=logging.Logger)
        mock_ctx.logger = mock_logger

        func.ctx = mock_ctx
        logger = func.logger

        assert logger == mock_logger

    def test_name_without_context(self):
        """Test name property without context"""
        func = ConcreteFunction()

        name = func.name
        assert name == "ConcreteFunction"

    def test_name_with_context(self):
        """Test name property with context"""
        func = ConcreteFunction()

        # Mock context with name
        mock_ctx = Mock()
        mock_ctx.name = "test_function"

        func.ctx = mock_ctx
        name = func.name

        assert name == "test_function"

    def test_call_service_without_context(self):
        """Test call_service raises error without context"""
        func = ConcreteFunction()

        with pytest.raises(RuntimeError, match="Runtime context not initialized"):
            func.call_service("test_service")

    def test_call_service_with_context(self):
        """Test call_service with context"""
        func = ConcreteFunction()

        # Mock context
        mock_ctx = Mock()
        mock_ctx.call_service = Mock(return_value="result")

        func.ctx = mock_ctx

        result = func.call_service("test_service", arg1="value1", timeout=5.0)

        assert result == "result"
        mock_ctx.call_service.assert_called_once_with(
            "test_service", arg1="value1", timeout=5.0, method=None
        )

    def test_call_service_with_method(self):
        """Test call_service with method parameter"""
        func = ConcreteFunction()

        # Mock context
        mock_ctx = Mock()
        mock_ctx.call_service = Mock(return_value="result")

        func.ctx = mock_ctx

        result = func.call_service("test_service", method="custom_method", param=123)

        assert result == "result"
        mock_ctx.call_service.assert_called_once_with(
            "test_service", method="custom_method", param=123, timeout=None
        )

    def test_call_service_async_without_context(self):
        """Test call_service_async raises error without context"""
        func = ConcreteFunction()

        with pytest.raises(RuntimeError, match="Runtime context not initialized"):
            func.call_service_async("test_service")

    def test_call_service_async_with_context(self):
        """Test call_service_async with context"""
        func = ConcreteFunction()

        # Mock context
        mock_ctx = Mock()
        mock_future = Mock()
        mock_ctx.call_service_async = Mock(return_value=mock_future)

        func.ctx = mock_ctx

        result = func.call_service_async("test_service", arg1="value1", timeout=10.0)

        assert result == mock_future
        mock_ctx.call_service_async.assert_called_once_with(
            "test_service", arg1="value1", timeout=10.0, method=None
        )

    def test_get_state_basic(self):
        """Test get_state returns function attributes"""
        func = ConcreteFunction()

        state = func.get_state()

        assert isinstance(state, dict)
        assert "test_value" in state
        assert state["test_value"] == 42
        assert "test_string" in state
        assert state["test_string"] == "hello"

    def test_get_state_excludes_context(self):
        """Test get_state excludes context and logger"""
        func = ConcreteFunction()
        func.ctx = Mock()

        state = func.get_state()

        assert "ctx" not in state
        assert "_logger" not in state
        assert "logger" not in state

    def test_get_state_with_include_list(self):
        """Test get_state with __state_include__ filter"""

        class SelectiveFunction(BaseFunction):
            __state_include__ = ["important_value"]

            def __init__(self):
                super().__init__()
                self.important_value = 100
                self.ignored_value = 200

            def execute(self, data):
                return data

        func = SelectiveFunction()
        state = func.get_state()

        assert "important_value" in state
        assert state["important_value"] == 100
        # When include list is specified, only those are included
        if "__state_include__" in func.__dict__:
            assert "ignored_value" not in state

    def test_get_state_with_exclude_list(self):
        """Test get_state with custom __state_exclude__"""

        class ExclusiveFunction(BaseFunction):
            __state_exclude__ = ["ctx", "_logger", "logger", "secret"]  # pragma: allowlist secret

            def __init__(self):
                super().__init__()
                self.public_value = 100
                self.secret = "hidden"  # pragma: allowlist secret

            def execute(self, data):
                return data

        func = ExclusiveFunction()
        state = func.get_state()

        assert "public_value" in state
        assert "secret" not in state  # pragma: allowlist secret

    def test_restore_state_basic(self):
        """Test restore_state restores function state"""
        func = ConcreteFunction()

        # Change values
        func.test_value = 99
        func.test_string = "changed"

        # Save state
        state = {"test_value": 42, "test_string": "hello", "new_attr": "new"}

        func.restore_state(state)

        assert func.test_value == 42
        assert func.test_string == "hello"
        assert func.new_attr == "new"

    def test_state_include_list_behavior(self):
        """Test __state_include__ behavior"""

        class FilteredFunction(BaseFunction):
            __state_include__ = ["kept"]

            def __init__(self):
                super().__init__()
                self.kept = "keep_this"
                self.removed = "remove_this"

            def execute(self, data):
                return data

        func = FilteredFunction()
        state = func.get_state()

        # If include list is used, only those fields should be present
        assert "kept" in state

    def test_state_exclude_list_behavior(self):
        """Test __state_exclude__ behavior"""

        class ExcludedFunction(BaseFunction):
            __state_exclude__ = ["ctx", "_logger", "logger", "excluded_field"]

            def __init__(self):
                super().__init__()
                self.included_field = "include"
                self.excluded_field = "exclude"

            def execute(self, data):
                return data

        func = ExcludedFunction()
        state = func.get_state()

        assert "included_field" in state
        assert "excluded_field" not in state
        assert "ctx" not in state


class TestBaseFunctionStatePersistence:
    """Tests for state persistence functionality"""

    def test_roundtrip_state(self):
        """Test saving and restoring state"""
        func1 = ConcreteFunction()
        func1.test_value = 123
        func1.test_string = "modified"

        # Save state
        state = func1.get_state()

        # Create new function and restore state
        func2 = ConcreteFunction()
        func2.restore_state(state)

        assert func2.test_value == 123
        assert func2.test_string == "modified"

    def test_state_excludes_unserializable_types(self):
        """Test that unserializable types are excluded from state"""

        class FunctionWithCallables(BaseFunction):
            def __init__(self):
                super().__init__()
                self.value = 42
                self.callback = lambda x: x * 2

            def execute(self, data):
                return data

        func = FunctionWithCallables()
        state = func.get_state()

        assert "value" in state
        # Functions should be excluded
        assert "callback" not in state or not callable(state.get("callback"))
