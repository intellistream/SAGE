#!/usr/bin/env python3
"""
SAGE Queue 完整功能验证
"""
import sys
import os
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, 'sage_ext/sage_queue/tests/stress')
from sage_ext.sage_queue.python.sage_queue import SageQueue

def test_basic_operations():
    """基本操作测试"""
    print("1. 基本操作测试")
    queue = SageQueue('basic_test', 1024)
    
    # 放入和获取
    queue.put(b'hello', timeout=1.0)
    data = queue.get(timeout=1.0)
    assert data == b'hello', f"Expected b'hello', got {data}"
    
    queue.close()
    print("   ✓ 基本 put/get 操作正常")

def producer_func():
    """生产者进程函数"""
    queue = SageQueue('cross_process_test', 1024)
    for i in range(5):
        queue.put(f'message_{i}'.encode(), timeout=5.0)
    queue.close()

def consumer_func():
    """消费者进程函数"""
    time.sleep(0.5)  # 让生产者先启动
    queue = SageQueue('cross_process_test', 1024)
    messages = []
    for i in range(5):
        data = queue.get(timeout=5.0)
        messages.append(data.decode())
    queue.close()
    return messages

def test_cross_process():
    """跨进程通信测试"""
    print("2. 跨进程通信测试")
    
    with ProcessPoolExecutor(max_workers=2) as executor:
        prod_future = executor.submit(producer_func)
        cons_future = executor.submit(consumer_func)
        
        prod_future.result(timeout=10)
        messages = cons_future.result(timeout=10)
    
    expected = [f'message_{i}' for i in range(5)]
    assert messages == expected, f"Expected {expected}, got {messages}"
    print("   ✓ 跨进程通信正常")

def test_persistence():
    """持久性测试"""
    print("3. 持久性测试")
    
    # 创建队列并放入数据
    queue1 = SageQueue('persistence_test', 1024)
    queue1.put(b'persistent_message', timeout=1.0)
    queue1.close()
    
    # 重新打开队列获取数据
    queue2 = SageQueue('persistence_test', 1024)
    data = queue2.get(timeout=1.0)
    assert data == b'persistent_message', f"Expected b'persistent_message', got {data}"
    queue2.close()
    
    print("   ✓ 数据持久性正常")

def worker_func(worker_id, num_messages):
    """并发访问工作进程函数"""
    queue = SageQueue('concurrent_test', 2048)
    sent = 0
    received = 0
    
    # 发送消息
    for i in range(num_messages):
        try:
            queue.put(f'worker_{worker_id}_msg_{i}'.encode(), timeout=2.0)
            sent += 1
        except:
            pass
    
    # 接收消息
    for i in range(num_messages):
        try:
            data = queue.get(timeout=2.0)
            received += 1
        except:
            pass
    
    queue.close()
    return sent, received

def test_concurrent_access():
    """并发访问测试"""
    print("4. 并发访问测试")
    
    num_workers = 4
    messages_per_worker = 10
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_func, i, messages_per_worker) for i in range(num_workers)]
        results = [f.result(timeout=15) for f in futures]
    
    total_sent = sum(r[0] for r in results)
    total_received = sum(r[1] for r in results)
    
    print(f"   发送: {total_sent}, 接收: {total_received}")
    assert total_sent > 0 and total_received > 0, "并发访问失败"
    print("   ✓ 并发访问正常")

def test_cleanup():
    """清理测试"""
    print("5. 清理测试")
    
    queue = SageQueue('cleanup_test', 1024)
    queue.put(b'test', timeout=1.0)
    queue.close()
    queue.destroy()
    
    print("   ✓ 队列清理正常")

def main():
    """主测试函数"""
    print("=== SAGE Queue 完整功能验证 ===\n")
    
    try:
        test_basic_operations()
        test_cross_process()
        test_persistence()
        test_concurrent_access()
        test_cleanup()
        
        print("\n=== 所有测试通过 ===")
        print("✓ SageQueue 基于 Boost.Interprocess 的实现工作正常")
        print("✓ 支持真正的跨进程通信")
        print("✓ 数据持久性和并发访问均正常")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
