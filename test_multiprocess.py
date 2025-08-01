#!/usr/bin/env python3
import sys
import os
import multiprocessing as mp
import time
sys.path.insert(0, 'sage_ext/sage_queue/tests/stress')

from sage_ext.sage_queue.python.sage_queue import SageQueue

def producer_process(queue_name, num_messages):
    """生产者进程"""
    print(f"Producer starting: {queue_name}")
    queue = SageQueue(queue_name, 1024)
    
    for i in range(num_messages):
        message = f"Message {i}".encode()
        try:
            queue.put(message, timeout=5.0)
            print(f"Producer sent: Message {i}")
        except Exception as e:
            print(f"Producer failed to put message {i}: {e}")
        time.sleep(0.1)
    
    queue.close()
    print(f"Producer finished: {queue_name}")

def consumer_process(queue_name, expected_messages):
    """消费者进程"""
    print(f"Consumer starting: {queue_name}")
    time.sleep(0.5)  # 让生产者先启动
    
    queue = SageQueue(queue_name, 1024)
    received = 0
    
    for i in range(expected_messages):
        try:
            data = queue.get(timeout=10.0)
            print(f"Consumer received: {data.decode()}")
            received += 1
        except Exception as e:
            print(f"Consumer error: {e}")
            break
        time.sleep(0.1)
    
    queue.close()
    print(f"Consumer finished: {queue_name}, received {received} messages")
    return received

def test_multiprocess():
    """测试多进程通信"""
    print("=== 多进程生产者-消费者测试 ===")
    
    queue_name = "multiprocess_test"
    num_messages = 5
    
    # 启动生产者进程
    producer = mp.Process(target=producer_process, args=(queue_name, num_messages))
    
    # 启动消费者进程
    consumer = mp.Process(target=consumer_process, args=(queue_name, num_messages))
    
    # 启动进程
    producer.start()
    consumer.start()
    
    # 等待完成
    producer.join(timeout=20)
    consumer.join(timeout=20)
    
    if producer.is_alive():
        producer.terminate()
        print("Producer was terminated due to timeout")
    
    if consumer.is_alive():
        consumer.terminate()
        print("Consumer was terminated due to timeout")
    
    print("多进程测试完成")

if __name__ == "__main__":
    test_multiprocess()
