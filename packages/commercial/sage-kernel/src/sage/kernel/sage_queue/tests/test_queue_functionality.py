#!/usr/bin/env python3
"""
测试 SAGE Queue 的完整功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sage.extensions.sage_queue.python.sage_queue import SageQueue
import time
import threading
import multiprocessing

def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试基本功能 ===")
    
    try:
        # 创建队列
        queue = SageQueue('test_basic', maxsize=1024)
        print("✓ Queue created successfully")
        
        # 测试空队列状态
        print(f"✓ Queue empty: {queue.empty()}")
        print(f"✓ Queue size: {queue.qsize()}")
        
        # 测试 put/get
        test_data = [
            "Hello, SAGE!",
            {"key": "value", "number": 42},
            [1, 2, 3, 4, 5],
            ("tuple", "data")
        ]
        
        for data in test_data:
            queue.put(data)
            
        print(f"✓ Added {len(test_data)} items, queue size: {queue.qsize()}")
        
        # 获取数据
        retrieved = []
        for _ in range(len(test_data)):
            retrieved.append(queue.get())
            
        print(f"✓ Retrieved data: {retrieved}")
        print(f"✓ Data matches: {retrieved == test_data}")
        
        # 测试非阻塞操作
        try:
            queue.get_nowait()
            print("❌ Should have raised Empty exception")
        except Exception as e:
            print(f"✓ Correctly raised exception for empty queue: {type(e).__name__}")
        
        queue.close()
        print("✓ Queue closed successfully")
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()

def test_threading():
    """测试多线程功能"""
    print("\n=== 测试多线程功能 ===")
    
    try:
        queue = SageQueue('test_threading', maxsize=1024)
        results = []
        
        def producer():
            for i in range(10):
                queue.put(f"Message {i}")
                time.sleep(0.01)
        
        def consumer():
            for i in range(10):
                item = queue.get()
                results.append(item)
                time.sleep(0.01)
        
        # 启动线程
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join()
        consumer_thread.join()
        
        print(f"✓ Threading test completed, received {len(results)} messages")
        print(f"✓ First message: {results[0] if results else 'None'}")
        print(f"✓ Last message: {results[-1] if results else 'None'}")
        
        queue.close()
        
    except Exception as e:
        print(f"❌ Threading test failed: {e}")
        import traceback
        traceback.print_exc()

def test_serialization():
    """测试序列化功能"""
    print("\n=== 测试序列化功能 ===")
    
    try:
        queue = SageQueue('test_serialization', maxsize=1024)
        
        # 测试队列引用的序列化
        ref = queue.get_reference()
        print(f"✓ Got queue reference: {ref}")
        
        # 测试统计信息
        stats = queue.get_stats()
        print(f"✓ Queue stats: {stats}")
        
        queue.close()
        
    except Exception as e:
        print(f"❌ Serialization test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("SAGE Queue 功能测试开始...\n")
    
    test_basic_functionality()
    test_threading()
    test_serialization()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
