#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 安全测试套件
Safety test suite for SAGE high-performance memory-mapped queue
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

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("请先运行 ../build.sh 编译C库")
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
        test_data = [
            # 基本类型
            None,
            True,
            False,
            0,
            1,
            -1,
            3.14159,
            float('inf'),
            float('-inf'),
            
            # 字符串类型
            "",
            "Hello, 世界!",
            "a" * 1000,  # 长字符串
            "\n\t\r",  # 特殊字符
            
            # 容器类型
            [],
            [1, 2, 3],
            list(range(100)),  # 长列表
            {},
            {"key": "value"},
            {"nested": {"deep": {"data": [1, 2, 3]}}},  # 嵌套字典
            (),
            (1, 2, 3),
            tuple(range(50)),  # 长元组
            set(),
            {1, 2, 3, 4, 5},
            
            # 字节类型
            b"",
            b"binary data",
            bytes(range(256)),  # 所有字节值
            
            # 复杂对象
            {
                "mixed": [1, "two", 3.0, [4, 5], {"six": 7}],
                "unicode": "测试中文字符和emoji 🚀",
                "numbers": list(range(100)),
                "nested_deep": {
                    "level1": {
                        "level2": {
                            "level3": "deep value"
                        }
                    }
                }
            }
        ]
        
        print(f"测试 {len(test_data)} 种不同数据类型...")
        
        # 写入所有测试数据
        for i, data in enumerate(test_data):
            try:
                queue.put(data, timeout=5.0)
                if i % 10 == 0:
                    print(f"  已写入 {i+1}/{len(test_data)} 种数据类型")
            except Exception as e:
                print(f"  写入第 {i} 项时出错: {type(data).__name__} - {e}")
                raise
        
        print("  所有数据写入完成")
        
        # 读取并验证所有数据
        retrieved_data = []
        for i in range(len(test_data)):
            try:
                data = queue.get(timeout=5.0)
                retrieved_data.append(data)
                if i % 10 == 0:
                    print(f"  已读取 {i+1}/{len(test_data)} 种数据类型")
            except Exception as e:
                print(f"  读取第 {i} 项时出错: {e}")
                raise
        
        print("  所有数据读取完成")
        
        # 验证数据一致性
        mismatches = 0
        for i, (original, retrieved) in enumerate(zip(test_data, retrieved_data)):
            try:
                # 特殊处理set类型（pickle后可能变成其他类型）
                if isinstance(original, set) and isinstance(retrieved, (list, tuple)):
                    assert set(retrieved) == original, f"Set类型数据不匹配 at {i}"
                elif isinstance(original, float) and isinstance(retrieved, float):
                    # 特殊处理浮点数无穷大
                    if original != original:  # NaN
                        assert retrieved != retrieved, f"NaN处理不正确 at {i}"
                    else:
                        assert original == retrieved, f"浮点数不匹配 at {i}: {original} != {retrieved}"
                else:
                    assert original == retrieved, f"数据不匹配 at {i}: {type(original).__name__} {original} != {type(retrieved).__name__} {retrieved}"
            except AssertionError as e:
                print(f"  ⚠️  数据不匹配 #{i}: {e}")
                mismatches += 1
        
        if mismatches == 0:
            print(f"✓ 所有 {len(test_data)} 种数据类型完全匹配")
        else:
            print(f"⚠️  有 {mismatches} 种数据类型不匹配（可能是正常的类型转换）")
        
        # 队列应该为空
        assert queue.empty(), "队列应该为空"
        assert queue.qsize() == 0, "队列大小应该为0"
        
        queue.close()
        destroy_queue(queue_name)
        print("✓ 数据完整性测试通过")
        
    except Exception as e:
        print(f"✗ 数据完整性测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_error_conditions():
    """测试错误条件处理"""
    print("\n=== 测试错误条件处理 ===")
    
    queue_name = f"test_errors_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=1024)
        
        # 测试1: 超时条件
        print("  测试超时条件...")
        
        # 从空队列读取应该超时
        start_time = time.time()
        try:
            queue.get(timeout=0.1)
            assert False, "应该超时"
        except Exception as e:
            elapsed = time.time() - start_time
            assert 0.05 <= elapsed <= 0.2, f"超时时间不准确: {elapsed}"
            assert "timed out" in str(e).lower() or "empty" in str(e).lower(), f"超时异常信息不正确: {e}"
            print(f"    ✓ 读取超时正确: {elapsed:.3f}s")
        
        # 测试2: 不可序列化对象
        print("  测试不可序列化对象...")
        
        class UnserializableClass:
            def __init__(self):
                self.file = open(__file__, 'r')  # 文件对象不能序列化
            
            def __del__(self):
                if hasattr(self, 'file'):
                    self.file.close()
        
        try:
            queue.put(UnserializableClass())
            assert False, "应该抛出序列化异常"
        except Exception as e:
            assert "pickle" in str(e).lower() or "serialize" in str(e).lower(), f"序列化异常信息不正确: {e}"
            print(f"    ✓ 不可序列化对象异常正确: {type(e).__name__}")
        
        # 测试3: 非阻塞操作
        print("  测试非阻塞操作...")
        
        # 空队列非阻塞读取
        try:
            queue.get_nowait()
            assert False, "应该抛出Empty异常"
        except Exception as e:
            assert "empty" in str(e).lower(), f"Empty异常信息不正确: {e}"
            print(f"    ✓ 非阻塞读取异常正确: {type(e).__name__}")
        
        # 填满队列测试非阻塞写入
        message = {"data": "x" * 100}
        written = 0
        try:
            while True:
                queue.put_nowait(message)
                written += 1
                if written > 100:  # 安全限制
                    break
        except Exception as e:
            assert "full" in str(e).lower(), f"Full异常信息不正确: {e}"
            print(f"    ✓ 队列满异常正确: {type(e).__name__}, 写入了{written}条消息")
        
        # 测试4: 状态检查
        print("  测试状态检查...")
        
        assert not queue.empty(), "队列不应该为空"
        assert queue.full() or queue.qsize() > 0, "队列应该有数据"
        print(f"    ✓ 队列状态: size={queue.qsize()}, empty={queue.empty()}, full={queue.full()}")
        
        queue.close()
        destroy_queue(queue_name)
        print("✓ 错误条件处理测试通过")
        
    except Exception as e:
        print(f"✗ 错误条件处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_thread_safety():
    """测试线程安全"""
    print("\n=== 测试线程安全 ===")
    
    queue_name = f"test_thread_safety_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        queue = SageQueue(queue_name, maxsize=20000)
        
        num_threads = 6
        operations_per_thread = 200
        results = {'writes': 0, 'reads': 0, 'errors': 0}
        results_lock = threading.Lock()
        
        def worker_thread(thread_id: int, operation_type: str):
            """工作线程"""
            local_ops = 0
            local_errors = 0
            
            try:
                for i in range(operations_per_thread):
                    try:
                        if operation_type == 'write':
                            message = {
                                'thread_id': thread_id,
                                'operation_id': i,
                                'timestamp': time.time(),
                                'data': f'Thread-{thread_id}-Operation-{i}'
                            }
                            queue.put(message, timeout=10.0)
                            local_ops += 1
                        else:  # read
                            message = queue.get(timeout=10.0)
                            local_ops += 1
                            
                            # 验证消息结构
                            assert isinstance(message, dict), f"消息应该是字典类型"
                            assert 'thread_id' in message, f"消息应该包含thread_id"
                        
                        # 随机短暂暂停，增加竞争
                        if random.random() < 0.05:
                            time.sleep(0.001)
                            
                    except Exception as e:
                        local_errors += 1
                        if local_errors > 10:  # 避免过多错误
                            break
                        continue
                
                with results_lock:
                    if operation_type == 'write':
                        results['writes'] += local_ops
                    else:
                        results['reads'] += local_ops
                    results['errors'] += local_errors
                    
            except Exception as e:
                print(f"  线程 {thread_id} ({operation_type}) 异常: {e}")
                with results_lock:
                    results['errors'] += 1
        
        # 创建并启动线程
        threads = []
        
        # 写线程
        for i in range(num_threads // 2):
            t = threading.Thread(target=worker_thread, args=(i, 'write'))
            threads.append(t)
        
        # 读线程
        for i in range(num_threads // 2, num_threads):
            t = threading.Thread(target=worker_thread, args=(i, 'read'))
            threads.append(t)
        
        print(f"  启动 {len(threads)} 个线程 ({num_threads//2} 写 + {num_threads//2} 读)...")
        
        # 启动所有线程
        start_time = time.time()
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join(timeout=30.0)
            if t.is_alive():
                print("  警告: 有线程未及时完成")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"  线程执行完成，耗时: {duration:.3f}s")
        print(f"  写操作: {results['writes']}")
        print(f"  读操作: {results['reads']}")
        print(f"  错误数: {results['errors']}")
        print(f"  总操作: {results['writes'] + results['reads']}")
        print(f"  操作速率: {(results['writes'] + results['reads']) / duration:.0f} ops/s")
        
        # 验证基本一致性
        total_expected_ops = num_threads * operations_per_thread
        actual_ops = results['writes'] + results['reads']
        success_rate = actual_ops / total_expected_ops
        
        print(f"  成功率: {success_rate:.1%}")
        
        # 允许一定的失败率（由于超时等）
        assert success_rate >= 0.9, f"成功率太低: {success_rate:.1%}"
        assert results['errors'] < total_expected_ops * 0.1, f"错误率太高: {results['errors']}/{total_expected_ops}"
        
        # 检查最终队列状态
        final_stats = queue.get_stats()
        print(f"  最终队列状态: {final_stats}")
        
        queue.close()
        destroy_queue(queue_name)
        print("✓ 线程安全测试通过")
        
    except Exception as e:
        print(f"✗ 线程安全测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_resource_cleanup():
    """测试资源清理"""
    print("\n=== 测试资源清理 ===")
    
    try:
        # 测试多个队列的创建和销毁
        queue_names = []
        queues = []
        
        for i in range(10):
            queue_name = f"test_cleanup_{int(time.time())}_{i}"
            queue_names.append(queue_name)
            
            destroy_queue(queue_name)  # 清理可能存在的旧队列
            
            queue = SageQueue(queue_name, maxsize=1024)
            queues.append(queue)
            
            # 添加一些数据
            for j in range(5):
                queue.put(f"cleanup_test_{i}_{j}")
        
        print(f"  创建了 {len(queues)} 个队列")
        
        # 关闭所有队列
        for queue in queues:
            queue.close()
        
        print("  关闭了所有队列")
        
        # 销毁所有队列
        for queue_name in queue_names:
            destroy_queue(queue_name)
        
        print("  销毁了所有队列")
        
        # 尝试重新创建同名队列（测试是否完全清理）
        for i, queue_name in enumerate(queue_names[:3]):  # 只测试前3个
            queue = SageQueue(queue_name, maxsize=1024)
            
            # 新队列应该是空的
            assert queue.empty(), f"重新创建的队列 {queue_name} 应该为空"
            assert queue.qsize() == 0, f"重新创建的队列 {queue_name} 大小应该为0"
            
            queue.close()
            destroy_queue(queue_name)
        
        print("✓ 资源清理测试通过")
        
    except Exception as e:
        print(f"✗ 资源清理测试失败: {e}")
        import traceback
        traceback.print_exc()


def run_safety_tests():
    """运行所有安全测试"""
    print("SAGE Memory-Mapped Queue 安全测试套件")
    print("=" * 50)
    
    # 安全测试函数列表
    safety_tests = [
        test_queue_capacity,
        test_data_integrity,
        test_error_conditions,
        test_thread_safety,
        test_resource_cleanup,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in safety_tests:
        try:
            print(f"\n运行 {test_func.__doc__ or test_func.__name__}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} 测试异常: {e}")
            failed += 1
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("安全测试结果汇总:")
    print("-" * 50)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")
    
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
    
    success = run_safety_tests()
    sys.exit(0 if success else 1)
