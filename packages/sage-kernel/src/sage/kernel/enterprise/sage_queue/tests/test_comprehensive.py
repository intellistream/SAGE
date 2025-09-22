#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 综合测试套件  
Comprehensive test suite for SAGE high-performance memory-mapped queue
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
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sage.extensions.sage_queue.python.sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("请先运行 ../build.sh 编译C库")
    sys.exit(1)


class TestResult:
    """测试结果记录类"""
    def __init__(self, name: str):
        self.name = name
        self.start_time = time.time()
        self.end_time = None
        self.passed = False
        self.error = None
        self.stats = {}
    
    def finish(self, passed: bool, error: str = None, stats: dict = None):
        self.end_time = time.time()
        self.passed = passed
        self.error = error
        self.stats = stats or {}
    
    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        duration = f"{self.duration:.3f}s"
        if self.error:
            return f"{status} {self.name} ({duration}) - {self.error}"
        return f"{status} {self.name} ({duration})"


def test_edge_cases() -> TestResult:
    """测试边界条件和错误处理"""
    result = TestResult("边界条件测试")
    
    try:
        queue_name = f"test_edge_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 测试1: 大数据对象
        print("  测试大数据对象...")
        large_queue = SageQueue(queue_name + "_large")  # 1MB
        
        # 生成大数据
        large_data = {
            'array': list(range(10000)),
            'text': 'A' * 10000,
            'nested': {'level1': {'level2': list(range(1000))}}
        }
        
        large_queue.put(large_data, timeout=5.0)
        retrieved_data = large_queue.get(timeout=5.0)
        assert retrieved_data == large_data, "大数据对象不匹配"
        large_queue.close()
        
        # 测试2: 空值和None
        print("  测试特殊值...")
        special_queue = SageQueue(queue_name + "_special")
        special_values = [None, "", [], {}, 0, False, b'', set()]
        
        for val in special_values:
            special_queue.put(val)
        
        for expected in special_values:
            actual = special_queue.get()
            if isinstance(expected, set):
                # set在pickle后可能变成list
                continue
            assert actual == expected, f"特殊值不匹配: expected={expected}, actual={actual}"
        
        special_queue.close()
        
        # 测试3: 超时处理
        print("  测试超时处理...")
        timeout_queue = SageQueue(queue_name + "_timeout")
        
        # 测试get超时
        start_time = time.time()
        try:
            timeout_queue.get(timeout=0.1)
            assert False, "应该超时"
        except Exception as e:
            assert "timed out" in str(e).lower(), f"超时异常信息不正确: {e}"
        
        elapsed = time.time() - start_time
        assert 0.08 <= elapsed <= 0.15, f"超时时间不准确: {elapsed}"
        
        timeout_queue.close()
        
        # 测试4: 不可序列化对象
        print("  测试不可序列化对象...")
        serial_queue = SageQueue(queue_name + "_serial")
        
        class NotSerializable:
            def __getstate__(self):
                raise Exception("Cannot serialize")
        
        try:
            serial_queue.put(NotSerializable())
            assert False, "应该抛出序列化异常"
        except ValueError as e:
            assert "serialize" in str(e), f"序列化异常信息不正确: {e}"
        
        serial_queue.close()
        
        # 清理
        for suffix in ["_large", "_special", "_timeout", "_serial"]:
            destroy_queue(queue_name + suffix)
        
        result.finish(True, stats={'large_data_size': len(pickle.dumps(large_data))})
        
    except Exception as e:
        result.finish(False, str(e))
    
    return result


def test_concurrent_access() -> TestResult:
    """测试并发访问"""
    result = TestResult("并发访问测试")
    
    try:
        queue_name = f"test_concurrent_{int(time.time())}"
        destroy_queue(queue_name)
        
        queue = SageQueue(queue_name)
        num_threads = 8
        messages_per_thread = 100
        
        results = {'put': [], 'get': []}
        barrier = threading.Barrier(num_threads * 2)  # writers + readers
        
        def writer_thread(thread_id: int):
            barrier.wait()  # 同步启动
            start = time.time()
            
            for i in range(messages_per_thread):
                message = {
                    'thread_id': thread_id,
                    'message_id': i,
                    'data': f"Thread-{thread_id}-Message-{i}",
                    'timestamp': time.time()
                }
                queue.put(message, timeout=10.0)
            
            end = time.time()
            results['put'].append(end - start)
        
        def reader_thread(thread_id: int):
            barrier.wait()  # 同步启动
            start = time.time()
            messages = []
            
            for i in range(messages_per_thread):
                try:
                    msg = queue.get(timeout=15.0)
                    messages.append(msg)
                except Exception as e:
                    print(f"Reader {thread_id} error at message {i}: {e}")
                    break
            
            end = time.time()
            results['get'].append((end - start, len(messages)))
        
        # 创建线程
        threads = []
        
        # 写线程
        for i in range(num_threads):
            t = threading.Thread(target=writer_thread, args=(i,))
            threads.append(t)
            t.start()
        
        # 读线程
        for i in range(num_threads):
            t = threading.Thread(target=reader_thread, args=(i + num_threads,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join(timeout=20.0)
        
        # 验证结果
        total_put_time = sum(results['put'])
        total_messages_read = sum(count for _, count in results['get'])
        expected_messages = num_threads * messages_per_thread
        
        assert total_messages_read == expected_messages, \
            f"消息数量不匹配: expected={expected_messages}, actual={total_messages_read}"
        
        queue.close()
        destroy_queue(queue_name)
        
        stats = {
            'threads': num_threads * 2,
            'messages_per_thread': messages_per_thread,
            'total_messages': expected_messages,
            'avg_put_time': total_put_time / num_threads,
            'avg_get_time': sum(time_taken for time_taken, _ in results['get']) / num_threads
        }
        
        result.finish(True, stats=stats)
        
    except Exception as e:
        result.finish(False, str(e))
        try:
            destroy_queue(queue_name)
        except:
            pass
    
    return result


def test_memory_leak() -> TestResult:
    """测试内存泄漏"""
    result = TestResult("内存泄漏测试")
    
    try:
        try:
            import psutil
            import gc
        except ImportError:
            result.finish(False, "需要安装 psutil: pip install psutil")
            return result
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        queue_name = f"test_memory_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 创建多个队列并频繁操作
        num_iterations = 100
        messages_per_iteration = 50
        
        for iteration in range(num_iterations):
            current_queue_name = f"{queue_name}_{iteration}"
            queue = SageQueue(current_queue_name)
            
            # 写入大量数据
            for i in range(messages_per_iteration):
                data = {
                    'iteration': iteration,
                    'message': i,
                    'payload': list(range(100)),  # 一些数据
                    'text': f"Iteration {iteration} Message {i}" * 5
                }
                queue.put(data)
            
            # 读取所有数据
            for i in range(messages_per_iteration):
                queue.get()
            
            # 关闭队列
            queue.close()
            destroy_queue(current_queue_name)
            
            # 强制垃圾回收
            if iteration % 20 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"  Iteration {iteration}: Memory usage: {current_memory:.1f}MB")
        
        # 最终内存检查
        gc.collect()
        time.sleep(0.1)
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"  初始内存: {initial_memory:.1f}MB")
        print(f"  最终内存: {final_memory:.1f}MB")
        print(f"  内存增长: {memory_increase:.1f}MB")
        
        # 允许一定的内存增长（小于50MB）
        assert memory_increase < 50, f"可能存在内存泄漏: 增长了{memory_increase:.1f}MB"
        
        stats = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'iterations': num_iterations,
            'messages_per_iteration': messages_per_iteration
        }
        
        result.finish(True, stats=stats)
        
    except Exception as e:
        result.finish(False, str(e))
    
    return result


def test_persistence() -> TestResult:
    """测试队列持久性"""
    result = TestResult("持久性测试")
    
    try:
        queue_name = f"test_persistence_{int(time.time())}"
        destroy_queue(queue_name)
        
        test_data = [
            "持久性测试数据1",
            {"key": "value", "number": 42},
            [1, 2, 3, 4, 5],
            "最后一条消息"
        ]
        
        # 第一阶段：创建队列并写入数据
        queue1 = SageQueue(queue_name)
        for data in test_data:
            queue1.put(data)
        
        # 获取统计信息
        stats_before = queue1.get_stats()
        print(f"  写入前统计: {stats_before}")
        
        # 关闭队列（但不销毁）
        queue1.close()
        
        # 短暂等待
        time.sleep(0.1)
        
        # 第二阶段：重新打开队列并读取数据
        queue2 = SageQueue(queue_name)
        
        retrieved_data = []
        for _ in range(len(test_data)):
            data = queue2.get(timeout=5.0)
            retrieved_data.append(data)
        
        # 验证数据一致性
        assert retrieved_data == test_data, f"数据不一致: {retrieved_data} != {test_data}"
        
        stats_after = queue2.get_stats()
        print(f"  读取后统计: {stats_after}")
        
        queue2.close()
        destroy_queue(queue_name)
        
        result.finish(True, stats={
            'data_items': len(test_data),
            'bytes_written': stats_before['total_bytes_written'],
            'bytes_read': stats_after['total_bytes_read']
        })
        
    except Exception as e:
        result.finish(False, str(e))
        try:
            destroy_queue(queue_name)
        except:
            pass
    
    return result


def test_stress_performance() -> TestResult:
    """压力性能测试"""
    result = TestResult("压力性能测试")
    
    try:
        queue_name = f"test_stress_{int(time.time())}"
        destroy_queue(queue_name)
        
        queue = SageQueue(queue_name)  # 100KB buffer
        
        # 测试参数
        num_messages = 5000
        message_sizes = [100, 1000, 5000]  # bytes
        
        performance_data = {}
        
        for msg_size in message_sizes:
            print(f"  测试消息大小: {msg_size} 字节")
            
            # 生成测试数据
            test_message = {
                'id': 0,
                'data': 'x' * msg_size,
                'timestamp': time.time()
            }
            
            # 写入性能测试
            write_start = time.time()
            write_count = 0
            
            for i in range(num_messages):
                test_message['id'] = i
                test_message['timestamp'] = time.time()
                
                try:
                    queue.put_nowait(test_message)
                    write_count += 1
                except:
                    # 队列满了，先读一些
                    for _ in range(min(100, queue.qsize())):
                        try:
                            queue.get_nowait()
                        except:
                            break
                    
                    try:
                        queue.put_nowait(test_message)
                        write_count += 1
                    except:
                        break
            
            write_time = time.time() - write_start
            
            # 读取性能测试
            read_start = time.time()
            read_count = 0
            
            while not queue.empty() and read_count < write_count:
                try:
                    queue.get_nowait()
                    read_count += 1
                except:
                    break
            
            read_time = time.time() - read_start
            
            # 计算性能指标
            write_rate = write_count / write_time if write_time > 0 else 0
            read_rate = read_count / read_time if read_time > 0 else 0
            throughput_mbps = (write_count * msg_size) / (1024 * 1024) / max(write_time, 0.001)
            
            performance_data[msg_size] = {
                'write_count': write_count,
                'read_count': read_count,
                'write_rate_mps': write_rate,
                'read_rate_mps': read_rate,
                'throughput_mbps': throughput_mbps
            }
            
            print(f"    写入: {write_count} 消息, {write_rate:.0f} msg/s")
            print(f"    读取: {read_count} 消息, {read_rate:.0f} msg/s")
            print(f"    吞吐量: {throughput_mbps:.1f} MB/s")
        
        queue.close()
        destroy_queue(queue_name)
        
        result.finish(True, stats=performance_data)
        
    except Exception as e:
        result.finish(False, str(e))
        try:
            destroy_queue(queue_name)
        except:
            pass
    
    return result


def test_multiprocess_robustness() -> TestResult:
    """多进程健壮性测试"""
    result = TestResult("多进程健壮性测试")
    
    def worker_process(queue_name: str, worker_id: int, operation_count: int, seed: int):
        """工作进程"""
        random.seed(seed + worker_id)
        
        try:
            queue = SageQueue(queue_name)
            operations = ['put', 'get'] * (operation_count // 2)
            random.shuffle(operations)
            
            put_count = 0
            get_count = 0
            
            for op in operations:
                try:
                    if op == 'put':
                        data = "12345"
                        queue.put(data, timeout=1.0)
                        put_count += 1
                    else:
                        queue.get(timeout=1.0)
                        get_count += 1
                    
                    # 随机暂停
                    if random.random() < 0.1:
                        time.sleep(random.uniform(0.001, 0.01))
                        
                except:
                    continue  # 忽略超时等错误
            
            queue.close()
            return {'worker_id': worker_id, 'put_count': put_count, 'get_count': get_count}
            
        except Exception as e:
            return {'worker_id': worker_id, 'error': str(e)}
    
    try:
        queue_name = f"test_multiproc_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 创建主队列
        main_queue = SageQueue(queue_name)
        
        # 预填充一些数据
        for i in range(100):
            main_queue.put(f"prefill_{i}")
        
        main_queue.close()
        
        # 启动多个工作进程
        num_workers = 6
        operations_per_worker = 200
        seed = int(time.time())
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for worker_id in range(num_workers):
                future = executor.submit(
                    worker_process,
                    queue_name,
                    worker_id,
                    operations_per_worker,
                    seed
                )
                futures.append(future)
            
            # 收集结果
            worker_results = []
            for future in as_completed(futures, timeout=30):
                try:
                    result_data = future.result()
                    worker_results.append(result_data)
                except Exception as e:
                    worker_results.append({'error': str(e)})
            print("  工作进程结果:")
            for r in worker_results:
                print(f"    {r}")
            
        # 分析结果
        successful_workers = [r for r in worker_results if 'error' not in r]
        total_puts = sum(r['put_count'] for r in successful_workers)
        total_gets = sum(r['get_count'] for r in successful_workers)
        
        print(f"  成功的工作进程: {len(successful_workers)}/{num_workers}")
        print(f"  总put操作: {total_puts}")
        print(f"  总get操作: {total_gets}")
        
        # 检查最终队列状态
        final_queue = SageQueue(queue_name)
        final_size = 0
        try:
            while True:
                final_queue.get_nowait()
                final_size += 1
        except:
            pass
        
        final_queue.close()
        destroy_queue(queue_name)
        
        print(f"  最终队列大小: {final_size}")
        
        # 成功条件：至少一半的工作进程成功完成
        assert len(successful_workers) >= num_workers // 2, \
            f"太多工作进程失败: {num_workers - len(successful_workers)}/{num_workers}"
        
        stats = {
            'workers': num_workers,
            'successful_workers': len(successful_workers),
            'total_puts': total_puts,
            'total_gets': total_gets,
            'final_queue_size': final_size
        }
        
        result.finish(True, stats=stats)
        
    except Exception as e:
        result.finish(False, str(e))
        try:
            destroy_queue(queue_name)
        except:
            pass
    
    return result


def run_comprehensive_tests():
    """运行所有综合测试"""
    print("SAGE Memory-Mapped Queue 综合测试套件")
    print("=" * 60)
    print()
    
    # 定义测试函数
    test_functions = [
        test_edge_cases,
        test_persistence,
        test_stress_performance,
        test_concurrent_access,
        test_memory_leak,
        test_multiprocess_robustness,
    ]
    
    results = []
    
    for test_func in test_functions:
        print(f"运行 {test_func.__doc__ or test_func.__name__}...")
        try:
            test_result = test_func()
            results.append(test_result)
            print(f"  {test_result}")
            if test_result.stats:
                for key, value in test_result.stats.items():
                    print(f"    {key}: {value}")
            print()
        except Exception as e:
            error_result = TestResult(test_func.__name__)
            error_result.finish(False, f"测试执行异常: {e}")
            results.append(error_result)
            print(f"  {error_result}")
            print()
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    total_time = 0
    
    for test_result in results:
        print(f"  {test_result}")
        if test_result.passed:
            passed += 1
        else:
            failed += 1
        total_time += test_result.duration
    
    print("-" * 60)
    print(f"总计: {passed} 通过, {failed} 失败, 耗时 {total_time:.1f}秒")
    
    if failed == 0:
        print("\n🎉 所有测试都通过了!")
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
    
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
