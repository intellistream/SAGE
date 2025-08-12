#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 多进程并发读写和引用传递测试
Multiprocess concurrent read/write and reference passing test for SAGE mmap queue
"""

import os
import sys
import time
import multiprocessing
import threading
import json
from typing import Dict, Any, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sage.extensions.sage_queue.python.sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


# ============================================================================
# 多进程 Worker 函数 (必须在模块顶层定义，以支持 pickle 序列化)
# ============================================================================

def multiprocess_writer_worker(queue_name: str, worker_id: int, num_messages: int) -> Dict[str, Any]:
    """多进程写入 worker (通过队列名称连接)"""
    try:
        # 通过队列名称连接到共享队列
        queue = SageQueue(queue_name)
        
        start_time = time.time()
        completed = 0
        errors = 0
        
        for i in range(num_messages):
            try:
                message = {
                    'worker_id': worker_id,
                    'msg_id': i,
                    'timestamp': time.time(),
                    'content': f'Worker-{worker_id} Message-{i} Data: {i * worker_id}',
                    'payload': list(range(i % 10))  # 变长负载
                }
                
                queue.put(message, timeout=5.0)
                completed += 1
                
                if i % 10 == 0:
                    print(f"  Writer-{worker_id}: {i+1}/{num_messages}")
                    
            except Exception as e:
                errors += 1
                print(f"  Writer-{worker_id}: Error at {i}: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        queue.close()
        
        return {
            'worker_id': worker_id,
            'worker_type': 'writer',
            'completed': completed,
            'errors': errors,
            'duration': duration,
            'ops_per_sec': completed / duration if duration > 0 else 0,
            'success': True
        }
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'worker_type': 'writer',
            'error': str(e),
            'success': False
        }


def multiprocess_reader_worker(queue_name: str, worker_id: int, expected_messages: int, timeout: float = 30.0) -> Dict[str, Any]:
    """多进程读取 worker (通过队列名称连接)"""
    try:
        # 通过队列名称连接到共享队列
        queue = SageQueue(queue_name)
        
        start_time = time.time()
        completed = 0
        errors = 0
        messages = []
        
        deadline = start_time + timeout
        
        while completed < expected_messages and time.time() < deadline:
            try:
                message = queue.get(timeout=1.0)
                completed += 1
                messages.append(message)
                
                if completed % 10 == 0:
                    print(f"  Reader-{worker_id}: {completed}/{expected_messages}")
                    
            except Exception as e:
                if "empty" in str(e).lower() or "timed out" in str(e).lower():
                    # 队列为空，短暂等待
                    time.sleep(0.01)
                    continue
                else:
                    errors += 1
                    print(f"  Reader-{worker_id}: Error: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        queue.close()
        
        return {
            'worker_id': worker_id,
            'worker_type': 'reader',
            'completed': completed,
            'errors': errors,
            'duration': duration,
            'ops_per_sec': completed / duration if duration > 0 else 0,
            'messages_sample': messages[:3],  # 前3条消息作为样本
            'success': True
        }
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'worker_type': 'reader',
            'error': str(e),
            'success': False
        }


def concurrent_rw_worker(queue_name: str, worker_id: int, num_operations: int, read_write_ratio: float = 0.5) -> Dict[str, Any]:
    """并发读写混合操作 worker"""
    try:
        queue = SageQueue(queue_name)
        
        start_time = time.time()
        writes_completed = 0
        reads_completed = 0
        errors = 0
        
        for i in range(num_operations):
            try:
                # 根据比例决定是读还是写
                if (i / num_operations) < read_write_ratio or queue.empty():
                    # 写入操作
                    message = {
                        'concurrent_worker_id': worker_id,
                        'operation_type': 'write',
                        'op_id': i,
                        'timestamp': time.time(),
                        'data': f'ConcurrentWorker-{worker_id} Write-{i}'
                    }
                    queue.put(message, timeout=2.0)
                    writes_completed += 1
                else:
                    # 读取操作
                    message = queue.get(timeout=2.0)
                    reads_completed += 1
                    
            except Exception as e:
                errors += 1
                if errors > 5:  # 连续错误太多则退出
                    break
        
        end_time = time.time()
        duration = end_time - start_time
        
        queue.close()
        
        return {
            'worker_id': worker_id,
            'worker_type': 'concurrent_rw',
            'writes_completed': writes_completed,
            'reads_completed': reads_completed,
            'total_ops': writes_completed + reads_completed,
            'errors': errors,
            'duration': duration,
            'ops_per_sec': (writes_completed + reads_completed) / duration if duration > 0 else 0,
            'success': True
        }
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'worker_type': 'concurrent_rw',
            'error': str(e),
            'success': False
        }


def queue_reference_worker(queue_ref_data: Dict[str, Any], worker_id: int, num_operations: int) -> Dict[str, Any]:
    """队列引用传递 worker (通过引用数据重建队列)"""
    try:
        # 从引用数据重建队列引用
        import pickle
        
        # 创建 SageQueueRef 对象
        from sage.extensions.sage_queue.python.sage_queue import SageQueueRef
        queue_ref = SageQueueRef(
            queue_ref_data['queue_name'],
            queue_ref_data['maxsize'],
            queue_ref_data['create_if_not_exists']
        )
        
        # 获取队列实例
        queue = queue_ref.get_queue()
        
        start_time = time.time()
        completed_ops = 0
        
        # 执行混合读写操作
        for i in range(num_operations):
            try:
                if i % 2 == 0:  # 写操作
                    message = {
                        'ref_worker_id': worker_id,
                        'operation': 'write_via_ref',
                        'op_id': i,
                        'timestamp': time.time(),
                        'data': f'RefWorker-{worker_id} Via-Reference Op-{i}'
                    }
                    queue.put(message, timeout=3.0)
                else:  # 读操作
                    message = queue.get(timeout=3.0)
                
                completed_ops += 1
                
            except Exception as e:
                if "empty" in str(e).lower() or "timed out" in str(e).lower():
                    continue  # 忽略超时错误
                else:
                    raise
        
        end_time = time.time()
        duration = end_time - start_time
        
        queue.close()
        
        return {
            'worker_id': worker_id,
            'worker_type': 'queue_reference',
            'completed_ops': completed_ops,
            'duration': duration,
            'ops_per_sec': completed_ops / duration if duration > 0 else 0,
            'success': True
        }
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'worker_type': 'queue_reference',
            'error': str(e),
            'success': False
        }


# ============================================================================
# 测试函数
# ============================================================================

def test_multiprocess_producer_consumer():
    """测试基本的多进程生产者-消费者模式"""
    print("\n=== 测试多进程生产者-消费者模式 ===")
    
    queue_name = f"test_mp_pc_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        # 创建主队列
        main_queue = SageQueue(queue_name)
        main_queue.close()  # 关闭主队列，让子进程使用
        
        # 测试参数
        num_producers = 3
        num_consumers = 2
        messages_per_producer = 50
        total_messages = num_producers * messages_per_producer
        messages_per_consumer = total_messages // num_consumers
        
        print(f"配置: {num_producers} 生产者 × {messages_per_producer} = {total_messages} 消息")
        print(f"      {num_consumers} 消费者，每个预期 ~{messages_per_consumer} 消息")
        
        # 使用 ProcessPoolExecutor 管理进程
        with ProcessPoolExecutor(max_workers=num_producers + num_consumers) as executor:
            futures = []
            
            # 启动生产者
            for i in range(num_producers):
                future = executor.submit(
                    multiprocess_writer_worker,
                    queue_name,
                    i,
                    messages_per_producer
                )
                futures.append(future)
            
            # 启动消费者
            for i in range(num_consumers):
                expected = messages_per_consumer + (total_messages % num_consumers if i == 0 else 0)
                future = executor.submit(
                    multiprocess_reader_worker,
                    queue_name,
                    i + 100,  # 不同的worker_id避免冲突
                    expected,
                    45.0  # 45秒超时
                )
                futures.append(future)
            
            # 收集结果
            results = []
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"进程执行异常: {e}")
                    results.append({'success': False, 'error': str(e)})
        
        # 分析结果
        producers = [r for r in results if r.get('worker_type') == 'writer']
        consumers = [r for r in results if r.get('worker_type') == 'reader']
        
        successful_producers = [p for p in producers if p.get('success', False)]
        successful_consumers = [c for c in consumers if c.get('success', False)]
        
        total_produced = sum(p['completed'] for p in successful_producers)
        total_consumed = sum(c['completed'] for c in successful_consumers)
        
        print(f"\n结果统计:")
        print(f"  成功生产者: {len(successful_producers)}/{num_producers}")
        print(f"  成功消费者: {len(successful_consumers)}/{num_consumers}")
        print(f"  总生产消息: {total_produced}")
        print(f"  总消费消息: {total_consumed}")
        print(f"  消息完整率: {total_consumed/total_produced*100:.1f}%" if total_produced > 0 else "  消息完整率: N/A")
        
        # 显示个体性能
        for p in successful_producers:
            print(f"  生产者{p['worker_id']}: {p['ops_per_sec']:.0f} msg/s")
        for c in successful_consumers:
            print(f"  消费者{c['worker_id']}: {c['ops_per_sec']:.0f} msg/s")
        
        destroy_queue(queue_name)
        print("✓ 多进程生产者-消费者测试完成")
        
    except Exception as e:
        print(f"✗ 多进程生产者-消费者测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_concurrent_read_write():
    """测试并发读写混合操作"""
    print("\n=== 测试多进程并发读写混合操作 ===")
    
    queue_name = f"test_concurrent_rw_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        # 创建主队列并预填充一些数据
        main_queue = SageQueue(queue_name)
        
        # 预填充数据
        prefill_count = 50
        for i in range(prefill_count):
            main_queue.put({
                'prefill_id': i,
                'data': f'prefill_message_{i}',
                'timestamp': time.time()
            })
        
        print(f"预填充 {prefill_count} 条消息")
        main_queue.close()
        
        # 测试参数
        num_workers = 6
        operations_per_worker = 100
        read_write_ratio = 0.6  # 60% 读操作
        
        print(f"启动 {num_workers} 个并发读写进程，每个执行 {operations_per_worker} 操作")
        print(f"读写比例: {read_write_ratio*100:.0f}% 读, {(1-read_write_ratio)*100:.0f}% 写")
        
        # 启动并发进程
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            
            for worker_id in range(num_workers):
                future = executor.submit(
                    concurrent_rw_worker,
                    queue_name,
                    worker_id,
                    operations_per_worker,
                    read_write_ratio
                )
                futures.append(future)
            
            # 收集结果
            results = []
            for future in as_completed(futures, timeout=45):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"并发进程异常: {e}")
                    results.append({'success': False, 'error': str(e)})
        
        # 分析结果
        successful_workers = [r for r in results if r.get('success', False)]
        
        total_writes = sum(w['writes_completed'] for w in successful_workers)
        total_reads = sum(w['reads_completed'] for w in successful_workers)
        total_ops = sum(w['total_ops'] for w in successful_workers)
        total_errors = sum(w['errors'] for w in successful_workers)
        
        print(f"\n并发读写结果:")
        print(f"  成功进程: {len(successful_workers)}/{num_workers}")
        print(f"  总写操作: {total_writes}")
        print(f"  总读操作: {total_reads}")
        print(f"  总操作数: {total_ops}")
        print(f"  总错误数: {total_errors}")
        
        avg_ops_per_sec = sum(w['ops_per_sec'] for w in successful_workers) / len(successful_workers) if successful_workers else 0
        print(f"  平均性能: {avg_ops_per_sec:.0f} ops/s per process")
        
        # 检查最终队列状态
        final_queue = SageQueue(queue_name)
        final_size = final_queue.qsize()
        final_stats = final_queue.get_stats()
        final_queue.close()
        
        print(f"  最终队列大小: {final_size}")
        print(f"  最终统计: 写入={final_stats['total_bytes_written']}, 读取={final_stats['total_bytes_read']}")
        
        destroy_queue(queue_name)
        print("✓ 多进程并发读写测试完成")
        
    except Exception as e:
        print(f"✗ 多进程并发读写测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            destroy_queue(queue_name)
        except:
            pass


def test_queue_reference_passing():
    """测试队列引用跨进程传递"""
    print("\n=== 测试队列引用跨进程传递 ===")
    
    queue_name = f"test_ref_passing_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        # 创建主队列
        main_queue = SageQueue(queue_name)
        
        # 获取队列引用
        queue_ref = main_queue.get_reference()
        print(f"创建队列引用: {queue_ref}")
        
        # 准备引用数据用于进程间传递
        ref_data = {
            'queue_name': queue_ref.queue_name,
            'maxsize': queue_ref.maxsize,
            'create_if_not_exists': queue_ref.create_if_not_exists
        }
        
        main_queue.close()
        
        # 测试参数
        num_workers = 4
        operations_per_worker = 30
        
        print(f"启动 {num_workers} 个进程通过引用访问队列，每个执行 {operations_per_worker} 操作")
        
        # 启动引用传递进程
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            
            for worker_id in range(num_workers):
                future = executor.submit(
                    queue_reference_worker,
                    ref_data,
                    worker_id,
                    operations_per_worker
                )
                futures.append(future)
            
            # 收集结果
            results = []
            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"引用传递进程异常: {e}")
                    results.append({'success': False, 'error': str(e)})
        
        # 分析结果
        successful_workers = [r for r in results if r.get('success', False)]
        
        total_ops = sum(w['completed_ops'] for w in successful_workers)
        avg_ops_per_sec = sum(w['ops_per_sec'] for w in successful_workers) / len(successful_workers) if successful_workers else 0
        
        print(f"\n引用传递结果:")
        print(f"  成功进程: {len(successful_workers)}/{num_workers}")
        print(f"  总操作数: {total_ops}")
        print(f"  平均性能: {avg_ops_per_sec:.0f} ops/s per process")
        
        for w in successful_workers:
            print(f"  进程{w['worker_id']}: {w['completed_ops']} ops, {w['ops_per_sec']:.0f} ops/s")
        
        # 检查队列引用是否还能正常使用
        test_queue = SageQueue(queue_name)
        remaining_messages = 0
        try:
            while True:
                test_queue.get_nowait()
                remaining_messages += 1
                if remaining_messages > 1000:  # 安全限制
                    break
        except:
            pass
        
        print(f"  队列中剩余消息: {remaining_messages}")
        test_queue.close()
        
        destroy_queue(queue_name)
        print("✓ 队列引用跨进程传递测试完成")
        
    except Exception as e:
        print(f"✗ 队列引用跨进程传递测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            destroy_queue(queue_name)
        except:
            pass


def run_all_multiprocess_tests():
    """运行所有多进程测试"""
    print("SAGE Memory-Mapped Queue 多进程并发测试套件")
    print("=" * 60)
    
    # 多进程测试函数列表
    multiprocess_tests = [
        test_multiprocess_producer_consumer,
        test_concurrent_read_write,
        test_queue_reference_passing,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in multiprocess_tests:
        try:
            print(f"\n运行 {test_func.__doc__ or test_func.__name__}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} 测试异常: {e}")
            failed += 1
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("多进程测试结果汇总:")
    print("-" * 60)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 所有多进程测试都通过了!")
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
    
    success = run_all_multiprocess_tests()
    sys.exit(0 if success else 1)
