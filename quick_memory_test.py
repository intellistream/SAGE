#!/usr/bin/env python3
"""
快速内存压力测试
"""
import sys
import os
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, 'sage_ext/sage_queue/tests/stress')
from sage_ext.sage_queue.tests.stress.test_multiprocess_stress import (
    stress_producer_worker_func, 
    stress_consumer_worker_func
)

def quick_memory_pressure_test():
    """快速内存压力测试"""
    print("=== 快速内存压力测试 ===")
    
    # 简化的配置
    num_processes = 4
    num_queues = 2
    messages_per_process = 100  # 减少消息数
    message_size = 1024  # 减少消息大小
    test_duration = 10  # 减少测试时间
    
    queue_names = [f"quick_memory_test_{i}" for i in range(num_queues)]
    
    print(f"配置:")
    print(f"  - 进程数: {num_processes}")
    print(f"  - 队列数: {num_queues}")
    print(f"  - 每进程消息数: {messages_per_process}")
    print(f"  - 消息大小: {message_size} bytes")
    print(f"  - 测试时长: {test_duration}s")
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = []
        
        # 启动生产者
        for i in range(num_processes // 2):
            future = executor.submit(
                stress_producer_worker_func,
                i,
                queue_names,
                messages_per_process,
                message_size
            )
            futures.append(('producer', future))
        
        # 启动消费者
        for i in range(num_processes // 2):
            future = executor.submit(
                stress_consumer_worker_func,
                i + num_processes // 2,
                queue_names,
                messages_per_process,
                test_duration
            )
            futures.append(('consumer', future))
        
        # 收集结果
        producer_stats = []
        consumer_stats = []
        
        for worker_type, future in futures:
            try:
                result = future.result(timeout=test_duration + 5)
                if worker_type == 'producer':
                    producer_stats.append(result)
                else:
                    consumer_stats.append(result)
                print(f"{worker_type.capitalize()} {result.get('worker_id', 'unknown')} completed")
            except Exception as e:
                print(f"{worker_type.capitalize()} failed: {e}")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 统计结果
    total_sent = sum(stat['messages_sent'] for stat in producer_stats)
    total_received = sum(stat['messages_received'] for stat in consumer_stats)
    
    print(f"\n=== 测试结果 ===")
    print(f"总耗时: {total_duration:.2f}s")
    print(f"消息发送: {total_sent}")
    print(f"消息接收: {total_received}")
    print(f"消息匹配: {'✓' if total_sent == total_received else '✗'}")
    
    if total_sent > 0 and total_received > 0:
        print("快速内存压力测试通过！")
        return True
    else:
        print("快速内存压力测试失败！")
        return False

if __name__ == "__main__":
    success = quick_memory_pressure_test()
    sys.exit(0 if success else 1)
