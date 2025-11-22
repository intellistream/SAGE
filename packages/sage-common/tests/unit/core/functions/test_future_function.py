"""
Tests for FutureFunction class

FutureFunction is a placeholder function for future transformations
that should not be executed directly.

Tests cover:
- Inheritance and basic properties
- __call__ raises RuntimeError
- call() raises RuntimeError
- __repr__ representation
- Error messages
"""

import pytest

from sage.common.core.functions.base_function import BaseFunction
from sage.common.core.functions.future_function import FutureFunction


# Concrete implementation for testing
class ConcreteFutureFunction(FutureFunction):
    """Concrete FutureFunction for testing"""

    def execute(self, data):
        """Implement execute to make class concrete"""
        # This should never be called for FutureFunction
        raise RuntimeError("FutureFunction execute should not be called")


class TestFutureFunctionBasics:
    """Test FutureFunction basic properties"""

    def test_future_function_inherits_from_base_function(self):
        """Test FutureFunction inherits from BaseFunction"""
        func = ConcreteFutureFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, FutureFunction)

    def test_future_function_instantiation(self):
        """Test FutureFunction can be instantiated"""
        func = ConcreteFutureFunction()
        assert func is not None


class TestFutureFunctionCallMethod:
    """Test FutureFunction __call__ method"""

    def test_call_raises_runtime_error(self):
        """Test __call__ raises RuntimeError"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError):
            func()

    def test_call_with_args_raises_runtime_error(self):
        """Test __call__ with args raises RuntimeError"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError):
            func("arg1", "arg2")

    def test_call_with_kwargs_raises_runtime_error(self):
        """Test __call__ with kwargs raises RuntimeError"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError):
            func(key1="value1", key2="value2")

    def test_call_error_message_mentions_placeholder(self):
        """Test error message mentions placeholder"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError, match="placeholder"):
            func()

    def test_call_error_message_warns_not_to_call(self):
        """Test error message warns not to call directly"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError, match="should not be called directly"):
            func()


class TestFutureFunctionCallMethodExplicit:
    """Test FutureFunction call() method"""

    def test_call_method_raises_runtime_error(self):
        """Test call() raises RuntimeError"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError):
            func.call("data")

    def test_call_method_with_none_raises_error(self):
        """Test call() with None raises RuntimeError"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError):
            func.call(None)

    def test_call_method_with_complex_data_raises_error(self):
        """Test call() with complex data raises RuntimeError"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError):
            func.call({"complex": "data", "nested": [1, 2, 3]})

    def test_call_method_error_message(self):
        """Test call() error message is correct"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError, match="FutureFunction should not be called directly"):
            func.call("test")

    def test_call_method_error_message_mentions_placeholder(self):
        """Test call() error message mentions placeholder"""
        func = ConcreteFutureFunction()

        with pytest.raises(RuntimeError, match="placeholder"):
            func.call("test")


class TestFutureFunctionRepr:
    """Test FutureFunction __repr__ method"""

    def test_repr_returns_string(self):
        """Test __repr__ returns a string"""
        func = ConcreteFutureFunction()
        result = repr(func)
        assert isinstance(result, str)

    def test_repr_contains_function_name(self):
        """Test __repr__ contains 'FutureFunction'"""
        func = ConcreteFutureFunction()
        result = repr(func)
        assert "FutureFunction" in result

    def test_repr_contains_placeholder(self):
        """Test __repr__ contains 'placeholder'"""
        func = ConcreteFutureFunction()
        result = repr(func)
        assert "placeholder" in result

    def test_repr_exact_format(self):
        """Test __repr__ exact format"""
        func = ConcreteFutureFunction()
        result = repr(func)
        assert result == "FutureFunction(placeholder)"

    def test_repr_consistency(self):
        """Test __repr__ is consistent across calls"""
        func = ConcreteFutureFunction()
        result1 = repr(func)
        result2 = repr(func)
        assert result1 == result2


class TestFutureFunctionMultipleInstances:
    """Test multiple FutureFunction instances"""

    def test_multiple_instances_independent(self):
        """Test multiple instances are independent"""
        func1 = ConcreteFutureFunction()
        func2 = ConcreteFutureFunction()

        assert func1 is not func2
        assert repr(func1) == repr(func2)

    def test_multiple_instances_all_raise_errors(self):
        """Test all instances raise errors when called"""
        funcs = [ConcreteFutureFunction() for _ in range(3)]

        for func in funcs:
            with pytest.raises(RuntimeError):
                func()
            with pytest.raises(RuntimeError):
                func.call("data")


class TestFutureFunctionEdgeCases:
    """Test edge cases for FutureFunction"""

    def test_str_representation(self):
        """Test str() representation"""
        func = ConcreteFutureFunction()
        # str() should use __repr__ if __str__ is not defined
        str_result = str(func)
        # Should return a string
        assert isinstance(str_result, str)

    def test_calling_after_repr(self):
        """Test calling function after repr still raises error"""
        func = ConcreteFutureFunction()
        _ = repr(func)

        with pytest.raises(RuntimeError):
            func()

    def test_repr_after_failed_call(self):
        """Test repr still works after failed call"""
        func = ConcreteFutureFunction()

        try:
            func()
        except RuntimeError:
            pass

        result = repr(func)
        assert result == "FutureFunction(placeholder)"

    def test_multiple_call_attempts(self):
        """Test multiple call attempts all fail"""
        func = ConcreteFutureFunction()

        for _ in range(5):
            with pytest.raises(RuntimeError):
                func()

    def test_call_and_call_method_raise_same_error(self):
        """Test __call__ and call() raise same type of error"""
        func = ConcreteFutureFunction()

        try:
            func()
        except RuntimeError as e1:
            error1_msg = str(e1)

        try:
            func.call("data")
        except RuntimeError as e2:
            error2_msg = str(e2)

        # Both should be RuntimeError with placeholder message
        assert "placeholder" in error1_msg
        assert "placeholder" in error2_msg
