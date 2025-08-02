#!/usr/bin/env python3
"""
Python队列多进程支持测试

测试 PythonQueueDescriptor 对 multiprocessing.Queue 的支持
验证：
1. multiprocessing.Queue 的创建和使用
2. 进程间队列共享
3. 多进程并发读写
4. 队列描述符的跨进程传递
"""

import sys
import os
import time
import multiprocessing
import queue
from multiprocessing import Process, Manager
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, '/api-rework')

try:
    from sage.runtime.communication.queue import (
        PythonQueueDescriptor,
    )
    print("✓ 成功导入Python队列描述符")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


# ============ 多进程工作函数 ============

def mp_producer_worker(queue_desc_data: Dict[str, Any], worker_id: int, num_items: int, shared_stats: Dict):
    """多进程生产者工作函数"""
    try:
        # 重建队列描述符 - 使用 resolve_descriptor 替代 from_dict
        from sage.runtime.communication.queue import resolve_descriptor
        queue_desc = resolve_descriptor(queue_desc_data)
        
        produced_count = 0
        start_time = time.time()
        
        for i in range(num_items):
            item = f"mp_producer_{worker_id}_item_{i}_{time.time()}"
            queue_desc.put(item)
            produced_count += 1
            
            # 每10个项目记录一次进度
            if (i + 1) % 10 == 0:
                print(f"生产者 {worker_id}: 已生产 {i + 1}/{num_items}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 更新共享统计
        shared_stats[f'producer_{worker_id}'] = {
            'produced': produced_count,
            'duration': duration,
            'rate': produced_count / duration if duration > 0 else 0
        }
        
        return f"producer_{worker_id}_completed_{produced_count}"
        
    except Exception as e:
        shared_stats[f'producer_{worker_id}'] = {'error': str(e)}
        return f"producer_{worker_id}_error_{e}"


def mp_consumer_worker(queue_desc_data: Dict[str, Any], worker_id: int, target_items: int, 
                      timeout_per_item: float, shared_stats: Dict):
    """多进程消费者工作函数"""
    try:
        # 重建队列描述符
        queue_desc = PythonQueueDescriptor.from_dict(queue_desc_data)
        
        consumed_items = []
        start_time = time.time()
        
        while len(consumed_items) < target_items:
            try:
                item = queue_desc.get(timeout=timeout_per_item)
                consumed_items.append(item)
                
                # 每10个项目记录一次进度
                if len(consumed_items) % 10 == 0:
                    print(f"消费者 {worker_id}: 已消费 {len(consumed_items)}/{target_items}")
                    
            except queue.Empty:
                print(f"消费者 {worker_id}: 队列空，等待...")
                continue
            except Exception as e:
                print(f"消费者 {worker_id}: 获取项目时出错: {e}")
                break
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 更新共享统计
        shared_stats[f'consumer_{worker_id}'] = {
            'consumed': len(consumed_items),
            'duration': duration,
            'rate': len(consumed_items) / duration if duration > 0 else 0,
            'items_sample': consumed_items[:5]  # 保存前5个项目作为样本
        }
        
        return consumed_items
        
    except Exception as e:
        shared_stats[f'consumer_{worker_id}'] = {'error': str(e)}
        return []


def mp_mixed_worker(queue_desc_data: Dict[str, Any], worker_id: int, num_operations: int, shared_stats: Dict):
    """多进程混合读写工作函数"""
    try:
        # 重建队列描述符
        queue_desc = PythonQueueDescriptor.from_dict(queue_desc_data)
        
        put_count = 0
        get_count = 0
        start_time = time.time()
        
        for i in range(num_operations):
            if i % 3 == 0:  # 写操作 (1/3 的操作)
                try:
                    item = f"mixed_{worker_id}_{i}_{time.time()}"
                    queue_desc.put(item)
                    put_count += 1
                except Exception as e:
                    print(f"混合工作者 {worker_id}: 写入出错: {e}")
            else:  # 读操作 (2/3 的操作)
                try:
                    item = queue_desc.get(timeout=0.1)
                    get_count += 1
                except queue.Empty:
                    # 队列空时跳过
                    pass
                except Exception as e:
                    print(f"混合工作者 {worker_id}: 读取出错: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        total_ops = put_count + get_count
        
        # 更新共享统计
        shared_stats[f'mixed_{worker_id}'] = {
            'put_count': put_count,
            'get_count': get_count,
            'total_ops': total_ops,
            'duration': duration,
            'rate': total_ops / duration if duration > 0 else 0
        }
        
        return {'put': put_count, 'get': get_count, 'total': total_ops}
        
    except Exception as e:
        shared_stats[f'mixed_{worker_id}'] = {'error': str(e)}
        return {'error': str(e)}


def mp_queue_monitor(queue_desc_data: Dict[str, Any], monitor_duration: int, shared_stats: Dict):
    """多进程队列监控函数"""
    try:
        # 重建队列描述符
        queue_desc = PythonQueueDescriptor.from_dict(queue_desc_data)
        
        monitor_data = []
        start_time = time.time()
        
        while time.time() - start_time < monitor_duration:
            try:
                current_time = time.time()
                size = queue_desc.qsize()
                empty = queue_desc.empty()
                
                monitor_data.append({
                    'timestamp': current_time,
                    'size': size,
                    'empty': empty
                })
                
                print(f"队列监控: 大小={size}, 空={empty}")
                time.sleep(1)  # 每秒监控一次
                
            except Exception as e:
                print(f"监控出错: {e}")
                break
        
        # 更新共享统计
        shared_stats['monitor'] = {
            'data_points': len(monitor_data),
            'duration': time.time() - start_time,
            'max_size': max(point['size'] for point in monitor_data) if monitor_data else 0,
            'avg_size': sum(point['size'] for point in monitor_data) / len(monitor_data) if monitor_data else 0
        }
        
        return monitor_data
        
    except Exception as e:
        shared_stats['monitor'] = {'error': str(e)}
        return []


# ============ 测试类 ============

class TestPythonQueueMultiprocessing:
    """Python队列多进程测试"""
    
    def test_multiprocessing_queue_creation(self):
        """测试multiprocessing队列创建"""
        print("\n=== 测试multiprocessing队列创建 ===")
        
        # 创建使用multiprocessing的队列描述符
        mp_queue_desc = PythonQueueDescriptor(
            queue_id="test_mp_queue",
            maxsize=100,
            use_multiprocessing=True
        )
        
        print(f"队列ID: {mp_queue_desc.queue_id}")
        print(f"队列类型: {mp_queue_desc.queue_type}")
        print(f"可序列化: {mp_queue_desc.can_serialize}")
        print(f"使用多进程: {mp_queue_desc.metadata.get('use_multiprocessing')}")
        
        # 测试基本操作
        mp_queue_desc.put("test_item")
        assert mp_queue_desc.qsize() == 1
        assert not mp_queue_desc.empty()
        
        item = mp_queue_desc.get()
        assert item == "test_item"
        assert mp_queue_desc.empty()
        
        print("✓ multiprocessing队列创建测试通过")
    
    def test_simple_producer_consumer(self):
        """测试简单的生产者-消费者模式"""
        print("\n=== 测试简单生产者-消费者 ===")
        
        # 创建共享队列
        with Manager() as manager:
            shared_stats = manager.dict()
            
            # 创建multiprocessing队列描述符
            mp_queue_desc = PythonQueueDescriptor(
                queue_id="test_simple_pc",
                maxsize=50,
                use_multiprocessing=True
            )
            
            queue_data = mp_queue_desc.to_dict()
            
            # 启动一个生产者和一个消费者
            producer_process = Process(
                target=mp_producer_worker,
                args=(queue_data, 1, 10, shared_stats)
            )
            
            consumer_process = Process(
                target=mp_consumer_worker,
                args=(queue_data, 1, 10, 5.0, shared_stats)
            )
            
            print("启动生产者和消费者进程...")
            producer_process.start()
            time.sleep(1)  # 让生产者先开始
            consumer_process.start()
            
            # 等待完成
            producer_process.join(timeout=10)
            consumer_process.join(timeout=10)
            
            # 检查结果
            print(f"共享统计: {dict(shared_stats)}")
            
            assert 'producer_1' in shared_stats
            assert 'consumer_1' in shared_stats
            
            producer_stats = shared_stats['producer_1']
            consumer_stats = shared_stats['consumer_1']
            
            print(f"生产者统计: {producer_stats}")
            print(f"消费者统计: {consumer_stats}")
            
            assert producer_stats.get('produced', 0) > 0
            assert consumer_stats.get('consumed', 0) > 0
        
        print("✓ 简单生产者-消费者测试通过")
    
    def test_multiple_processes_concurrent(self):
        """测试多进程并发访问"""
        print("\n=== 测试多进程并发访问 ===")
        
        with Manager() as manager:
            shared_stats = manager.dict()
            
            # 创建大容量队列
            mp_queue_desc = PythonQueueDescriptor(
                queue_id="test_concurrent_mp",
                maxsize=200,
                use_multiprocessing=True
            )
            
            queue_data = mp_queue_desc.to_dict()
            
            # 配置
            num_producers = 3
            num_consumers = 2
            items_per_producer = 15
            total_items = num_producers * items_per_producer
            items_per_consumer = total_items // num_consumers
            
            print(f"配置: {num_producers}个生产者进程, {num_consumers}个消费者进程")
            print(f"每个生产者生产{items_per_producer}个项目, 总共{total_items}个")
            
            # 创建进程列表
            processes = []
            
            # 创建生产者进程
            for i in range(num_producers):
                process = Process(
                    target=mp_producer_worker,
                    args=(queue_data, i, items_per_producer, shared_stats)
                )
                processes.append(process)
            
            # 创建消费者进程
            for i in range(num_consumers):
                process = Process(
                    target=mp_consumer_worker,
                    args=(queue_data, i, items_per_consumer, 3.0, shared_stats)
                )
                processes.append(process)
            
            # 启动所有进程
            start_time = time.time()
            for process in processes:
                process.start()
            
            # 等待所有进程完成
            for process in processes:
                process.join(timeout=30)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 分析结果
            print(f"\n多进程并发测试结果 (耗时: {total_duration:.2f}秒):")
            
            total_produced = 0
            total_consumed = 0
            
            for key, stats in shared_stats.items():
                if key.startswith('producer_'):
                    produced = stats.get('produced', 0)
                    rate = stats.get('rate', 0)
                    total_produced += produced
                    print(f"  {key}: 生产 {produced} 项目, 速率 {rate:.2f} items/sec")
                elif key.startswith('consumer_'):
                    consumed = stats.get('consumed', 0)
                    rate = stats.get('rate', 0)
                    total_consumed += consumed
                    print(f"  {key}: 消费 {consumed} 项目, 速率 {rate:.2f} items/sec")
            
            print(f"\n总计: 生产 {total_produced}, 消费 {total_consumed}")
            
            # 验证
            assert total_produced == total_items, f"应该生产 {total_items} 个项目，实际生产 {total_produced}"
            assert total_consumed > 0, "应该消费了一些项目"
        
        print("✓ 多进程并发访问测试通过")
    
    def test_mixed_operations_with_monitoring(self):
        """测试混合操作与监控"""
        print("\n=== 测试混合操作与监控 ===")
        
        with Manager() as manager:
            shared_stats = manager.dict()
            
            # 创建队列
            mp_queue_desc = PythonQueueDescriptor(
                queue_id="test_mixed_monitor",
                maxsize=100,
                use_multiprocessing=True
            )
            
            # 预填充一些数据
            for i in range(20):
                mp_queue_desc.put(f"prefill_item_{i}")
            
            queue_data = mp_queue_desc.to_dict()
            
            # 配置
            num_mixed_workers = 4
            operations_per_worker = 30
            monitor_duration = 15
            
            print(f"配置: {num_mixed_workers}个混合工作进程, 监控{monitor_duration}秒")
            
            # 创建进程
            processes = []
            
            # 创建监控进程
            monitor_process = Process(
                target=mp_queue_monitor,
                args=(queue_data, monitor_duration, shared_stats)
            )
            processes.append(monitor_process)
            
            # 创建混合工作进程
            for i in range(num_mixed_workers):
                process = Process(
                    target=mp_mixed_worker,
                    args=(queue_data, i, operations_per_worker, shared_stats)
                )
                processes.append(process)
            
            # 启动所有进程
            start_time = time.time()
            for process in processes:
                process.start()
            
            # 等待完成
            for process in processes:
                process.join(timeout=20)
            
            end_time = time.time()
            
            # 分析结果
            print(f"\n混合操作测试结果:")
            
            total_puts = 0
            total_gets = 0
            
            for key, stats in shared_stats.items():
                if key.startswith('mixed_'):
                    put_count = stats.get('put_count', 0)
                    get_count = stats.get('get_count', 0)
                    rate = stats.get('rate', 0)
                    total_puts += put_count
                    total_gets += get_count
                    print(f"  {key}: PUT={put_count}, GET={get_count}, 速率={rate:.2f} ops/sec")
                elif key == 'monitor':
                    print(f"  监控统计: {stats}")
            
            print(f"\n总计: PUT={total_puts}, GET={total_gets}")
            
            # 验证
            assert total_puts > 0, "应该执行了一些PUT操作"
            assert total_gets > 0, "应该执行了一些GET操作"
            assert 'monitor' in shared_stats, "应该有监控数据"
        
        print("✓ 混合操作与监控测试通过")
    
    def test_queue_descriptor_serialization_across_processes(self):
        """测试队列描述符跨进程序列化"""
        print("\n=== 测试队列描述符跨进程序列化 ===")
        
        # 创建队列描述符
        original_desc = PythonQueueDescriptor(
            queue_id="test_serialization",
            maxsize=50,
            use_multiprocessing=True
        )
        
        # 添加一些数据
        test_items = ["serial_item1", "serial_item2", "serial_item3"]
        for item in test_items:
            original_desc.put(item)
        
        print(f"原始队列大小: {original_desc.qsize()}")
        
        # 序列化
        queue_dict = original_desc.to_dict()
        print(f"序列化数据: {queue_dict}")
        
        # 在子进程中反序列化并操作
        def subprocess_operation(queue_data):
            """子进程操作函数"""
            try:
                # 反序列化
                restored_desc = PythonQueueDescriptor.from_dict(queue_data)
                
                # 读取所有数据
                items = []
                while not restored_desc.empty():
                    try:
                        item = restored_desc.get_nowait()
                        items.append(item)
                    except queue.Empty:
                        break
                
                # 写入新数据
                restored_desc.put("subprocess_added_item")
                
                return {
                    'retrieved_items': items,
                    'final_size': restored_desc.qsize()
                }
            except Exception as e:
                return {'error': str(e)}
        
        # 启动子进程
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(subprocess_operation, queue_dict)
            result = future.result()
        
        print(f"子进程操作结果: {result}")
        
        # 验证结果
        assert 'retrieved_items' in result, "应该有检索到的项目"
        assert len(result['retrieved_items']) == len(test_items), "应该检索到所有原始项目"
        assert result['final_size'] == 1, "最终应该有1个项目（子进程添加的）"
        
        # 在主进程中验证
        remaining_item = original_desc.get()
        assert remaining_item == "subprocess_added_item", "应该能获取子进程添加的项目"
        
        print("✓ 跨进程序列化测试通过")


def run_multiprocessing_tests():
    """运行多进程测试"""
    print("开始运行Python队列多进程测试...")
    
    # 设置multiprocessing启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # 已经设置过了
    
    test_suite = TestPythonQueueMultiprocessing()
    
    try:
        test_suite.test_multiprocessing_queue_creation()
        test_suite.test_simple_producer_consumer()
        test_suite.test_multiple_processes_concurrent()
        test_suite.test_mixed_operations_with_monitoring()
        test_suite.test_queue_descriptor_serialization_across_processes()
        
        print("\n🎉 所有Python队列多进程测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 多进程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_multiprocessing_tests()
    if not success:
        sys.exit(1)
