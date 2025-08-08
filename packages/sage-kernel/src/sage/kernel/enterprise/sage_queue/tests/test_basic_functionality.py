#!/usr/bin/env python3
"""
SAGE Queue 基础功能测试
测试核心的队列操作：put, get, empty, full, qsize 等
"""

import sys
import os
import unittest
import time
import threading
from queue import Empty, Full

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sage.extensions.sage_queue import SageQueue

class TestBasicFunctionality(unittest.TestCase):
    """测试基础功能"""
    
    def setUp(self):
        """每个测试前的设置"""
        self.queue_name = f"test_basic_{int(time.time() * 1000)}"
        self.queue = SageQueue(self.queue_name, maxsize=1024)
    
    def tearDown(self):
        """每个测试后的清理"""
        if hasattr(self, 'queue') and self.queue:
            self.queue.close()
    
    def test_queue_creation(self):
        """测试队列创建"""
        self.assertIsNotNone(self.queue)
        self.assertTrue(self.queue.empty())
        self.assertEqual(self.queue.qsize(), 0)
    
    def test_put_get_string(self):
        """测试字符串 put/get"""
        test_string = "Hello, SAGE!"
        self.queue.put(test_string)
        self.assertFalse(self.queue.empty())
        self.assertEqual(self.queue.qsize(), 1)
        
        result = self.queue.get()
        self.assertEqual(result, test_string)
        self.assertTrue(self.queue.empty())
        self.assertEqual(self.queue.qsize(), 0)
    
    def test_put_get_dict(self):
        """测试字典 put/get"""
        test_dict = {"key": "value", "number": 42, "list": [1, 2, 3]}
        self.queue.put(test_dict)
        result = self.queue.get()
        self.assertEqual(result, test_dict)
    
    def test_put_get_list(self):
        """测试列表 put/get"""
        test_list = [1, 2, 3, "string", {"nested": "dict"}]
        self.queue.put(test_list)
        result = self.queue.get()
        self.assertEqual(result, test_list)
    
    def test_put_get_tuple(self):
        """测试元组 put/get"""
        test_tuple = ("tuple", "data", 123)
        self.queue.put(test_tuple)
        result = self.queue.get()
        self.assertEqual(result, test_tuple)
    
    def test_multiple_items(self):
        """测试多个项目的 put/get"""
        items = ["item1", "item2", "item3"]
        
        # 放入多个项目
        for item in items:
            self.queue.put(item)
        
        self.assertEqual(self.queue.qsize(), len(items))
        
        # 取出多个项目
        results = []
        for _ in range(len(items)):
            results.append(self.queue.get())
        
        self.assertEqual(results, items)
        self.assertTrue(self.queue.empty())
    
    def test_nowait_operations(self):
        """测试非阻塞操作"""
        # 测试 get_nowait 在空队列上
        with self.assertRaises(Empty):
            self.queue.get_nowait()
        
        # 测试 put_nowait 和 get_nowait
        test_item = "nowait_test"
        self.queue.put_nowait(test_item)
        result = self.queue.get_nowait()
        self.assertEqual(result, test_item)
    
    def test_queue_states(self):
        """测试队列状态检查"""
        # 空队列状态
        self.assertTrue(self.queue.empty())
        self.assertFalse(self.queue.full())
        self.assertEqual(self.queue.qsize(), 0)
        
        # 添加一个项目
        self.queue.put("test")
        self.assertFalse(self.queue.empty())
        self.assertEqual(self.queue.qsize(), 1)
        
        # 取出项目
        self.queue.get()
        self.assertTrue(self.queue.empty())
        self.assertEqual(self.queue.qsize(), 0)
    
    def test_queue_reference(self):
        """测试队列引用功能"""
        ref = self.queue.get_reference()
        self.assertIsNotNone(ref)
        self.assertTrue(hasattr(ref, 'name'))
        self.assertTrue(hasattr(ref, 'size'))
    
    def test_queue_stats(self):
        """测试队列统计信息"""
        stats = self.queue.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('buffer_size', stats)
        self.assertIn('available_read', stats)
        self.assertIn('available_write', stats)
    
    def test_context_manager(self):
        """测试上下文管理器"""
        queue_name = f"test_context_{int(time.time() * 1000)}"
        
        with SageQueue(queue_name, maxsize=1024) as queue:
            queue.put("test")
            result = queue.get()
            self.assertEqual(result, "test")
        
        # 队列应该已经关闭


class TestThreadSafety(unittest.TestCase):
    """测试线程安全性"""
    
    def setUp(self):
        self.queue_name = f"test_thread_{int(time.time() * 1000)}"
        self.queue = SageQueue(self.queue_name, maxsize=1024)
        self.results = []
        self.errors = []
    
    def tearDown(self):
        if hasattr(self, 'queue') and self.queue:
            self.queue.close()
    
    def test_concurrent_put_get(self):
        """测试并发 put/get 操作"""
        num_items = 50
        
        def producer():
            try:
                for i in range(num_items):
                    self.queue.put(f"item_{i}")
                    time.sleep(0.001)  # 小延迟
            except Exception as e:
                self.errors.append(f"Producer error: {e}")
        
        def consumer():
            try:
                for i in range(num_items):
                    item = self.queue.get()
                    self.results.append(item)
                    time.sleep(0.001)  # 小延迟
            except Exception as e:
                self.errors.append(f"Consumer error: {e}")
        
        # 启动线程
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join(timeout=10)
        consumer_thread.join(timeout=10)
        
        # 检查结果
        self.assertEqual(len(self.errors), 0, f"Errors occurred: {self.errors}")
        self.assertEqual(len(self.results), num_items)
        
        # 验证所有项目都被正确传递
        expected_items = [f"item_{i}" for i in range(num_items)]
        self.assertEqual(sorted(self.results), sorted(expected_items))


if __name__ == '__main__':
    unittest.main()
