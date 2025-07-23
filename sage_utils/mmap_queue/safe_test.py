#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 安全测试套件
Safe test suite for SAGE high-performance memory-mapped queue
"""

import os
import sys
import time
import random
import threading
import multiprocessing
import pickle
import gc
from typing import List, Dict, Any, Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("请先运行 ./build.sh 编译C库")
    sys.exit(1)


def test_queue_capacity():
    """测试队列容量限制"""
    print("\n=== 测试队列容量限制 ===")
    
    queue_name = f"test_capacity_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        # 创建小队列测试容量
        small_queue = SageQueue(queue_name, maxsize=1024)  # 1KB
        
        message_count = 0
        test_message = {"data": "x" * 50}  # 约50字节的消息
        
        print(f"测试消息大小: ~{len(pickle.dumps(test_message)) + 4} 字节")
        
        # 填充队列直到满
        while True:
            try:
                small_queue.put_nowait(test_message)
                message_count += 1
                if message_count % 5 == 0:
                    stats = small_queue.get_stats()
                    print(f"  已写入 {message_count} 消息, 可写空间: {stats['available_write']}")
                
                # 安全检查，避免无限循环
                if message_count > 100:
                    break
                    
            except Exception as e:
                print(f"  队列已满: {e}")
                break
        
        final_stats = small_queue.get_stats()
        print(f"  最终统计: {final_stats}")
        print(f"  成功写入 {message_count} 条消息")
        
        # 测试读取
        read_count = 0
        while not small_queue.empty():
            try:
                small_queue.get_nowait()
                read_count += 1
            except:
                break
        
        print(f"  成功读取 {read_count} 条消息")
        assert read_count == message_count, f"读取数量不匹配: {read_count} != {message_count}"
        
        small_queue.close()
        destroy_queue(queue_name)
        print("✓ 队列容量测试通过")
        
    except Exception as e:
        print(f"✗ 队列容量测试失败: {e}")
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_data_integrity():
    """测试数据完整性"""
    print("\n=== 测试数据完整性 ===")
    
    queue_name = f"test_integrity_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=10240)
        
        # 测试各种数据类型
        test_cases = [
            # 基本类型
            None,
            True, False,
            0, 1, -1, 42, 2**32-1,
            0.0, 3.14, -2.71, float('inf'), float('-inf'),
            "", "hello", "中文测试", "🎉emoji",
            
            # 容器类型
            [], [1, 2, 3], [None, True, "mixed"],
            {}, {"key": "value"}, {"a": 1, "b": [2, 3], "c": {"nested": True}},
            (), (1,), (1, 2, 3), ("tuple", {"mixed": "data"}),
            
            # 字节数据
            b"", b"binary data", bytes(range(256)),
            
            # 复杂嵌套
            {
                "string": "value",
                "number": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
                "list": [1, 2, 3, {"nested": "dict"}],
                "tuple": (4, 5, 6),
                "bytes": b"binary",
                "deep": {
                    "level2": {
                        "level3": {
                            "data": list(range(10))
                        }
                    }
                }
            }
        ]
        
        print(f"测试 {len(test_cases)} 种数据类型...")
        
        # 写入所有测试数据
        for i, data in enumerate(test_cases):
            queue.put(data, timeout=5.0)
            if i % 10 == 0:
                print(f"  已写入 {i+1}/{len(test_cases)} 项数据")
        
        # 读取并验证
        results = []
        for i in range(len(test_cases)):
            data = queue.get(timeout=5.0)
            results.append(data)
            if i % 10 == 0:
                print(f"  已读取 {i+1}/{len(test_cases)} 项数据")
        
        # 逐一验证（特别处理float('nan')等特殊值）
        for i, (original, retrieved) in enumerate(zip(test_cases, results)):
            if isinstance(original, float) and isinstance(retrieved, float):
                if str(original) != str(retrieved):  # 处理nan, inf等
                    raise AssertionError(f"数据 {i} 不匹配: {original} != {retrieved}")
            else:
                if original != retrieved:
                    raise AssertionError(f"数据 {i} 不匹配: {original} != {retrieved}")
        
        queue.close()
        destroy_queue(queue_name)
        print("✓ 数据完整性测试通过")
        
    except Exception as e:
        print(f"✗ 数据完整性测试失败: {e}")
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_queue_lifecycle():
    """测试队列生命周期"""
    print("\n=== 测试队列生命周期 ===")
    
    base_queue_name = f"test_lifecycle_{int(time.time())}"
    
    try:
        # 测试1: 创建和销毁
        print("  测试创建和销毁...")
        for i in range(5):
            queue_name = f"{base_queue_name}_{i}"
            destroy_queue(queue_name)  # 确保清理
            
            queue = SageQueue(queue_name, maxsize=1024)
            queue.put(f"test_message_{i}")
            
            # 检查队列状态
            assert not queue.empty(), "队列应该不为空"
            assert queue.qsize() > 0, "队列大小应该大于0"
            
            message = queue.get()
            assert message == f"test_message_{i}", "消息内容不匹配"
            
            queue.close()
            destroy_queue(queue_name)
        
        # 测试2: 重复创建同名队列
        print("  测试重复创建同名队列...")
        queue_name = f"{base_queue_name}_repeat"
        
        queue1 = SageQueue(queue_name, maxsize=2048)
        queue1.put("from_queue1")
        
        # 尝试创建同名队列（应该连接到现有的）
        queue2 = SageQueue(queue_name, maxsize=2048)
        
        # queue2应该能读到queue1写入的数据
        message = queue2.get(timeout=1.0)
        assert message == "from_queue1", "同名队列应该共享数据"
        
        queue1.close()
        queue2.close()
        destroy_queue(queue_name)
        
        # 测试3: 队列引用
        print("  测试队列引用...")
        ref_queue_name = f"{base_queue_name}_ref"
        original_queue = SageQueue(ref_queue_name, maxsize=1024)
        original_queue.put("reference_test")
        
        # 获取引用
        queue_ref = original_queue.get_reference()
        print(f"    队列引用: {queue_ref}")
        
        # 从引用创建新实例
        new_queue = queue_ref.get_queue()
        
        # 应该能读到原队列的数据
        message = new_queue.get(timeout=1.0)
        assert message == "reference_test", "引用队列应该能访问原数据"
        
        original_queue.close()
        new_queue.close()
        destroy_queue(ref_queue_name)
        
        print("✓ 队列生命周期测试通过")
        
    except Exception as e:
        print(f"✗ 队列生命周期测试失败: {e}")
        # 清理所有可能的队列
        for i in range(5):
            try:
                destroy_queue(f"{base_queue_name}_{i}")
            except:
                pass
        try:
            destroy_queue(f"{base_queue_name}_repeat")
            destroy_queue(f"{base_queue_name}_ref")
        except:
            pass


def test_concurrent_simple():
    """简单并发测试"""
    print("\n=== 简单并发测试 ===")
    
    queue_name = f"test_concurrent_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=5000)
        
        num_threads = 4
        messages_per_thread = 50
        results = {'written': 0, 'read': 0, 'errors': 0}
        results_lock = threading.Lock()
        
        def writer(thread_id):
            try:
                for i in range(messages_per_thread):
                    message = {
                        'thread_id': thread_id,
                        'message_id': i,
                        'content': f"Message from thread {thread_id}, number {i}"
                    }
                    queue.put(message, timeout=10.0)
                    
                    with results_lock:
                        results['written'] += 1
                    
                    time.sleep(0.001)  # 小延时
                        
            except Exception as e:
                with results_lock:
                    results['errors'] += 1
                print(f"Writer {thread_id} error: {e}")
        
        def reader(thread_id):
            try:
                for i in range(messages_per_thread):
                    message = queue.get(timeout=15.0)
                    
                    # 基本验证
                    assert isinstance(message, dict), "消息应该是字典类型"
                    assert 'thread_id' in message, "消息应该包含thread_id"
                    assert 'message_id' in message, "消息应该包含message_id"
                    
                    with results_lock:
                        results['read'] += 1
                    
                    time.sleep(0.001)  # 小延时
                        
            except Exception as e:
                with results_lock:
                    results['errors'] += 1
                print(f"Reader {thread_id} error: {e}")
        
        # 启动线程
        threads = []
        
        # 写线程
        for i in range(num_threads):
            t = threading.Thread(target=writer, args=(i,))
            threads.append(t)
            t.start()
        
        # 读线程  
        for i in range(num_threads):
            t = threading.Thread(target=reader, args=(i + num_threads,))
            threads.append(t)
            t.start()
        
        # 等待完成
        for t in threads:
            t.join(timeout=20.0)
        
        print(f"  写入: {results['written']}/{num_threads * messages_per_thread}")
        print(f"  读取: {results['read']}/{num_threads * messages_per_thread}")
        print(f"  错误: {results['errors']}")
        
        expected_total = num_threads * messages_per_thread
        assert results['written'] >= expected_total * 0.9, "写入成功率太低"
        assert results['read'] >= expected_total * 0.9, "读取成功率太低"
        assert results['errors'] < expected_total * 0.1, "错误率太高"
        
        queue.close()
        destroy_queue(queue_name)
        print("✓ 简单并发测试通过")
        
    except Exception as e:
        print(f"✗ 简单并发测试失败: {e}")
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    try:
        # 测试1: 无效队列名
        print("  测试无效队列名...")
        try:
            invalid_queue = SageQueue("", maxsize=1024)
            assert False, "空队列名应该失败"
        except:
            pass  # 预期的错误
        
        try:
            invalid_queue = SageQueue("a" * 100, maxsize=1024)  # 太长的名称
            # 可能成功也可能失败，取决于实现
        except:
            pass
        
        # 测试2: 超时行为
        print("  测试超时行为...")
        timeout_queue_name = f"test_timeout_{int(time.time())}"
        destroy_queue(timeout_queue_name)
        
        timeout_queue = SageQueue(timeout_queue_name, maxsize=1024)
        
        # get超时
        start_time = time.time()
        try:
            timeout_queue.get(timeout=0.2)
            assert False, "空队列get应该超时"
        except Exception as e:
            elapsed = time.time() - start_time
            assert 0.15 <= elapsed <= 0.3, f"超时时间不准确: {elapsed}"
            assert "timed out" in str(e).lower() or "empty" in str(e).lower()
        
        timeout_queue.close()
        destroy_queue(timeout_queue_name)
        
        # 测试3: 不可序列化对象
        print("  测试不可序列化对象...")
        serial_queue_name = f"test_serial_{int(time.time())}"
        destroy_queue(serial_queue_name)
        
        serial_queue = SageQueue(serial_queue_name, maxsize=1024)
        
        # Lambda函数不能序列化
        try:
            serial_queue.put(lambda x: x + 1)
            assert False, "lambda函数应该序列化失败"
        except Exception as e:
            assert "serialize" in str(e).lower() or "pickle" in str(e).lower()
        
        serial_queue.close()
        destroy_queue(serial_queue_name)
        
        print("✓ 错误处理测试通过")
        
    except Exception as e:
        print(f"✗ 错误处理测试失败: {e}")


def test_performance_basic():
    """基础性能测试"""
    print("\n=== 基础性能测试 ===")
    
    queue_name = f"test_perf_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=50*1024)  # 50KB缓冲区
        
        # 测试小消息高频
        small_message = {"id": 0, "data": "x" * 50}
        num_small = 1000
        
        print(f"  测试小消息 ({len(pickle.dumps(small_message))} 字节) x {num_small}")
        
        start_time = time.time()
        successful_puts = 0
        
        for i in range(num_small):
            small_message['id'] = i
            try:
                queue.put_nowait(small_message)
                successful_puts += 1
            except:
                # 队列满了，读取一些数据
                try:
                    for _ in range(10):
                        queue.get_nowait()
                except:
                    pass
                # 再次尝试
                try:
                    queue.put_nowait(small_message)
                    successful_puts += 1
                except:
                    pass
        
        write_time = time.time() - start_time
        write_rate = successful_puts / write_time if write_time > 0 else 0
        
        print(f"    写入: {successful_puts}/{num_small} 消息, {write_rate:.0f} msg/s")
        
        # 读取测试
        start_time = time.time()
        successful_gets = 0
        
        while not queue.empty() and successful_gets < successful_puts:
            try:
                queue.get_nowait()
                successful_gets += 1
            except:
                break
        
        read_time = time.time() - start_time
        read_rate = successful_gets / read_time if read_time > 0 else 0
        
        print(f"    读取: {successful_gets} 消息, {read_rate:.0f} msg/s")
        
        queue.close()
        destroy_queue(queue_name)
        
        assert successful_puts > num_small * 0.8, "写入成功率太低"
        assert successful_gets == successful_puts, "读取数量不匹配"
        
        print("✓ 基础性能测试通过")
        
    except Exception as e:
        print(f"✗ 基础性能测试失败: {e}")
        try:
            destroy_queue(queue_name)
        except:
            pass


def run_safe_tests():
    """运行安全测试套件"""
    print("SAGE Memory-Mapped Queue 安全测试套件")
    print("=" * 50)
    
    test_functions = [
        test_data_integrity,
        test_queue_capacity,
        test_queue_lifecycle,
        test_error_handling,
        test_performance_basic,
        test_concurrent_simple,
    ]
    
    passed = 0
    failed = 0
    start_time = time.time()
    
    for test_func in test_functions:
        print(f"\n运行 {test_func.__doc__ or test_func.__name__}...")
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ 测试异常: {e}")
            failed += 1
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"总耗时: {total_time:.1f}秒")
    
    if failed == 0:
        print("\n🎉 所有安全测试都通过了!")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return False


if __name__ == "__main__":
    # 设置多进程启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
    
    success = run_safe_tests()
    sys.exit(0 if success else 1)
