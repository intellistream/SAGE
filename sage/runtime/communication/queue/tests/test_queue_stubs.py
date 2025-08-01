"""
Tests for Queue Stubs and Conversion

测试队列 Stub 实现和转换功能
"""

import unittest
import tempfile
import os
from typing import Any

from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor
from sage.runtime.communication.queue_stubs import (
    LocalQueueStub,
    SharedMemoryQueueStub,
    initialize_queue_stubs,
    list_supported_queue_types,
    create_local_queue,
    create_shm_queue
)


class TestQueueStubsBasic(unittest.TestCase):
    """基础队列 Stub 测试"""
    
    def setUp(self):
        """测试设置"""
        initialize_queue_stubs()
    
    def test_local_queue_stub(self):
        """测试本地队列 Stub"""
        # 创建描述符
        descriptor = QueueDescriptor.create_local_queue(
            queue_id="test_local",
            maxsize=10
        )
        
        # 从描述符创建队列
        queue_stub = LocalQueueStub.from_descriptor(descriptor)
        
        # 测试基本操作
        self.assertTrue(queue_stub.empty())
        self.assertEqual(queue_stub.qsize(), 0)
        
        # 测试 put/get
        test_data = "test_message"
        queue_stub.put(test_data)
        self.assertFalse(queue_stub.empty())
        self.assertEqual(queue_stub.qsize(), 1)
        
        retrieved = queue_stub.get()
        self.assertEqual(retrieved, test_data)
        self.assertTrue(queue_stub.empty())
    
    def test_shared_memory_queue_stub(self):
        """测试共享内存队列 Stub"""
        # 创建描述符
        descriptor = QueueDescriptor.create_shm_queue(
            shm_name="test_shm",
            queue_id="test_shm_queue",
            maxsize=20
        )
        
        # 从描述符创建队列
        queue_stub = SharedMemoryQueueStub.from_descriptor(descriptor)
        
        # 测试基本操作
        self.assertTrue(queue_stub.empty())
        
        # 测试 put/get
        test_data = {"key": "value", "number": 42}
        queue_stub.put(test_data)
        
        retrieved = queue_stub.get()
        self.assertEqual(retrieved, test_data)
        
        # 清理
        queue_stub.close()
    
    def test_descriptor_serialization(self):
        """测试描述符序列化"""
        # 创建各种类型的描述符
        descriptors = [
            QueueDescriptor.create_local_queue("local_test", maxsize=100),
            QueueDescriptor.create_shm_queue("shm_test", "shm_queue_test", maxsize=200),
            QueueDescriptor.create_sage_queue("sage_test", maxsize=300)
        ]
        
        for original_desc in descriptors:
            # 序列化为 JSON
            json_str = original_desc.to_json()
            self.assertIsInstance(json_str, str)
            self.assertIn(original_desc.queue_id, json_str)
            
            # 从 JSON 反序列化
            restored_desc = QueueDescriptor.from_json(json_str)
            
            # 验证内容一致
            self.assertEqual(original_desc.queue_id, restored_desc.queue_id)
            self.assertEqual(original_desc.queue_type, restored_desc.queue_type)
            self.assertEqual(original_desc.metadata, restored_desc.metadata)
    
    def test_queue_stub_registry(self):
        """测试队列 Stub 注册机制"""
        supported_types = list_supported_queue_types()
        self.assertIsInstance(supported_types, list)
        self.assertIn("local", supported_types)
        self.assertIn("shm", supported_types)
    
    def test_resolve_descriptor(self):
        """测试描述符解析"""
        # 测试本地队列解析
        local_desc = QueueDescriptor.create_local_queue("resolve_test")
        local_queue = resolve_descriptor(local_desc)
        
        # 验证队列类型
        self.assertIsInstance(local_queue, LocalQueueStub)
        
        # 测试队列功能
        local_queue.put("resolve_test_data")
        data = local_queue.get()
        self.assertEqual(data, "resolve_test_data")


class TestQueueConversion(unittest.TestCase):
    """队列转换测试"""
    
    def test_local_queue_conversion(self):
        """测试本地队列的双向转换"""
        from queue import Queue
        
        # 创建原始 Python Queue
        original_queue = Queue(maxsize=5)
        original_queue.put("original_data")
        
        # 从原始队列创建 Stub
        stub = LocalQueueStub.from_queue(
            original_queue,
            queue_id="conversion_test"
        )
        
        # 验证数据保持
        data = stub.get()
        self.assertEqual(data, "original_data")
        
        # 获取描述符
        descriptor = stub.to_descriptor()
        self.assertEqual(descriptor.queue_id, "conversion_test")
        self.assertEqual(descriptor.queue_type, "local")
        
        # 从描述符重建队列
        new_stub = LocalQueueStub.from_descriptor(descriptor)
        self.assertIsInstance(new_stub, LocalQueueStub)
    
    def test_descriptor_metadata_preservation(self):
        """测试描述符元数据保持"""
        # 创建带有自定义元数据的描述符
        descriptor = QueueDescriptor.create_sage_queue(
            queue_id="metadata_test",
            maxsize=2048,
            auto_cleanup=False,
            namespace="test_namespace",
            enable_multi_tenant=False
        )
        
        # 验证元数据
        self.assertEqual(descriptor.metadata['maxsize'], 2048)
        self.assertEqual(descriptor.metadata['auto_cleanup'], False)
        self.assertEqual(descriptor.metadata['namespace'], "test_namespace")
        self.assertEqual(descriptor.metadata['enable_multi_tenant'], False)
        
        # 序列化和反序列化
        json_str = descriptor.to_json()
        restored = QueueDescriptor.from_json(json_str)
        
        # 验证元数据保持
        self.assertEqual(restored.metadata, descriptor.metadata)


class TestConvenienceFunctions(unittest.TestCase):
    """便利函数测试"""
    
    def test_create_local_queue(self):
        """测试创建本地队列的便利函数"""
        queue = create_local_queue("convenience_local", maxsize=15)
        
        # 验证队列类型
        self.assertIsInstance(queue, LocalQueueStub)
        
        # 测试功能
        queue.put("convenience_test")
        data = queue.get()
        self.assertEqual(data, "convenience_test")
    
    def test_create_shm_queue(self):
        """测试创建共享内存队列的便利函数"""
        queue = create_shm_queue(
            shm_name="convenience_shm",
            queue_id="convenience_shm_queue",
            maxsize=25
        )
        
        # 验证队列类型  
        self.assertIsInstance(queue, SharedMemoryQueueStub)
        
        # 测试功能
        test_data = [1, 2, 3, "test"]
        queue.put(test_data)
        retrieved = queue.get()
        self.assertEqual(retrieved, test_data)
        
        # 清理
        queue.close()


def run_sage_queue_tests():
    """运行 SAGE Queue 相关测试（如果可用）"""
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        from sage.runtime.communication.queue_stubs import SageQueueStub, create_sage_queue
        
        print("\n=== SAGE Queue 测试 ===")
        
        # 测试 SAGE Queue Stub
        descriptor = QueueDescriptor.create_sage_queue(
            queue_id="test_sage",
            maxsize=1024,
            auto_cleanup=True
        )
        
        sage_stub = resolve_descriptor(descriptor)
        print(f"SAGE Queue Stub 创建成功: {sage_stub}")
        
        # 测试操作
        sage_stub.put("SAGE test data")
        data = sage_stub.get()
        print(f"SAGE Queue 操作测试成功: {data}")
        
        # 测试统计信息
        stats = sage_stub.get_stats()
        print(f"SAGE Queue 统计信息: {stats}")
        
        sage_stub.close()  
        print("SAGE Queue 测试完成")
        
    except ImportError:
        print("SAGE Queue 不可用，跳过 SAGE Queue 测试")
    except Exception as e:
        print(f"SAGE Queue 测试失败: {e}")


def run_ray_queue_tests():
    """运行 Ray Queue 相关测试（如果可用）"""
    try:
        import ray
        from sage.runtime.communication.queue_stubs import RayQueueStub, create_ray_queue
        
        print("\n=== Ray Queue 测试 ===")
        
        # 初始化 Ray
        if not ray.is_initialized():
            ray.init(local_mode=True)
        
        # 测试 Ray Queue
        ray_queue = create_ray_queue("test_ray", maxsize=50)
        print(f"Ray Queue 创建成功: {ray_queue}")
        
        # 测试操作  
        ray_queue.put("Ray test data")
        data = ray_queue.get()
        print(f"Ray Queue 操作测试成功: {data}")
        
        print("Ray Queue 测试完成")
        
    except ImportError:
        print("Ray 不可用，跳过 Ray Queue 测试")
    except Exception as e:
        print(f"Ray Queue 测试失败: {e}")


def main():
    """运行所有测试"""
    print("开始运行队列 Stub 测试...")
    
    # 运行基础单元测试
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # 运行可选的 SAGE Queue 和 Ray Queue 测试
    run_sage_queue_tests()
    run_ray_queue_tests()
    
    print("\n所有测试运行完成！")


if __name__ == "__main__":
    main()
