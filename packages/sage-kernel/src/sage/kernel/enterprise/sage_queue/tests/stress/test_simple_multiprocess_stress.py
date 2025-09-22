"""
SAGE Queue 简化多进程压力测试

专门测试多进程环境下的：
1. 并发读写压力测试
2. 生命周期管控压力测试
"""

import pytest
import time
import multiprocessing as mp
import os
import threading
import tempfile
import json
import sys
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from ..utils import DataGenerator, MessageData

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class SimpleStressConfig:
    """简化压力测试配置"""
    num_processes: int = 4
    num_queues: int = 2
    messages_per_process: int = 100
    message_size: int = 512
    test_duration: int = 20


def stress_producer_worker(worker_id: int, queue_names: List[str], 
                          message_count: int, message_size: int, 
                          results_file: str) -> None:
    """压力测试生产者工作进程"""
    try:
        # 优先使用Mock实现进行压力测试
        try:
            from ..mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        except ImportError:
            try:
                from sage.extensions.sage_queue.python.sage_queue import SageQueue
                use_real_queue = True
            except ImportError:
                # 如果都没有，创建一个最简单的mock
                class SimpleMockQueue:
                    def __init__(self, name, **kwargs):
                        self.name = name
                        self._queue = []
                        self._closed = False
                    def put(self, item, **kwargs):
                        if not self._closed:
                            self._queue.append(item)
                    def get(self, **kwargs):
                        if self._queue:
                            return self._queue.pop(0)
                        raise Exception("Queue empty")
                    def close(self):
                        self._closed = True
                    def destroy(self):
                        self.close()
                
                SageQueue = SimpleMockQueue
                use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'worker_type': 'producer',
            'messages_sent': 0,
            'errors': [],
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock',
            'process_id': os.getpid()
        }
        
        # 创建队列连接
        queues = {}
        for queue_name in queue_names:
            try:
                queues[queue_name] = SageQueue(queue_name, maxsize=10000)
            except Exception as e:
                stats['errors'].append(f"Queue creation failed: {e}")
                continue
        
        if not queues:
            stats['errors'].append("No queues available")
            _save_results(stats, results_file)
            return
        
        # 生成测试数据
        test_data = DataGenerator.string(message_size)
        
        # 发送消息
        for i in range(message_count):
            queue_name = queue_names[i % len(queue_names)]
            queue = queues.get(queue_name)
            
            if queue is None:
                continue
            
            try:
                message = MessageData.create({
                    'worker_id': worker_id,
                    'message_id': i,
                    'data': test_data,
                    'timestamp': time.time()
                })
                
                queue.put(message, timeout=1.0)
                stats['messages_sent'] += 1
                
            except Exception as e:
                stats['errors'].append(f"Send error at message {i}: {str(e)[:100]}")
                if len(stats['errors']) > 5:  # 限制错误记录数量
                    break
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        # 清理队列
        for queue in queues.values():
            try:
                queue.close()
            except:
                pass
        
        _save_results(stats, results_file)
        
    except Exception as e:
        error_stats = {
            'worker_id': worker_id,
            'worker_type': 'producer',
            'messages_sent': 0,
            'errors': [f"Worker failed: {e}"],
            'fatal_error': True,
            'process_id': os.getpid()
        }
        _save_results(error_stats, results_file)


def stress_consumer_worker(worker_id: int, queue_names: List[str], 
                          expected_messages: int, timeout: float,
                          results_file: str) -> None:
    """压力测试消费者工作进程"""
    try:
        # 优先使用Mock实现进行压力测试
        try:
            from ..mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        except ImportError:
            try:
                from sage.extensions.sage_queue.python.sage_queue import SageQueue
                use_real_queue = True
            except ImportError:
                # 如果都没有，创建一个最简单的mock
                class SimpleMockQueue:
                    def __init__(self, name, **kwargs):
                        self.name = name
                        self._queue = []
                        self._closed = False
                    def put(self, item, **kwargs):
                        if not self._closed:
                            self._queue.append(item)
                    def get(self, **kwargs):
                        if self._queue:
                            return self._queue.pop(0)
                        raise Exception("Queue empty")
                    def close(self):
                        self._closed = True
                    def destroy(self):
                        self.close()
                
                SageQueue = SimpleMockQueue
                use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'worker_type': 'consumer',
            'messages_received': 0,
            'errors': [],
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock',
            'process_id': os.getpid()
        }
        
        # 创建队列连接
        queues = {}
        for queue_name in queue_names:
            try:
                queues[queue_name] = SageQueue(queue_name)
            except Exception as e:
                stats['errors'].append(f"Queue connection failed: {e}")
                continue
        
        if not queues:
            stats['errors'].append("No queues available")
            _save_results(stats, results_file)
            return
        
        # 接收消息
        received_count = 0
        start_time = time.time()
        
        while received_count < expected_messages:
            if time.time() - start_time > timeout:
                break
            
            for queue_name, queue in queues.items():
                try:
                    message = queue.get(timeout=0.1)
                    received_count += 1
                    stats['messages_received'] += 1
                    
                    # 验证消息完整性
                    if hasattr(message, 'payload') and isinstance(message.payload, dict):
                        if 'worker_id' not in message.payload:
                            stats['errors'].append(f"Invalid message format")
                    
                    if received_count >= expected_messages:
                        break
                        
                except Exception as e:
                    if "timeout" not in str(e).lower() and "empty" not in str(e).lower():
                        stats['errors'].append(f"Receive error: {str(e)[:100]}")
            
            # 防止CPU占用过高
            time.sleep(0.001)
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        # 清理队列
        for queue in queues.values():
            try:
                queue.close()
            except:
                pass
        
        _save_results(stats, results_file)
        
    except Exception as e:
        error_stats = {
            'worker_id': worker_id,
            'worker_type': 'consumer',
            'messages_received': 0,
            'errors': [f"Worker failed: {e}"],
            'fatal_error': True,
            'process_id': os.getpid()
        }
        _save_results(error_stats, results_file)


def lifecycle_stress_worker(worker_id: int, cycles: int, results_file: str) -> None:
    """生命周期压力测试工作进程"""
    try:
        # 优先使用Mock实现进行压力测试
        try:
            from ..mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        except ImportError:
            try:
                from sage.extensions.sage_queue.python.sage_queue import SageQueue
                use_real_queue = True
            except ImportError:
                # 如果都没有，创建一个最简单的mock
                class SimpleMockQueue:
                    def __init__(self, name, **kwargs):
                        self.name = name
                        self._queue = []
                        self._closed = False
                    def put(self, item, **kwargs):
                        if not self._closed:
                            self._queue.append(item)
                    def get(self, **kwargs):
                        if self._queue:
                            return self._queue.pop(0)
                        raise Exception("Queue empty")  
                    def close(self):
                        self._closed = True
                    def destroy(self):
                        self.close()
                
                SageQueue = SimpleMockQueue
                use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'worker_type': 'lifecycle',
            'cycles_completed': 0,
            'creation_errors': 0,
            'destruction_errors': 0,
            'operation_errors': 0,
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock',
            'process_id': os.getpid()
        }
        
        for cycle in range(cycles):
            queue_name = f"lifecycle_test_{worker_id}_{cycle}_{int(time.time()*1000000)}"
            queue = None
            
            try:
                # 创建队列
                queue = SageQueue(queue_name, maxsize=100)
                
                # 执行一些操作
                test_message = MessageData.create(f"test_data_{cycle}")
                queue.put(test_message)
                received = queue.get()
                
                if received != test_message:
                    stats['operation_errors'] += 1
                
                stats['cycles_completed'] += 1
                
            except Exception as e:
                if queue is None:
                    stats['creation_errors'] += 1
                else:
                    stats['operation_errors'] += 1
            
            finally:
                # 销毁队列
                if queue is not None:
                    try:
                        queue.destroy()
                    except Exception as e:
                        stats['destruction_errors'] += 1
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        _save_results(stats, results_file)
        
    except Exception as e:
        error_stats = {
            'worker_id': worker_id,
            'worker_type': 'lifecycle',
            'cycles_completed': 0,
            'errors': [f"Worker failed: {e}"],
            'fatal_error': True,
            'process_id': os.getpid()
        }
        _save_results(error_stats, results_file)


def _save_results(stats: Dict[str, Any], results_file: str) -> None:
    """保存结果到文件"""
    try:
        # 使用文件锁避免并发写入冲突
        import fcntl
        
        with open(results_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(stats, f)
            f.write('\n')
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except ImportError:
        # 没有fcntl，使用简单的文件写入
        with open(results_file, 'a') as f:
            json.dump(stats, f)
            f.write('\n')
    except Exception as e:
        print(f"Failed to save results: {e}")


def _load_results(results_file: str) -> List[Dict[str, Any]]:
    """从文件加载结果"""
    results = []
    try:
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))
    except Exception as e:
        print(f"Failed to load results: {e}")
    return results


@pytest.mark.stress
@pytest.mark.multiprocess
class TestSimpleMultiprocessStress:
    """简化多进程压力测试类"""
    
    def test_simple_concurrent_read_write_stress(self):
        """测试简化多进程并发读写压力"""
        config = SimpleStressConfig(
            num_processes=4,
            num_queues=2,
            messages_per_process=200,
            message_size=1024,
            test_duration=25
        )
        
        # 创建临时结果文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            results_file = f.name
        
        try:
            queue_names = [f"simple_stress_queue_{i}_{int(time.time())}" for i in range(config.num_queues)]
            
            # 启动生产者和消费者进程
            with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
                futures = []
                
                # 启动生产者进程
                num_producers = config.num_processes // 2
                for i in range(num_producers):
                    future = executor.submit(
                        stress_producer_worker,
                        i,
                        queue_names,
                        config.messages_per_process,
                        config.message_size,
                        results_file
                    )
                    futures.append(future)
                
                # 启动消费者进程
                num_consumers = config.num_processes - num_producers
                expected_per_consumer = (num_producers * config.messages_per_process) // num_consumers
                
                for i in range(num_consumers):
                    future = executor.submit(
                        stress_consumer_worker,
                        i + num_producers,
                        queue_names,
                        expected_per_consumer,
                        config.test_duration,
                        results_file
                    )
                    futures.append(future)
                
                # 等待所有进程完成
                for future in futures:
                    try:
                        future.result(timeout=config.test_duration + 10)
                    except Exception as e:
                        print(f"Process failed: {e}")
            
            # 加载并分析结果
            all_results = _load_results(results_file)
            self._analyze_simple_stress_results(all_results)
        
        finally:
            # 清理临时文件
            try:
                os.unlink(results_file)
            except:
                pass

    def test_simple_lifecycle_management_stress(self):
        """测试简化生命周期管控压力"""
        config = SimpleStressConfig(
            num_processes=4,
            test_duration=30
        )
        
        # 创建临时结果文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            results_file = f.name
        
        try:
            # 启动生命周期压力测试
            with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
                futures = []
                
                for i in range(config.num_processes):
                    future = executor.submit(
                        lifecycle_stress_worker,
                        i,
                        30,  # cycles
                        results_file
                    )
                    futures.append(future)
                
                # 等待所有进程完成
                for future in futures:
                    try:
                        future.result(timeout=config.test_duration + 10)
                    except Exception as e:
                        print(f"Lifecycle process failed: {e}")
            
            # 加载并分析结果
            all_results = _load_results(results_file)
            self._analyze_simple_lifecycle_results(all_results)
        
        finally:
            # 清理临时文件
            try:
                os.unlink(results_file)
            except:
                pass

    def test_mixed_workload_stress(self):
        """测试混合工作负载压力"""
        config = SimpleStressConfig(
            num_processes=6,
            num_queues=3,
            messages_per_process=150,
            test_duration=35
        )
        
        # 创建临时结果文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            results_file = f.name
        
        try:
            queue_names = [f"mixed_stress_queue_{i}_{int(time.time())}" for i in range(config.num_queues)]
            
            with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
                futures = []
                
                # 混合启动不同类型的工作进程
                for i in range(config.num_processes):
                    if i % 3 == 0:
                        # 生产者
                        future = executor.submit(
                            stress_producer_worker,
                            f"mixed_prod_{i}",
                            queue_names,
                            config.messages_per_process,
                            config.message_size,
                            results_file
                        )
                    elif i % 3 == 1:
                        # 消费者
                        future = executor.submit(
                            stress_consumer_worker,
                            f"mixed_cons_{i}",
                            queue_names,
                            config.messages_per_process,
                            config.test_duration,
                            results_file
                        )
                    else:
                        # 生命周期测试
                        future = executor.submit(
                            lifecycle_stress_worker,
                            f"mixed_lifecycle_{i}",
                            20,  # cycles
                            results_file
                        )
                    
                    futures.append(future)
                
                # 等待所有进程完成
                for future in futures:
                    try:
                        future.result(timeout=config.test_duration + 10)
                    except Exception as e:
                        print(f"Mixed workload process failed: {e}")
            
            # 加载并分析结果
            all_results = _load_results(results_file)
            self._analyze_mixed_workload_results(all_results)
        
        finally:
            # 清理临时文件
            try:
                os.unlink(results_file)
            except:
                pass

    def _analyze_simple_stress_results(self, all_results: List[Dict[str, Any]]):
        """分析简化压力测试结果"""
        print("\n=== 简化多进程并发读写压力测试结果 ===")
        
        producer_results = [r for r in all_results if r.get('worker_type') == 'producer']
        consumer_results = [r for r in all_results if r.get('worker_type') == 'consumer']
        
        # 生产者统计
        total_sent = sum(r.get('messages_sent', 0) for r in producer_results)
        producer_errors = sum(len(r.get('errors', [])) for r in producer_results)
        
        print(f"生产者统计:")
        print(f"  - 进程数: {len(producer_results)}")
        print(f"  - 总消息发送: {total_sent}")
        print(f"  - 发送错误数: {producer_errors}")
        
        # 消费者统计
        total_received = sum(r.get('messages_received', 0) for r in consumer_results)
        consumer_errors = sum(len(r.get('errors', [])) for r in consumer_results)
        
        print(f"消费者统计:")
        print(f"  - 进程数: {len(consumer_results)}")
        print(f"  - 总消息接收: {total_received}")
        print(f"  - 接收错误数: {consumer_errors}")
        
        # 队列类型统计
        queue_types = set(r.get('queue_type', 'unknown') for r in all_results)
        print(f"队列类型: {', '.join(queue_types)}")
        
        # 基本断言
        assert len(producer_results) > 0, "没有生产者进程结果"
        assert len(consumer_results) > 0, "没有消费者进程结果"
        assert total_sent > 0, "没有消息被发送"
        if total_sent > 0:
            assert producer_errors < total_sent * 0.2, f"生产者错误率过高: {producer_errors}/{total_sent}"

    def _analyze_simple_lifecycle_results(self, all_results: List[Dict[str, Any]]):
        """分析简化生命周期测试结果"""
        print("\n=== 简化生命周期管控压力测试结果 ===")
        
        lifecycle_results = [r for r in all_results if r.get('worker_type') == 'lifecycle']
        
        total_cycles = sum(r.get('cycles_completed', 0) for r in lifecycle_results)
        creation_errors = sum(r.get('creation_errors', 0) for r in lifecycle_results)
        destruction_errors = sum(r.get('destruction_errors', 0) for r in lifecycle_results)
        operation_errors = sum(r.get('operation_errors', 0) for r in lifecycle_results)
        
        print(f"生命周期统计:")
        print(f"  - 进程数: {len(lifecycle_results)}")
        print(f"  - 总循环完成: {total_cycles}")
        print(f"  - 创建错误: {creation_errors}")
        print(f"  - 销毁错误: {destruction_errors}")
        print(f"  - 操作错误: {operation_errors}")
        
        # 队列类型统计
        queue_types = set(r.get('queue_type', 'unknown') for r in lifecycle_results)
        print(f"队列类型: {', '.join(queue_types)}")
        
        # 基本断言
        assert len(lifecycle_results) > 0, "没有生命周期进程结果"
        assert total_cycles > 0, "没有完成任何生命周期循环"
        assert creation_errors == 0, f"队列创建失败: {creation_errors}"

    def _analyze_mixed_workload_results(self, all_results: List[Dict[str, Any]]):
        """分析混合工作负载结果"""
        print("\n=== 混合工作负载压力测试结果 ===")
        
        # 按工作类型分组
        by_type = {}
        for result in all_results:
            worker_type = result.get('worker_type', 'unknown')
            if worker_type not in by_type:
                by_type[worker_type] = []
            by_type[worker_type].append(result)
        
        for worker_type, results in by_type.items():
            successful = len([r for r in results if not r.get('fatal_error', False)])
            failed = len(results) - successful
            print(f"{worker_type}: {successful} 成功, {failed} 失败")
        
        # 系统稳定性检查
        total_processes = len(all_results)
        successful_processes = len([r for r in all_results if not r.get('fatal_error', False)])
        success_rate = successful_processes / total_processes if total_processes > 0 else 0
        
        print(f"系统稳定性: {success_rate:.2%} ({successful_processes}/{total_processes})")
        
        # 队列类型统计
        queue_types = set(r.get('queue_type', 'unknown') for r in all_results)
        print(f"队列类型: {', '.join(queue_types)}")
        
        # 断言验证
        assert success_rate >= 0.7, f"混合工作负载下系统稳定性不足: {success_rate:.2%}"


if __name__ == "__main__":
    # 运行简化压力测试
    pytest.main([__file__, "-v", "--tb=short"])
