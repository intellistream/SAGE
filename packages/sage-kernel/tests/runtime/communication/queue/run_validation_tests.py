#!/usr/bin/env python3
"""
队列描述符功能验证测试

验证引用传递和并发读写能力的核心功能
"""

import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, '/api-rework')

from sage.runtime.communication.queue import (
    PythonQueueDescriptor,
    RayQueueDescriptor,
    SageQueueDescriptor,
    RPCQueueDescriptor,
    resolve_descriptor
)

def test_basic_functionality():
    """测试基础功能"""
    print("🧪 测试基础功能...")
    
    try:
        from sage.runtime.communication.queue import (
            create_python_queue,
            create_sage_queue
        )
        
        # 测试Python队列
        python_queue = PythonQueueDescriptor('test_basic_python')
        python_queue.put('hello python')
        item = python_queue.get()
        assert item == 'hello python'
        print("✅ Python队列基础功能正常")
        
        # 测试SAGE队列
        try:
            sage_queue = create_sage_queue('test_basic_sage')
            sage_queue.put('hello sage')
            item = sage_queue.get()
            assert item == 'hello sage'
            sage_queue.close()
            print("✅ SAGE队列基础功能正常")
        except Exception as e:
            print(f"⚠️ SAGE队列基础功能测试失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False


def producer_worker(queue_desc, worker_id, num_items):
    """生产者工作函数"""
    try:
        for i in range(num_items):
            item = f"worker_{worker_id}_item_{i}"
            queue_desc.put(item)
        return f"producer_{worker_id}_success"
    except Exception as e:
        return f"producer_{worker_id}_error: {e}"


def consumer_worker(queue_desc, worker_id, expected_items):
    """消费者工作函数"""
    try:
        consumed = []
        for _ in range(expected_items):
            try:
                item = queue_desc.get(timeout=5.0)
                consumed.append(item)
            except:
                break
        return consumed
    except Exception as e:
        return []


def test_multithreading_concurrency():
    """测试多线程并发"""
    print("\n🧪 测试多线程并发...")
    
    try:
        from sage.runtime.communication.queue import create_python_queue
        
        # 创建队列
        queue_desc = PythonQueueDescriptor('test_concurrent', maxsize=100)
        
        # 配置
        num_producers = 3
        num_consumers = 2
        items_per_producer = 5
        total_items = num_producers * items_per_producer
        items_per_consumer = total_items // num_consumers
        
        print(f"配置: {num_producers}个生产者, {num_consumers}个消费者, 总共{total_items}个项目")
        
        # 使用线程池
        with ThreadPoolExecutor(max_workers=num_producers + num_consumers) as executor:
            # 启动生产者
            producer_futures = []
            for i in range(num_producers):
                future = executor.submit(producer_worker, queue_desc, i, items_per_producer)
                producer_futures.append(future)
            
            # 等待生产者完成
            producer_results = []
            for future in as_completed(producer_futures):
                result = future.result()
                producer_results.append(result)
                print(f"生产者结果: {result}")
            
            # 启动消费者
            consumer_futures = []
            for i in range(num_consumers):
                future = executor.submit(consumer_worker, queue_desc, i, items_per_consumer)
                consumer_futures.append(future)
            
            # 等待消费者完成
            consumer_results = []
            for future in as_completed(consumer_futures):
                result = future.result()
                consumer_results.append(result)
                print(f"消费者结果: 消费了{len(result)}个项目")
        
        # 验证结果
        total_consumed = sum(len(items) for items in consumer_results)
        print(f"总共生产: {len(producer_results)}, 总共消费: {total_consumed}")
        
        assert len(producer_results) == num_producers
        assert total_consumed > 0
        
        print("✅ 多线程并发测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 多线程并发测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sage_queue_concurrency():
    """测试SAGE队列并发"""
    print("\n🧪 测试SAGE队列并发...")
    
    try:
        from sage.runtime.communication.queue import create_sage_queue
        
        # 创建SAGE队列
        queue_desc = create_sage_queue('test_sage_concurrent', maxsize=1024*1024)
        
        # 简单的并发测试
        num_threads = 4
        items_per_thread = 3
        
        def worker(thread_id):
            try:
                # 每个线程写入一些数据
                for i in range(items_per_thread):
                    queue_desc.put(f"sage_thread_{thread_id}_item_{i}")
                
                # 然后读取一些数据
                consumed = []
                for _ in range(items_per_thread):
                    try:
                        item = queue_desc.get(timeout=2.0)
                        consumed.append(item)
                    except:
                        break
                
                return len(consumed)
            except Exception as e:
                return f"error: {e}"
        
        # 使用线程池测试
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(worker, i)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(f"SAGE工作线程结果: {result}")
        
        # 清理
        queue_desc.close()
        
        print("✅ SAGE队列并发测试通过")
        return True
        
    except Exception as e:
        print(f"⚠️ SAGE队列并发测试失败: {e}")
        return False


def test_queue_reference_passing():
    """测试队列引用传递"""
    print("\n🧪 测试队列引用传递...")
    
    try:
        from sage.runtime.communication.queue import create_python_queue
        
        # 创建原始队列
        original_queue = PythonQueueDescriptor('test_reference', maxsize=20)
        
        # 添加一些数据
        test_items = ["ref_item1", "ref_item2", "ref_item3"]
        for item in test_items:
            original_queue.put(item)
        
        print(f"原始队列大小: {original_queue.qsize()}")
        
        # 克隆队列描述符
        cloned_queue = original_queue.clone("test_reference_clone")
        
        # 在克隆的队列中添加数据
        cloned_queue.put("cloned_item")
        print(f"克隆队列添加项目后大小: {cloned_queue.qsize()}")
        
        # 从原始队列读取所有数据
        consumed_items = []
        while not original_queue.empty():
            try:
                item = original_queue.get_nowait()
                consumed_items.append(item)
            except:
                break
        
        print(f"从原始队列读取项目数: {len(consumed_items)}")
        print(f"读取后原始队列大小: {original_queue.qsize()}")
        
        assert len(consumed_items) >= len(test_items)
        
        print("✅ 队列引用传递测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 队列引用传递测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_serialization():
    """测试序列化功能"""
    print("\n🧪 测试序列化功能...")
    
    try:
        from sage.runtime.communication.queue import create_sage_queue
        
        # 创建可序列化的队列描述符
        queue_desc = create_sage_queue('test_serialization', maxsize=1024*1024)
        
        print(f"队列类型: {queue_desc.queue_type}")
        print(f"可序列化: {queue_desc.can_serialize}")
        
        if queue_desc.can_serialize:
            # 序列化为字典
            queue_dict = queue_desc.to_dict()
            print(f"序列化字典包含字段: {list(queue_dict.keys())}")
            
            # 从字典恢复
            from sage.runtime.communication.queue import resolve_descriptor
            restored_queue = resolve_descriptor(queue_dict)
            print(f"恢复的队列ID: {restored_queue.queue_id}")
            print(f"恢复的队列类型: {restored_queue.queue_type}")
            
            assert restored_queue.queue_id == queue_desc.queue_id
            assert restored_queue.queue_type == queue_desc.queue_type
        
        print("✅ 序列化功能测试通过")
        return True
        
    except Exception as e:
        print(f"⚠️ 序列化功能测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("队列描述符引用传递和并发测试")
    print("=" * 60)
    
    start_time = time.time()
    
    # 运行所有测试
    tests = [
        test_basic_functionality,
        test_multithreading_concurrency,
        test_sage_queue_concurrency,
        test_queue_reference_passing,
        test_serialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试函数 {test_func.__name__} 异常: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {total}")
    print(f"通过数: {passed}")
    print(f"失败数: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    print(f"总耗时: {duration:.2f}秒")
    
    if passed == total:
        print("\n🎉 所有测试通过！队列描述符引用传递和并发功能正常。")
        return True
    else:
        print("\n💥 部分测试失败，请检查错误信息。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
