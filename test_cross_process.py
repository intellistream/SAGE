#!/usr/bin/env python3
"""测试跨进程队列通信"""

import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

def producer_test(queue_name):
    """生产者进程"""
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        
        queue = SageQueue(queue_name, maxsize=1000)
        
        # 发送一些消息
        for i in range(10):
            message = f"Message {i}"
            queue.put(message, timeout=1.0)
            print(f"Producer sent: {message}")
        
        queue.close()
        return True
        
    except Exception as e:
        print(f"Producer failed: {e}")
        return False

def consumer_test(queue_name):
    """消费者进程"""
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        
        # 等待一下，确保生产者先发送一些消息
        time.sleep(1)
        
        queue = SageQueue(queue_name, maxsize=1000)
        
        messages_received = 0
        for i in range(20):  # 尝试接收更多消息
            try:
                message = queue.get(timeout=0.5)
                messages_received += 1
                print(f"Consumer received: {message}")
            except Exception as e:
                if "timeout" not in str(e).lower():
                    print(f"Consumer error: {e}")
                    
        queue.close()
        return messages_received
        
    except Exception as e:
        print(f"Consumer failed: {e}")
        return 0

def main():
    queue_name = "test_cross_process_queue"
    
    print("Testing cross-process queue communication...")
    
    with ProcessPoolExecutor(max_workers=2) as executor:
        # 启动生产者
        producer_future = executor.submit(producer_test, queue_name)
        
        # 启动消费者
        consumer_future = executor.submit(consumer_test, queue_name)
        
        # 等待结果
        producer_result = producer_future.result(timeout=10)
        consumer_result = consumer_future.result(timeout=10)
        
        print(f"Producer result: {producer_result}")
        print(f"Consumer received {consumer_result} messages")
        
        if producer_result and consumer_result > 0:
            print("✅ Cross-process communication works!")
        else:
            print("❌ Cross-process communication failed!")

if __name__ == "__main__":
    main()
