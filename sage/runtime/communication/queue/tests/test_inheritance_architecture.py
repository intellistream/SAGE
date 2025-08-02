"""
测试基于继承的队列描述符架构

验证 BaseQueueDescriptor 及其子类的功能完整性
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from sage.runtime.communication.queue import (
    BaseQueueDescriptor,
    PythonQueueDescriptor,
    RayQueueDescriptor,
    SageQueueDescriptor,
    RPCQueueDescriptor,
    resolve_descriptor
)


class TestBaseQueueDescriptor:
    """测试基础队列描述符"""
    
    def test_abstract_methods(self):
        """测试抽象方法不能直接实例化"""
        with pytest.raises(TypeError):
            BaseQueueDescriptor()


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
        queue = PythonQueueDescriptor(
            queue_id="test_mp", 
            maxsize=20, 
            use_multiprocessing=True
        )
        
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
        
        # 反序列化
        restored = PythonQueueDescriptor.from_dict(data)
        assert restored.queue_id == queue.queue_id
        assert restored.queue_type == queue.queue_type
        assert restored.metadata == queue.metadata
    
    def test_clone(self):
        """测试克隆功能"""
        original = PythonQueueDescriptor(queue_id="original", maxsize=15)
        clone = original.clone("cloned")
        
        assert clone.queue_id == "cloned"
        assert clone.queue_type == original.queue_type
        assert clone.metadata == original.metadata
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


class TestRayQueueDescriptor:
    """测试Ray队列描述符"""
    
    @patch('ray.util.Queue')
    @patch('ray.is_initialized')
    def test_ray_queue_creation(self, mock_ray_initialized, mock_ray_queue):
        """测试Ray队列创建"""
        mock_ray_initialized.return_value = True
        mock_queue_instance = MagicMock()
        mock_ray_queue.return_value = mock_queue_instance
        
        queue = RayQueueDescriptor(queue_id="test_ray", maxsize=100)
        
        assert queue.queue_id == "test_ray"
        assert queue.queue_type == "ray_queue"
        assert queue.metadata["maxsize"] == 100
    
    @patch('ray.get_actor')
    @patch('ray.is_initialized')
    def test_ray_actor_queue_creation(self, mock_ray_initialized, mock_get_actor):
        """测试Ray Actor队列创建"""
        mock_ray_initialized.return_value = True
        mock_actor = MagicMock()
        mock_get_actor.return_value = mock_actor
        
        queue = RayQueueDescriptor(
            queue_id="test_actor", 
            maxsize=200
        )
        
        assert queue.queue_id == "test_actor"
        assert queue.queue_type == "ray_queue"
        assert queue.metadata["maxsize"] == 200


class TestSageQueueDescriptor:
    """测试SAGE队列描述符"""
    
    @patch('sage_ext.sage_queue.python.sage_queue.SageQueue')
    def test_sage_queue_creation(self, mock_sage_queue):
        """测试SAGE队列创建"""
        mock_instance = MagicMock()
        mock_sage_queue.return_value = mock_instance
        
        queue = SageQueueDescriptor(
            queue_id="test_sage",
            maxsize=1024*1024,
            auto_cleanup=True,
            namespace="test_ns"
        )
        
        assert queue.queue_id == "test_sage"
        assert queue.queue_type == "sage"
        assert queue.metadata["maxsize"] == 1024*1024
        assert queue.metadata["auto_cleanup"] is True
        assert queue.metadata["namespace"] == "test_ns"
    
    @patch('sage_ext.sage_queue.python.sage_queue.SageQueue')
    def test_sage_queue_operations(self, mock_sage_queue):
        """测试SAGE队列操作"""
        mock_instance = MagicMock()
        mock_sage_queue.return_value = mock_instance
        mock_instance.put.return_value = None
        mock_instance.get.return_value = "sage_item"
        mock_instance.empty.return_value = False
        mock_instance.qsize.return_value = 1
        
        queue = SageQueueDescriptor(queue_id="test_ops")
        
        # 测试操作
        queue.put("sage_item")
        item = queue.get()
        
        # 验证调用
        mock_instance.put.assert_called_once_with("sage_item", block=True, timeout=None)
        mock_instance.get.assert_called_once_with(block=True, timeout=None)


class TestRPCQueueDescriptor:
    """测试RPC队列描述符"""
    
    def test_rpc_queue_creation(self):
        """测试RPC队列创建"""
        queue = RPCQueueDescriptor(
            queue_id="test_rpc",
            server_address="localhost",
            port=8080
        )
        
        assert queue.queue_id == "test_rpc"
        assert queue.queue_type == "rpc"
        assert queue.metadata["server_address"] == "localhost"
        assert queue.metadata["port"] == 8080


class TestDescriptorResolution:
    """测试描述符解析功能"""
    
    def test_resolve_python_descriptor(self):
        """测试解析Python描述符"""
        queue = PythonQueueDescriptor(queue_id="test_resolve")
        resolved = resolve_descriptor(queue)
        
        # 解析应该返回底层队列实例
        assert resolved is not None
        assert hasattr(resolved, 'put')
        assert hasattr(resolved, 'get')


class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_queue_id(self):
        """测试无效队列ID"""
        with pytest.raises(ValueError, match="queue_id must be a non-empty string"):
            PythonQueueDescriptor(queue_id="")
    
    def test_invalid_parameters(self):
        """测试无效参数"""
        with pytest.raises(ValueError):
            PythonQueueDescriptor(queue_id="test", maxsize=-1)


if __name__ == "__main__":
    # 运行测试
    test_suite = [
        TestBaseQueueDescriptor(),
        TestPythonQueueDescriptor(),
        TestRayQueueDescriptor(),
        TestSageQueueDescriptor(),
        TestRPCQueueDescriptor(),
        TestDescriptorResolution(),
        TestErrorHandling()
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
        
        print("\n🎉 All tests passed! The inheritance-based queue architecture is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
