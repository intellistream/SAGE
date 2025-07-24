#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 基本功能测试
Basic functionality test for SAGE high-performance memory-mapped queue
"""

import os
import sys
import time
import multiprocessing
import threading
from typing import List, Dict, Any

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("请先运行 ../build.sh 编译C库")
    sys.exit(1)


def test_basic_operations():
    """测试基本队列操作"""
    print("\n=== 测试基本操作 ===")
    
    queue_name = "test_basic"
    destroy_queue(queue_name)  # 清理可能存在的旧队列
    
    try:
        # 创建队列
        queue = SageQueue(queue_name, maxsize=1024)
        print(f"✓ 创建队列: {queue_name}")
        
        # 测试put/get
        test_items = [
            "Hello, SAGE!",
            42,
            [1, 2, 3, 4, 5],
            {"key": "value", "number": 123},
            ("tuple", "data")
        ]
        
        # 放入数据
        for item in test_items:
            queue.put(item)
            print(f"  Put: {item}")
        
        # 取出数据
        results = []
        for _ in range(len(test_items)):
            item = queue.get()
            results.append(item)
            print(f"  Get: {item}")
        
        # 验证结果
        assert results == test_items, "数据不匹配!"
        print("✓ 基本操作测试通过")
        
        # 测试统计信息
        stats = queue.get_stats()
        print(f"✓ 队列统计: {stats}")
        
        queue.close()
        
    except Exception as e:
        print(f"✗ 基本操作测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_queue_states():
    """测试队列状态检查"""
    print("\n=== 测试队列状态 ===")
    
    queue_name = "test_states"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=1024)
        
        # 测试空队列
        assert queue.empty(), "新队列应该为空"
        assert not queue.full(), "新队列不应该满"
        assert queue.qsize() == 0, "新队列大小应该为0"
        print("✓ 空队列状态正确")
        
        # 添加一些数据
        queue.put("test1")
        queue.put("test2")
        
        assert not queue.empty(), "有数据的队列不应该为空"
        assert queue.qsize() > 0, "有数据的队列大小应该>0"
        print("✓ 非空队列状态正确")
        
        # 测试nowait操作
        queue.put_nowait("test3")
        item = queue.get_nowait()
        assert item == "test1", f"预期'test1'，得到'{item}'"
        print("✓ nowait操作正确")
        
        queue.close()
        
    except Exception as e:
        print(f"✗ 队列状态测试失败: {e}")
        import traceback
        traceback.print_exc()


def producer_process(queue_name: str, producer_id: int, message_count: int):
    """生产者进程"""
    try:
        queue = SageQueue(queue_name)
        print(f"生产者{producer_id}: 开始生产{message_count}条消息")
        
        for i in range(message_count):
            message = {
                'producer_id': producer_id,
                'message_id': i,
                'content': f"来自生产者{producer_id}的消息{i}",
                'timestamp': time.time(),
                'data': list(range(i, i + 5))  # 一些测试数据
            }
            
            queue.put(message, timeout=5.0)
            if i % 10 == 0:
                print(f"生产者{producer_id}: 已发送{i+1}/{message_count}条消息")
            
            time.sleep(0.01)  # 模拟处理时间
        
        print(f"✓ 生产者{producer_id}: 完成，共发送{message_count}条消息")
        queue.close()
        
    except Exception as e:
        print(f"✗ 生产者{producer_id}出错: {e}")


def consumer_process(queue_name: str, consumer_id: int, expected_messages: int):
    """消费者进程"""
    try:
        queue = SageQueue(queue_name)
        print(f"消费者{consumer_id}: 开始消费，预期{expected_messages}条消息")
        
        received_messages = []
        start_time = time.time()
        timeout_duration = 30.0  # 30秒超时
        
        while len(received_messages) < expected_messages:
            try:
                # 检查超时
                if time.time() - start_time > timeout_duration:
                    print(f"消费者{consumer_id}: 超时，只接收到{len(received_messages)}/{expected_messages}条消息")
                    break
                
                message = queue.get(timeout=1.0)
                received_messages.append(message)
                
                if len(received_messages) % 20 == 0:
                    print(f"消费者{consumer_id}: 已接收{len(received_messages)}/{expected_messages}条消息")
                    
            except Exception as e:
                if "timed out" in str(e):
                    continue  # 继续等待
                else:
                    raise
        
        # 统计结果
        producer_stats = {}
        for msg in received_messages:
            pid = msg.get('producer_id', 'unknown')
            producer_stats[pid] = producer_stats.get(pid, 0) + 1
        
        print(f"✓ 消费者{consumer_id}: 完成，接收{len(received_messages)}条消息")
        print(f"  按生产者统计: {producer_stats}")
        
        queue.close()
        return len(received_messages)
        
    except Exception as e:
        print(f"✗ 消费者{consumer_id}出错: {e}")
        return 0


def test_multiprocess():
    """测试多进程通信"""
    print("\n=== 测试多进程通信 ===")
    
    queue_name = "test_multiprocess"
    destroy_queue(queue_name)
    
    try:
        # 创建主队列
        main_queue = SageQueue(queue_name, maxsize=64*1024)
        print(f"✓ 创建主队列: {queue_name}")
        
        # 配置测试参数
        producer_count = 3
        consumer_count = 2
        messages_per_producer = 50
        total_messages = producer_count * messages_per_producer
        
        print(f"配置: {producer_count}个生产者 × {messages_per_producer}条消息 = {total_messages}条总消息")
        print(f"      {consumer_count}个消费者")
        
        # 启动生产者进程
        producers = []
        for i in range(producer_count):
            p = multiprocessing.Process(
                target=producer_process,
                args=(queue_name, i, messages_per_producer)
            )
            p.start()
            producers.append(p)
        
        # 启动消费者进程
        consumers = []
        expected_per_consumer = total_messages // consumer_count
        for i in range(consumer_count):
            expected = expected_per_consumer + (total_messages % consumer_count if i == 0 else 0)
            p = multiprocessing.Process(
                target=consumer_process,
                args=(queue_name, i, expected)
            )
            p.start()
            consumers.append(p)
        
        # 等待所有进程完成
        print("等待所有生产者完成...")
        for p in producers:
            p.join(timeout=30)
            if p.is_alive():
                print("警告: 生产者进程超时")
                p.terminate()
        
        print("等待所有消费者完成...")
        for p in consumers:
            p.join(timeout=60)
            if p.is_alive():
                print("警告: 消费者进程超时")
                p.terminate()
        
        # 显示最终统计
        stats = main_queue.get_stats()
        print(f"✓ 多进程测试完成")
        print(f"  最终统计: {stats}")
        
        main_queue.close()
        
    except Exception as e:
        print(f"✗ 多进程测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_queue_reference():
    """测试队列引用传递"""
    print("\n=== 测试队列引用传递 ===")
    
    queue_name = "test_reference"
    destroy_queue(queue_name)
    
    try:
        # 创建原始队列
        original_queue = SageQueue(queue_name, maxsize=2048)
        print("✓ 创建原始队列")
        
        # 添加一些测试数据
        test_data = ["ref_test_1", "ref_test_2", "ref_test_3"]
        for item in test_data:
            original_queue.put(item)
        
        # 获取队列引用
        queue_ref = original_queue.get_reference()
        print(f"✓ 获取队列引用: {queue_ref}")
        
        # 通过引用创建新的队列实例
        new_queue = queue_ref.get_queue()
        print("✓ 从引用创建新队列实例")
        
        # 验证数据一致性
        for expected in test_data:
            actual = new_queue.get()
            assert actual == expected, f"数据不匹配: 预期'{expected}', 实际'{actual}'"
        
        print("✓ 队列引用传递测试通过")
        
        original_queue.close()
        new_queue.close()
        
    except Exception as e:
        print(f"✗ 队列引用测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_performance():
    """性能测试"""
    print("\n=== 性能测试 ===")
    
    queue_name = "test_performance"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=1024*1024)  # 1MB缓冲区
        
        # 测试数据
        test_message = {
            'id': 12345,
            'content': 'A' * 100,  # 100字节的内容
            'data': list(range(50)),
            'metadata': {'type': 'performance_test', 'version': '1.0'}
        }
        
        message_count = 10000
        
        # 写入性能测试
        print(f"测试写入性能: {message_count}条消息")
        start_time = time.time()
        
        for i in range(message_count):
            test_message['id'] = i
            queue.put(test_message)
        
        write_time = time.time() - start_time
        write_rate = message_count / write_time
        
        print(f"✓ 写入完成: {write_time:.3f}秒, {write_rate:.0f}消息/秒")
        
        # 读取性能测试
        print(f"测试读取性能: {message_count}条消息")
        start_time = time.time()
        
        for i in range(message_count):
            message = queue.get()
            assert message['content'] == 'A' * 100, "数据验证失败"
        
        read_time = time.time() - start_time
        read_rate = message_count / read_time
        
        print(f"✓ 读取完成: {read_time:.3f}秒, {read_rate:.0f}消息/秒")
        
        # 显示统计
        stats = queue.get_stats()
        print(f"✓ 性能测试完成")
        print(f"  总体吞吐量: {message_count*2/(write_time + read_time):.0f}操作/秒")
        print(f"  缓冲区利用率: {stats['utilization']:.2%}")
        print(f"  总传输字节: 写入={stats['total_bytes_written']}, 读取={stats['total_bytes_read']}")
        
        queue.close()
        
    except Exception as e:
        print(f"✗ 性能测试失败: {e}")
        import traceback
        traceback.print_exc()


def cleanup_test_queues():
    """清理测试队列"""
    print("\n=== 清理测试队列 ===")
    
    test_queues = [
        "test_basic",
        "test_states", 
        "test_multiprocess",
        "test_reference",
        "test_performance"
    ]
    
    for queue_name in test_queues:
        try:
            destroy_queue(queue_name)
            print(f"✓ 清理队列: {queue_name}")
        except:
            pass  # 忽略清理错误


def main():
    """主测试函数"""
    print("SAGE Memory-Mapped Queue 基本功能测试套件")
    print("=" * 50)
    
    # 运行所有测试
    test_basic_operations()
    test_queue_states()
    test_queue_reference()
    test_performance()
    test_multiprocess()  # 最后运行，因为比较耗时
    
    # 清理
    cleanup_test_queues()
    
    print("\n" + "=" * 50)
    print("✓ 所有基本功能测试完成!")


if __name__ == "__main__":
    # 设置多进程启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass  # 已经设置过了
    
    main()
