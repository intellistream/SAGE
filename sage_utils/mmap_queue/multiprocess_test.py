#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 多进程专项测试
Multi-process specific test for SAGE high-performance memory-mapped queue
"""

import os
import sys
import time
import multiprocessing
from typing import Dict, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


def simple_worker(queue_name: str, worker_id: int, operation_count: int) -> Dict[str, Any]:
    """简单工作进程"""
    try:
        print(f"Worker {worker_id}: 开始连接队列 {queue_name}")
        queue = SageQueue(queue_name)
        print(f"Worker {worker_id}: 成功连接队列")
        
        completed_ops = 0
        
        for i in range(operation_count):
            try:
                # 写入消息
                message = {
                    'worker_id': worker_id,
                    'op_id': i,
                    'data': f'worker_{worker_id}_op_{i}'
                }
                
                queue.put(message, timeout=5.0)
                completed_ops += 1
                
                if i % 5 == 0:
                    print(f"Worker {worker_id}: 完成写入操作 {i+1}/{operation_count}")
                
            except Exception as e:
                print(f"Worker {worker_id}: 写入失败 at {i}: {e}")
                break
        
        print(f"Worker {worker_id}: 完成，共写入 {completed_ops} 次操作")
        queue.close()
        
        return {
            'worker_id': worker_id,
            'completed_ops': completed_ops,
            'success': True
        }
        
    except Exception as e:
        print(f"Worker {worker_id}: 异常 - {e}")
        import traceback
        traceback.print_exc()
        return {
            'worker_id': worker_id,
            'error': str(e),
            'success': False
        }


def consumer_worker(queue_name: str, expected_messages: int) -> Dict[str, Any]:
    """消费者工作进程"""
    try:
        print(f"Consumer: 开始连接队列 {queue_name}")
        queue = SageQueue(queue_name)
        print(f"Consumer: 成功连接队列")
        
        consumed = 0
        start_time = time.time()
        timeout_duration = 20.0  # 20秒超时
        
        while consumed < expected_messages:
            try:
                current_time = time.time()
                if current_time - start_time > timeout_duration:
                    print(f"Consumer: 超时，已消费 {consumed}/{expected_messages}")
                    break
                
                message = queue.get(timeout=1.0)
                consumed += 1
                
                if consumed % 10 == 0:
                    print(f"Consumer: 已消费 {consumed}/{expected_messages}")
                
            except Exception as e:
                # 可能是超时，继续尝试
                if "timed out" in str(e).lower() or "empty" in str(e).lower():
                    continue
                else:
                    print(f"Consumer: 读取错误 - {e}")
                    break
        
        print(f"Consumer: 完成，共消费 {consumed} 条消息")
        queue.close()
        
        return {
            'consumed': consumed,
            'success': True
        }
        
    except Exception as e:
        print(f"Consumer: 异常 - {e}")
        return {
            'error': str(e),
            'success': False
        }


def test_multiprocess_simple():
    """简单多进程测试"""
    print("\n=== 简单多进程测试 ===")
    
    queue_name = f"test_multiproc_simple_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        # 创建队列
        print("创建主队列...")
        main_queue = SageQueue(queue_name, maxsize=32*1024)  # 32KB
        main_queue.close()  # 关闭句柄但保留共享内存
        
        num_workers = 2
        ops_per_worker = 10
        
        print(f"启动 {num_workers} 个生产者进程...")
        
        # 使用 multiprocessing.Process 而不是 ProcessPoolExecutor
        processes = []
        
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=simple_worker,
                args=(queue_name, worker_id, ops_per_worker)
            )
            processes.append(p)
            p.start()
            print(f"  启动进程 {worker_id}")
        
        # 等待所有进程完成
        for i, p in enumerate(processes):
            p.join(timeout=15.0)
            if p.is_alive():
                print(f"  进程 {i} 超时，强制终止")
                p.terminate()
                p.join()
            else:
                print(f"  进程 {i} 正常完成")
        
        # 检查队列状态
        print("检查队列状态...")
        check_queue = SageQueue(queue_name)
        stats = check_queue.get_stats()
        print(f"  队列统计: {stats}")
        
        # 尝试读取所有消息
        messages = []
        while not check_queue.empty():
            try:
                msg = check_queue.get_nowait()
                messages.append(msg)
            except:
                break
        
        print(f"  读取到 {len(messages)} 条消息")
        
        # 显示前几条消息作为样本
        for i, msg in enumerate(messages[:5]):
            print(f"    消息 {i}: {msg}")
        
        check_queue.close()
        destroy_queue(queue_name)
        
        expected_messages = num_workers * ops_per_worker
        success_rate = len(messages) / expected_messages if expected_messages > 0 else 0
        
        print(f"成功率: {len(messages)}/{expected_messages} = {success_rate:.1%}")
        
        if success_rate >= 0.8:  # 至少80%成功
            print("✓ 简单多进程测试通过")
        else:
            print("✗ 简单多进程测试未达到预期")
        
    except Exception as e:
        print(f"✗ 简单多进程测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_producer_consumer():
    """生产者-消费者多进程测试"""
    print("\n=== 生产者-消费者测试 ===")
    
    queue_name = f"test_prod_cons_{int(time.time())}"
    destroy_queue(queue_name)
    
    try:
        # 创建队列
        print("创建队列...")
        main_queue = SageQueue(queue_name, maxsize=64*1024)  # 64KB
        main_queue.close()
        
        num_producers = 2
        messages_per_producer = 15
        total_expected = num_producers * messages_per_producer
        
        print(f"启动 {num_producers} 个生产者，每个生产 {messages_per_producer} 条消息...")
        
        # 启动生产者进程
        producer_processes = []
        for i in range(num_producers):
            p = multiprocessing.Process(
                target=simple_worker,
                args=(queue_name, i, messages_per_producer)
            )
            producer_processes.append(p)
            p.start()
            print(f"  启动生产者 {i}")
        
        # 稍等一下让生产者开始工作
        time.sleep(0.5)
        
        # 启动消费者进程
        print("启动消费者...")
        consumer_process = multiprocessing.Process(
            target=consumer_worker,
            args=(queue_name, total_expected)
        )
        consumer_process.start()
        
        # 等待所有进程完成
        print("等待生产者完成...")
        for i, p in enumerate(producer_processes):
            p.join(timeout=10.0)
            if p.is_alive():
                print(f"  生产者 {i} 超时")
                p.terminate()
                p.join()
        
        print("等待消费者完成...")
        consumer_process.join(timeout=15.0)
        if consumer_process.is_alive():
            print("  消费者超时")
            consumer_process.terminate()
            consumer_process.join()
        
        # 检查最终状态
        final_queue = SageQueue(queue_name)
        final_stats = final_queue.get_stats()
        remaining_messages = 0
        
        while not final_queue.empty():
            try:
                final_queue.get_nowait()
                remaining_messages += 1
            except:
                break
        
        print(f"最终队列状态: {final_stats}")
        print(f"剩余消息: {remaining_messages}")
        
        final_queue.close()
        destroy_queue(queue_name)
        
        consumed_messages = total_expected - remaining_messages
        success_rate = consumed_messages / total_expected if total_expected > 0 else 0
        
        print(f"消费成功率: {consumed_messages}/{total_expected} = {success_rate:.1%}")
        
        if success_rate >= 0.7:  # 至少70%成功
            print("✓ 生产者-消费者测试通过")
        else:
            print("✗ 生产者-消费者测试未达到预期")
            
    except Exception as e:
        print(f"✗ 生产者-消费者测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_queue_reference_across_processes():
    """测试跨进程队列引用"""
    print("\n=== 跨进程队列引用测试 ===")
    
    def ref_worker(queue_ref_data: dict, worker_id: int) -> Dict[str, Any]:
        """使用队列引用的工作进程"""
        try:
            # 重建队列引用
            from sage_queue import SageQueueRef
            
            # 手动构建引用对象
            class MockRef:
                def __init__(self, data):
                    self.__dict__.update(data)
            
            mock_ref = MockRef(queue_ref_data)
            queue_ref = SageQueueRef.__new__(SageQueueRef)
            queue_ref.__setstate__(queue_ref_data)
            
            print(f"RefWorker {worker_id}: 从引用创建队列")
            queue = queue_ref.get_queue()
            
            # 写入一些数据
            for i in range(5):
                message = f"ref_worker_{worker_id}_msg_{i}"
                queue.put(message, timeout=3.0)
            
            queue.close()
            
            return {
                'worker_id': worker_id,
                'success': True,
                'messages_sent': 5
            }
            
        except Exception as e:
            return {
                'worker_id': worker_id,
                'error': str(e),
                'success': False
            }
    
    try:
        queue_name = f"test_ref_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 创建原始队列并获取引用
        print("创建原始队列...")
        original_queue = SageQueue(queue_name, maxsize=16*1024)
        queue_ref = original_queue.get_reference()
        
        print(f"获得队列引用: {queue_ref}")
        
        # 获取引用的可序列化数据
        ref_data = queue_ref.__getstate__()
        print(f"引用数据: {ref_data}")
        
        original_queue.close()
        
        # 启动使用引用的工作进程
        num_workers = 2
        processes = []
        
        for i in range(num_workers):
            p = multiprocessing.Process(
                target=ref_worker,
                args=(ref_data, i)
            )
            processes.append(p)
            p.start()
            print(f"  启动引用工作进程 {i}")
        
        # 等待完成
        for i, p in enumerate(processes):
            p.join(timeout=10.0)
            if p.is_alive():
                p.terminate()
                p.join()
        
        # 检查结果
        result_queue = SageQueue(queue_name)
        received_messages = []
        
        while not result_queue.empty():
            try:
                msg = result_queue.get_nowait()
                received_messages.append(msg)
            except:
                break
        
        print(f"收到 {len(received_messages)} 条消息:")
        for msg in received_messages[:10]:  # 显示前10条
            print(f"  - {msg}")
        
        result_queue.close()
        destroy_queue(queue_name)
        
        expected = num_workers * 5
        success_rate = len(received_messages) / expected if expected > 0 else 0
        
        print(f"引用传递成功率: {len(received_messages)}/{expected} = {success_rate:.1%}")
        
        if success_rate >= 0.8:
            print("✓ 跨进程队列引用测试通过")
        else:
            print("✗ 跨进程队列引用测试未达到预期")
            
    except Exception as e:
        print(f"✗ 跨进程队列引用测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("SAGE Memory-Mapped Queue 多进程专项测试")
    print("=" * 50)
    
    test_multiprocess_simple()
    test_producer_consumer()
    test_queue_reference_across_processes()
    
    print("\n" + "=" * 50)
    print("多进程测试完成!")


if __name__ == "__main__":
    # 设置多进程启动方法
    multiprocessing.set_start_method('spawn', force=True)
    
    main()
