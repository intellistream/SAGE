"""
Tests for sage.common.utils.serialization.exceptions module
===================================================

单元测试序列化异常模块的功能，包括：
- SerializationError异常类
- 异常继承关系
- 异常使用场景
"""

import pytest

from sage.common.utils.serialization.exceptions import SerializationError


@pytest.mark.unit
class TestSerializationError:
    """SerializationError异常类测试"""

    def test_serialization_error_is_exception(self):
        """测试SerializationError是Exception的子类"""
        assert issubclass(SerializationError, Exception)

    def test_serialization_error_instantiation(self):
        """测试SerializationError实例化"""
        error = SerializationError("Test error message")
        assert isinstance(error, SerializationError)
        assert isinstance(error, Exception)
        assert str(error) == "Test error message"

    def test_serialization_error_without_message(self):
        """测试不带消息的SerializationError"""
        error = SerializationError()
        assert isinstance(error, SerializationError)
        assert str(error) == ""

    def test_serialization_error_with_args(self):
        """测试带多个参数的SerializationError"""
        error = SerializationError("Error", "Additional info", 123)
        assert len(error.args) == 3
        assert error.args[0] == "Error"
        assert error.args[1] == "Additional info"
        assert error.args[2] == 123

    def test_serialization_error_str_representation(self):
        """测试SerializationError字符串表示"""
        error = SerializationError("Serialization failed")
        assert str(error) == "Serialization failed"

        error_multi = SerializationError("Error", "Details")
        assert str(error_multi) == "('Error', 'Details')"

    def test_serialization_error_repr_representation(self):
        """测试SerializationError repr表示"""
        error = SerializationError("Test error")
        repr_str = repr(error)
        assert "SerializationError" in repr_str
        assert "Test error" in repr_str


@pytest.mark.unit
class TestSerializationErrorUsageScenarios:
    """SerializationError使用场景测试"""

    def test_raise_serialization_error(self):
        """测试抛出SerializationError"""
        with pytest.raises(SerializationError) as exc_info:
            raise SerializationError("Failed to serialize object")

        assert str(exc_info.value) == "Failed to serialize object"
        assert isinstance(exc_info.value, SerializationError)

    def test_catch_serialization_error(self):
        """测试捕获SerializationError"""

        def failing_serialization():
            raise SerializationError("Serialization failed")

        try:
            failing_serialization()
            raise AssertionError("Should have raised SerializationError")
        except SerializationError as e:
            assert str(e) == "Serialization failed"
        except Exception:
            raise AssertionError("Should have caught SerializationError specifically")

    def test_serialization_error_with_chaining(self):
        """测试SerializationError异常链"""

        def inner_function():
            raise ValueError("Original error")

        def outer_function():
            try:
                inner_function()
            except ValueError as e:
                raise SerializationError("Serialization failed") from e

        with pytest.raises(SerializationError) as exc_info:
            outer_function()

        assert str(exc_info.value) == "Serialization failed"
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "Original error"

    def test_serialization_error_context_manager(self):
        """测试在上下文管理器中使用SerializationError"""

        class SerializationContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    raise SerializationError(f"Context error: {exc_val}") from exc_val

        with pytest.raises(SerializationError) as exc_info:
            with SerializationContext():
                raise ValueError("Context test error")

        assert "Context error: Context test error" in str(exc_info.value)

    def test_serialization_error_with_detailed_info(self):
        """测试带详细信息的SerializationError"""
        object_info = {
            "type": "CustomObject",
            "id": 12345,
            "attributes": ["attr1", "attr2"],
        }

        error_message = f"Failed to serialize {object_info['type']} with ID {object_info['id']}"

        with pytest.raises(SerializationError) as exc_info:
            raise SerializationError(error_message, object_info)

        assert error_message in str(exc_info.value)
        assert len(exc_info.value.args) == 2
        assert exc_info.value.args[1] == object_info

    def test_serialization_error_hierarchy(self):
        """测试SerializationError在异常层次中的位置"""

        def function_that_might_fail(fail_type="serialization"):
            if fail_type == "serialization":
                raise SerializationError("Serialization specific error")
            elif fail_type == "generic":
                raise Exception("Generic error")
            elif fail_type == "value":
                raise ValueError("Value error")

        # 测试捕获SerializationError
        with pytest.raises(SerializationError):
            function_that_might_fail("serialization")

        # 测试捕获为Exception
        with pytest.raises(Exception):  # noqa: B017
            function_that_might_fail("serialization")

        # 测试不同的异常类型
        with pytest.raises(ValueError):
            function_that_might_fail("value")


@pytest.mark.unit
class TestSerializationErrorInFunctionDecorators:
    """测试SerializationError在函数装饰器中的使用"""

    def test_serialization_error_decorator(self):
        """测试序列化错误装饰器"""

        def serialization_error_handler(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if isinstance(e, SerializationError):
                        raise
                    else:
                        raise SerializationError(f"Serialization failed in {func.__name__}") from e

            return wrapper

        @serialization_error_handler
        def problematic_serialization():
            raise ValueError("Some internal error")

        with pytest.raises(SerializationError) as exc_info:
            problematic_serialization()

        assert "Serialization failed in problematic_serialization" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_serialization_error_retry_decorator(self):
        """测试带重试的序列化错误装饰器"""

        def retry_on_serialization_error(max_retries=3):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    for attempt in range(max_retries):
                        try:
                            return func(*args, **kwargs)
                        except SerializationError as e:
                            if attempt == max_retries - 1:
                                raise SerializationError(
                                    f"Failed after {max_retries} attempts: {str(e)}"
                                ) from e
                            continue
                    return None

                return wrapper

            return decorator

        call_count = 0

        @retry_on_serialization_error(max_retries=3)
        def unreliable_serialization():
            nonlocal call_count
            call_count += 1
            raise SerializationError(f"Attempt {call_count} failed")

        with pytest.raises(SerializationError) as exc_info:
            unreliable_serialization()

        assert call_count == 3
        assert "Failed after 3 attempts" in str(exc_info.value)


@pytest.mark.integration
class TestSerializationErrorIntegration:
    """SerializationError集成测试"""

    def test_serialization_error_in_mock_serializer(self):
        """测试在模拟序列化器中使用SerializationError"""
        import json
        import pickle

        class MockSerializer:
            def __init__(self, method="json"):
                self.method = method

            def serialize(self, obj):
                try:
                    if self.method == "json":
                        return json.dumps(obj)
                    elif self.method == "pickle":
                        return pickle.dumps(obj)
                    else:
                        raise ValueError(f"Unknown serialization method: {self.method}")
                except (TypeError, ValueError, pickle.PickleError) as e:
                    raise SerializationError(
                        f"Failed to serialize object using {self.method}: {str(e)}"
                    ) from e

            def deserialize(self, data):
                try:
                    if self.method == "json":
                        return json.loads(data)
                    elif self.method == "pickle":
                        return pickle.loads(data)
                    else:
                        raise ValueError(f"Unknown deserialization method: {self.method}")
                except (
                    TypeError,
                    ValueError,
                    pickle.PickleError,
                    json.JSONDecodeError,
                ) as e:
                    raise SerializationError(
                        f"Failed to deserialize data using {self.method}: {str(e)}"
                    ) from e

        # 测试成功的序列化
        serializer = MockSerializer("json")
        data = {"key": "value", "number": 42}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        assert deserialized == data

        # 测试JSON序列化失败
        with pytest.raises(SerializationError) as exc_info:
            serializer.serialize({1, 2, 3})  # set不能JSON序列化

        assert "Failed to serialize object using json" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, TypeError)

        # 测试JSON反序列化失败
        with pytest.raises(SerializationError) as exc_info:
            serializer.deserialize("invalid json")

        assert "Failed to deserialize data using json" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)

        # 测试未知方法
        unknown_serializer = MockSerializer("unknown")
        with pytest.raises(SerializationError) as exc_info:
            unknown_serializer.serialize(data)

        assert "Unknown serialization method: unknown" in str(exc_info.value)

    def test_serialization_error_with_complex_object(self):
        """测试复杂对象的序列化错误"""

        class ComplexObject:
            def __init__(self):
                self.name = "complex"
                self.data = {"nested": {"deep": "value"}}
                self.function = lambda x: x * 2  # 不可序列化的函数

        def serialize_object(obj):
            """模拟对象序列化函数"""
            try:
                # 尝试简单的属性提取
                result = {}
                for attr_name in dir(obj):
                    if not attr_name.startswith("_"):
                        attr_value = getattr(obj, attr_name)
                        if callable(attr_value):
                            raise TypeError(f"Cannot serialize callable attribute: {attr_name}")
                        result[attr_name] = attr_value
                return result
            except Exception as e:
                raise SerializationError(f"Failed to serialize {obj.__class__.__name__}") from e

        complex_obj = ComplexObject()

        with pytest.raises(SerializationError) as exc_info:
            serialize_object(complex_obj)

        assert "Failed to serialize ComplexObject" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, TypeError)
        assert "Cannot serialize callable attribute" in str(exc_info.value.__cause__)

    def test_serialization_error_logging(self):
        """测试SerializationError的日志记录"""
        import importlib
        import logging

        # 使用importlib来避免io模块冲突
        io_module = importlib.import_module("io")
        StringIO = io_module.StringIO

        # 设置日志捕获
        log_capture = StringIO()
        logger = logging.getLogger("test_serialization")
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

        def serialize_with_logging(obj):
            try:
                # 模拟序列化失败
                raise ValueError("Mock serialization failure")
            except Exception as e:
                error = SerializationError("Serialization failed for object")
                error.__cause__ = e
                logger.error(f"Serialization error: {error}", exc_info=True)
                raise error

        try:
            with pytest.raises(SerializationError):
                serialize_with_logging({"test": "object"})
        finally:
            logger.removeHandler(handler)

        # 验证日志内容
        log_content = log_capture.getvalue()
        assert "Serialization error:" in log_content
        # The exception class name should appear in the traceback
        assert "SerializationError" in log_content or "Mock serialization failure" in log_content
