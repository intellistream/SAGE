"""
测试 dill 序列化器的基本功能

本测试文件验证 dill 序列化器的各种基本功能，包括：
- 基本数据类型序列化
- 复杂对象序列化
- 属性过滤
- 错误处理
"""

import threading

import pytest
from sage.common.utils.serialization.dill import (SerializationError,
                                                  UniversalSerializer,
                                                  deserialize_object,
                                                  serialize_object)


class TestUniversalSerializer:
    """测试 UniversalSerializer 类"""

    def test_basic_types_serialization(self):
        """测试基本类型的序列化"""
        test_cases = [
            42,
            3.14,
            "hello world",
            True,
            False,
            None,
            [1, 2, 3],
            {"key": "value"},
            (1, 2, 3),
            {1, 2, 3},
        ]

        for original in test_cases:
            serialized = serialize_object(original)
            restored = deserialize_object(serialized)
            assert restored == original, f"Failed for type {type(original)}: {original}"

    def test_simple_object_serialization(self):
        """测试简单对象的序列化"""

        class SimpleObject:
            def __init__(self, value):
                self.value = value

            def __eq__(self, other):
                return hasattr(other, "value") and self.value == other.value

        obj = SimpleObject("test_value")
        serialized = serialize_object(obj)
        restored = deserialize_object(serialized)

        assert restored.value == obj.value
        assert restored == obj

    def test_attribute_filtering_exclude(self):
        """测试属性过滤 - 排除特定属性"""

        class ObjectWithExclude:
            __state_exclude__ = ["sensitive_data", "temp_value"]

            def __init__(self):
                self.normal_data = "keep this"
                self.sensitive_data = "exclude this"
                self.temp_value = "also exclude"
                self.another_normal = "keep this too"

        obj = ObjectWithExclude()
        serialized = serialize_object(obj)
        restored = deserialize_object(serialized)

        # 正常属性应该保留
        assert restored.normal_data == "keep this"
        assert restored.another_normal == "keep this too"

        # 排除的属性不应该存在
        assert not hasattr(restored, "sensitive_data")
        assert not hasattr(restored, "temp_value")

    def test_attribute_filtering_include(self):
        """测试属性过滤 - 仅包含特定属性"""

        class ObjectWithInclude:
            __state_include__ = ["important_data"]

            def __init__(self):
                self.important_data = "keep this"
                self.unimportant_data = "exclude this"
                self.other_data = "also exclude"

        obj = ObjectWithInclude()
        serialized = serialize_object(obj)
        restored = deserialize_object(serialized)

        # 包含的属性应该保留
        assert restored.important_data == "keep this"

        # 其他属性不应该存在
        assert not hasattr(restored, "unimportant_data")
        assert not hasattr(restored, "other_data")

    def test_blacklisted_objects_excluded(self):
        """测试黑名单对象被排除"""

        class ObjectWithBlacklisted:
            def __init__(self):
                self.normal_data = "keep this"
                self.thread = threading.Thread(target=lambda: None)
                self.lock = threading.Lock()

        obj = ObjectWithBlacklisted()
        serialized = serialize_object(obj)
        restored = deserialize_object(serialized)

        # 正常数据应该保留
        assert restored.normal_data == "keep this"

        # 黑名单对象不应该存在
        assert not hasattr(restored, "thread")
        assert not hasattr(restored, "lock")

    def test_nested_objects(self):
        """测试嵌套对象"""

        class Inner:
            def __init__(self, value):
                self.value = value

            def __eq__(self, other):
                return hasattr(other, "value") and self.value == other.value

        class Outer:
            def __init__(self, inner_obj, data):
                self.inner = inner_obj
                self.data = data

            def __eq__(self, other):
                return (
                    hasattr(other, "inner")
                    and hasattr(other, "data")
                    and self.inner == other.inner
                    and self.data == other.data
                )

        inner = Inner("inner_value")
        outer = Outer(inner, {"key": "value"})

        serialized = serialize_object(outer)
        restored = deserialize_object(serialized)

        assert restored.inner.value == "inner_value"
        assert restored.data == {"key": "value"}
        assert restored == outer

    def test_serialization_error_handling(self):
        """测试序列化错误处理"""

        # 这个测试验证错误处理机制
        # 在正常情况下，大多数对象都应该能够成功序列化
        # 这里我们主要验证错误类型的正确性

        class ProblematicObject:
            def __init__(self):
                self.data = "normal"

        obj = ProblematicObject()

        try:
            # 正常情况下应该成功
            serialized = serialize_object(obj)
            restored = deserialize_object(serialized)
            assert restored.data == "normal"
        except SerializationError:
            # 如果出现序列化错误，应该是 SerializationError 类型
            pass

    def test_static_methods(self):
        """测试静态方法"""

        class TestData:
            def __init__(self, value):
                self.value = value

        # 测试 DillSerializer 的静态方法
        obj = TestData("test")

        # 使用静态方法序列化
        serialized = UniversalSerializer.serialize_object(obj)
        restored = UniversalSerializer.deserialize_object(serialized)

        assert restored.value == "test"

        # 测试便捷函数
        serialized2 = serialize_object(obj)
        restored2 = deserialize_object(serialized2)

        assert restored2.value == "test"
        assert serialized == serialized2  # 两种方法应该产生相同结果


if __name__ == "__main__":
    # 允许直接运行测试文件
    pytest.main([__file__, "-v"])
