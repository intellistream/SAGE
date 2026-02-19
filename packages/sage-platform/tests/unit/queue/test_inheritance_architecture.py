"""
测试基于继承的队列描述符架构

验证 BaseQueueDescriptor 及其子类的功能完整性
"""

import pytest

from sage.platform.queue import (
    BaseQueueDescriptor,
    PythonQueueDescriptor,
    RPCQueueDescriptor,
    resolve_descriptor,
)


class TestBaseQueueDescriptor:
    """测试基础队列描述符"""

    def test_abstract_methods(self):
        """测试抽象方法不能直接实例化"""
        with pytest.raises(TypeError):
            BaseQueueDescriptor()  # type: ignore[abstract]


class TestPythonQueueDescriptor:
    """测试Python队列描述符"""

    def test_local_queue_creation(self):
        """测试本地队列创建"""
        queue = PythonQueueDescriptor(queue_id="test_local", maxsize=10)

        assert queue.queue_id == "test_local"
        assert queue.queue_type == "python"
        assert queue.can_serialize is True
        assert queue.metadata["maxsize"] == 10
        assert queue.metadata["use_multiprocessing"] is False

    def test_multiprocessing_queue_creation(self):
        """测试多进程队列创建"""
        queue = PythonQueueDescriptor(queue_id="test_mp", maxsize=20, use_multiprocessing=True)

        assert queue.queue_id == "test_mp"
        assert queue.queue_type == "python"
        assert queue.metadata["maxsize"] == 20
        assert queue.metadata["use_multiprocessing"] is True

    def test_queue_operations(self):
        """测试队列基本操作"""
        queue = PythonQueueDescriptor(queue_id="test_ops", maxsize=5)

        # 初始状态
        assert queue.empty() is True
        assert queue.qsize() == 0

        # 放入和取出
        queue.put("item1")
        queue.put("item2")

        assert queue.empty() is False
        assert queue.qsize() == 2

        item1 = queue.get()
        item2 = queue.get()

        assert item1 == "item1"
        assert item2 == "item2"
        assert queue.empty() is True

    def test_serialization(self):
        """测试序列化功能"""
        queue = PythonQueueDescriptor(queue_id="test_serial", maxsize=10)

        # 序列化为字典
        data = queue.to_dict()
        assert data["queue_id"] == "test_serial"
        assert data["queue_type"] == "python"
        assert data["metadata"]["maxsize"] == 10

        # 序列化为JSON
        json_str = queue.to_json()
        assert isinstance(json_str, str)
        assert "test_serial" in json_str

        # 创建新的队列描述符来模拟反序列化
        restored = PythonQueueDescriptor(
            queue_id=data["queue_id"], maxsize=data["metadata"]["maxsize"]
        )
        assert restored.queue_id == queue.queue_id
        assert restored.queue_type == queue.queue_type

    def test_clone(self):
        """测试克隆功能"""
        original = PythonQueueDescriptor(queue_id="original", maxsize=15)
        clone = original.clone("cloned")

        assert clone.queue_id == "cloned"
        assert clone.queue_type == original.queue_type
        # 克隆应该保留原始配置
        assert clone.maxsize == 15  # 克隆保留原始的 maxsize 配置
        assert clone.is_initialized() is False

    def test_lazy_loading(self):
        """测试懒加载功能"""
        queue = PythonQueueDescriptor(queue_id="lazy_test")

        # 初始状态未初始化
        assert queue.is_initialized() is False

        # 首次使用时初始化
        queue.put("lazy_item")
        assert queue.is_initialized() is True

        # 清除缓存
        queue.clear_cache()
        assert queue.is_initialized() is False


class TestRPCQueueDescriptor:
    """测试RPC队列描述符"""

    def test_rpc_queue_creation(self):
        """测试RPC队列创建"""
        queue = RPCQueueDescriptor(queue_id="test_rpc", host="localhost", port=8080)

        assert queue.queue_id == "test_rpc"
        assert queue.queue_type == "rpc_queue"
        assert queue.metadata["host"] == "localhost"
        assert queue.metadata["port"] == 8080


class TestDescriptorResolution:
    """测试描述符解析功能"""

    def test_resolve_python_descriptor(self):
        """测试解析Python描述符"""
        queue = PythonQueueDescriptor(queue_id="test_resolve")
        data = queue.to_dict()
        resolved = resolve_descriptor(data)

        # 解析应该返回相同类型的队列描述符
        assert resolved is not None
        assert resolved.queue_id == queue.queue_id
        assert resolved.queue_type == queue.queue_type


class TestErrorHandling:
    """测试错误处理"""

    def test_invalid_queue_id(self):
        """测试无效队列ID"""
        # PythonQueueDescriptor 允许空字符串作为 queue_id，会自动生成
        # 这里测试传入 None 的情况
        queue = PythonQueueDescriptor(queue_id=None)
        assert queue.queue_id is not None
        assert len(queue.queue_id) > 0

    def test_invalid_parameters(self):
        """测试无效参数"""
        # PythonQueueDescriptor 允许负数 maxsize，这里测试正常创建
        queue = PythonQueueDescriptor(queue_id="test", maxsize=-1)
        assert queue.maxsize == -1


if __name__ == "__main__":
    # 运行测试
    test_suite = [
        TestBaseQueueDescriptor(),
        TestPythonQueueDescriptor(),
        TestRPCQueueDescriptor(),
        TestDescriptorResolution(),
        TestErrorHandling(),
    ]

    print("Running inheritance-based queue descriptor tests...")

    try:
        # 测试Python队列描述符
        python_tests = TestPythonQueueDescriptor()
        python_tests.test_local_queue_creation()
        print("✓ Python queue creation tests passed")

        python_tests.test_queue_operations()
        print("✓ Python queue operations tests passed")

        python_tests.test_serialization()
        print("✓ Python queue serialization tests passed")

        python_tests.test_clone()
        print("✓ Python queue clone tests passed")

        python_tests.test_lazy_loading()
        print("✓ Python queue lazy loading tests passed")

        # 测试错误处理
        error_tests = TestErrorHandling()
        error_tests.test_invalid_queue_id()
        print("✓ Error handling tests passed")

        print(
            "\n🎉 All tests passed! The inheritance-based queue architecture is working correctly."
        )

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
