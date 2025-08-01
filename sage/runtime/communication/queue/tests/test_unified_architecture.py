"""
测试统一的 QueueDescriptor 架构

验证统一队列架构的功能完整性
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from sage.runtime.communication.queue import QueueDescriptor, resolve_descriptor


class TestUnifiedQueueArchitecture:
    """测试统一队列架构"""
    
    def test_local_queue_creation_and_operations(self):
        """测试本地队列创建和基本操作"""
        queue = QueueDescriptor.create_local_queue(
            queue_id="test_local",
            maxsize=10
        )
        
        # 测试基本属性
        assert queue.queue_id == "test_local"
        assert queue.queue_type == "local"
        assert queue.metadata["maxsize"] == 10
        assert queue.can_serialize is True
        
        # 测试队列操作
        assert queue.empty() is True
        assert queue.qsize() == 0
        
        queue.put("item1")
        queue.put("item2")
        
        assert queue.empty() is False
        assert queue.qsize() == 2
        
        item1 = queue.get()
        item2 = queue.get()
        
        assert item1 == "item1"
        assert item2 == "item2"
        assert queue.empty() is True
    
    def test_shm_queue_creation_and_operations(self):
        """测试共享内存队列创建和基本操作"""
        queue = QueueDescriptor.create_shm_queue(
            shm_name="test_shm",
            queue_id="test_shm_queue",
            maxsize=100
        )
        
        # 测试基本属性
        assert queue.queue_id == "test_shm_queue"
        assert queue.queue_type == "shm"
        assert queue.metadata["shm_name"] == "test_shm"
        assert queue.metadata["maxsize"] == 100
        
        # 测试队列操作（可能会回退到本地队列）
        queue.put("shm_item")
        item = queue.get()
        assert item == "shm_item"
    
    @patch('sage_ext.sage_queue.python.sage_queue.SageQueue')
    def test_sage_queue_creation_and_operations(self, mock_sage_queue):
        """测试 SAGE 队列创建和基本操作"""
        # 设置 mock
        mock_instance = MagicMock()
        mock_sage_queue.return_value = mock_instance
        mock_instance.put.return_value = None
        mock_instance.get.return_value = "sage_item"
        mock_instance.empty.return_value = False
        mock_instance.qsize.return_value = 1
        
        queue = QueueDescriptor.create_sage_queue(
            queue_id="test_sage",
            maxsize=1024 * 1024,
            auto_cleanup=True,
            namespace="test_ns"
        )
        
        # 测试基本属性
        assert queue.queue_id == "test_sage"
        assert queue.queue_type == "sage_queue"
        assert queue.metadata["maxsize"] == 1024 * 1024
        assert queue.metadata["auto_cleanup"] is True
        assert queue.metadata["namespace"] == "test_ns"
        
        # 测试队列操作
        queue.put("sage_item")
        item = queue.get()
        
        # 验证底层 SAGE Queue 被正确调用
        mock_sage_queue.assert_called_once_with(
            name="test_sage",
            maxsize=1024 * 1024,
            auto_cleanup=True,
            namespace="test_ns",
            enable_multi_tenant=True
        )
        mock_instance.put.assert_called_once_with("sage_item", block=True, timeout=None)
        mock_instance.get.assert_called_once_with(block=True, timeout=None)
    
    @patch('ray.util.Queue')
    @patch('ray.is_initialized')
    def test_ray_queue_creation(self, mock_ray_initialized, mock_ray_queue):
        """测试 Ray 队列创建"""
        # 设置 mock
        mock_ray_initialized.return_value = True
        mock_queue_instance = MagicMock()
        mock_ray_queue.return_value = mock_queue_instance
        
        queue = QueueDescriptor.create_ray_queue(
            queue_id="test_ray",
            maxsize=100
        )
        
        # 测试基本属性
        assert queue.queue_id == "test_ray"
        assert queue.queue_type == "ray_queue"
        assert queue.metadata["maxsize"] == 100
        
        # 触发队列初始化
        queue.put("ray_item")
        
        # 验证 Ray Queue 被正确创建
        mock_ray_queue.assert_called_once_with(maxsize=100)
    
    def test_queue_serialization(self):
        """测试队列序列化功能"""
        queue = QueueDescriptor.create_local_queue(
            queue_id="test_serialization",
            maxsize=50
        )
        
        # 测试字典序列化
        data = queue.to_dict()
        assert data["queue_id"] == "test_serialization"
        assert data["queue_type"] == "local"
        assert data["metadata"]["maxsize"] == 50
        assert data["can_serialize"] is True
        
        # 测试 JSON 序列化
        json_str = queue.to_json()
        assert isinstance(json_str, str)
        assert "test_serialization" in json_str
        
        # 测试反序列化
        restored_queue = QueueDescriptor.from_dict(data)
        assert restored_queue.queue_id == queue.queue_id
        assert restored_queue.queue_type == queue.queue_type
        assert restored_queue.metadata == queue.metadata
        
        restored_from_json = QueueDescriptor.from_json(json_str)
        assert restored_from_json.queue_id == queue.queue_id
    
    def test_lazy_loading(self):
        """测试懒加载功能"""
        queue = QueueDescriptor.create_local_queue(queue_id="test_lazy")
        
        # 初始状态：未初始化
        assert queue.is_initialized() is False
        assert queue.queue_instance is None
        
        # 首次使用时初始化
        queue.put("lazy_item")
        assert queue.is_initialized() is True
        assert queue.queue_instance is not None
        
        # 清除缓存
        queue.clear_cache()
        assert queue.is_initialized() is False
        assert queue.queue_instance is None
        
        # 再次使用时重新初始化
        try:
            item = queue.get(block=False)  # 可能抛出异常，但会触发初始化
        except:
            pass  # 忽略异常，我们只关心是否触发了初什
        assert queue.is_initialized() is True
    
    def test_clone_functionality(self):
        """测试克隆功能"""
        original = QueueDescriptor.create_local_queue(
            queue_id="original",
            maxsize=100
        )
        
        # 克隆
        clone = original.clone("cloned")
        
        # 验证克隆结果
        assert clone.queue_id == "cloned"
        assert clone.queue_type == original.queue_type
        assert clone.metadata == original.metadata
        assert clone.can_serialize is True
        assert clone.is_initialized() is False
        
        # 验证克隆是独立的
        original.put("original_item")
        assert original.qsize() == 1
        assert clone.qsize() == 0  # 独立的队列实例
    
    def test_from_existing_queue(self):
        """测试从现有队列创建描述符"""
        import queue
        
        # 创建标准队列
        existing_queue = queue.Queue(maxsize=20)
        existing_queue.put("existing_item")
        
        # 从现有队列创建描述符
        descriptor = QueueDescriptor.from_existing_queue(
            queue_instance=existing_queue,
            queue_type="local",
            queue_id="from_existing",
            custom_metadata="test"
        )
        
        # 验证属性
        assert descriptor.queue_id == "from_existing"
        assert descriptor.queue_type == "local"
        assert descriptor.can_serialize is False  # 包含不可序列化对象
        assert descriptor.metadata["custom_metadata"] == "test"
        
        # 验证队列操作
        item = descriptor.get()
        assert item == "existing_item"
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效队列类型
        with pytest.raises(ValueError, match="Unsupported queue type"):
            QueueDescriptor(
                queue_id="invalid",
                queue_type="invalid_type",
                metadata={}
            )._ensure_queue_initialized()
        
        # 测试无效参数
        with pytest.raises(ValueError, match="queue_id must be a non-empty string"):
            QueueDescriptor(
                queue_id="",
                queue_type="local",
                metadata={}
            )
        
        with pytest.raises(ValueError, match="queue_type must be a non-empty string"):
            QueueDescriptor(
                queue_id="test",
                queue_type="",
                metadata={}
            )
    
    def test_queue_methods_coverage(self):
        """测试所有队列方法的覆盖性"""
        queue = QueueDescriptor.create_local_queue(queue_id="coverage_test")
        
        # 测试所有标准方法存在
        assert hasattr(queue, 'put')
        assert hasattr(queue, 'get')
        assert hasattr(queue, 'put_nowait')
        assert hasattr(queue, 'get_nowait')
        assert hasattr(queue, 'empty')
        assert hasattr(queue, 'qsize')
        assert hasattr(queue, 'full')
        
        # 测试方法可调用
        assert callable(queue.put)
        assert callable(queue.get)
        assert callable(queue.empty)
        assert callable(queue.qsize)
        assert callable(queue.full)


if __name__ == "__main__":
    # 运行测试
    test = TestUnifiedQueueArchitecture()
    
    print("Running unified queue architecture tests...")
    
    try:
        test.test_local_queue_creation_and_operations()
        print("✓ Local queue tests passed")
        
        test.test_shm_queue_creation_and_operations()
        print("✓ Shared memory queue tests passed")
        
        test.test_queue_serialization()
        print("✓ Serialization tests passed")
        
        test.test_lazy_loading()
        print("✓ Lazy loading tests passed")
        
        test.test_clone_functionality()
        print("✓ Clone functionality tests passed")
        
        test.test_from_existing_queue()
        print("✓ From existing queue tests passed")
        
        test.test_error_handling()
        print("✓ Error handling tests passed")
        
        test.test_queue_methods_coverage()
        print("✓ Queue methods coverage tests passed")
        
        print("\n🎉 All tests passed! The unified queue architecture is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
