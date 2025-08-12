"""
SAGE Queue 多进程压力测试

专门测试多进程环境下的：
1. 并发读写压力测试
2. 生命周期管控压力测试
3. 资源竞争和内存泄漏测试
4. 极限并发场景测试
"""

import pytest
import time
import multiprocessing as mp
import os
import signal
import gc
import threading
import sys
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from queue import Empty as QueueEmpty

from ..utils import DataGenerator, MessageData

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def stress_producer_worker_func(worker_id: int, queue_names: List[str], 
                               message_count: int, message_size: int) -> Dict[str, Any]:
    """压力测试生产者工作进程（独立函数）"""
    try:
        # 尝试导入真实的 SageQueue
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            use_real_queue = True
        except ImportError:
            from ..mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'messages_sent': 0,
            'errors': [],
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock'
        }
        
        # 创建多个队列连接
        queues = {}
        for queue_name in queue_names:
            try:
                queues[queue_name] = SageQueue(queue_name, maxsize=10000)
            except Exception as e:
                stats['errors'].append(f"Queue creation failed: {e}")
                continue
        
        if not queues:
            stats['errors'].append("No queues available")
            return stats
        
        # 生成测试数据
        test_data = DataGenerator.string(message_size)
        
        # 压力发送消息
        for i in range(message_count):
            # 轮换队列发送
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
                stats['errors'].append(f"Send error at message {i}: {e}")
                if len(stats['errors']) > 10:  # 限制错误记录数量
                    break
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        # 清理队列
        for queue in queues.values():
            try:
                queue.close()
            except:
                pass
        
        return stats
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'messages_sent': 0,
            'errors': [f"Worker failed: {e}"],
            'fatal_error': True
        }


def stress_consumer_worker_func(worker_id: int, queue_names: List[str], 
                               expected_messages: int, timeout: float) -> Dict[str, Any]:
    """压力测试消费者工作进程（独立函数）"""
    try:
        # 尝试导入真实的 SageQueue
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            use_real_queue = True
        except ImportError:
            from ..mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'messages_received': 0,
            'errors': [],
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock'
        }
        
        # 创建多个队列连接
        queues = {}
        for queue_name in queue_names:
            try:
                queues[queue_name] = SageQueue(queue_name, maxsize=10000)
            except Exception as e:
                stats['errors'].append(f"Queue connection failed: {e}")
                continue
        
        if not queues:
            stats['errors'].append("No queues available")
            return stats
        
        # 压力接收消息
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
                        stats['errors'].append(f"Receive error: {e}")
            
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
        
        return stats
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'messages_received': 0,
            'errors': [f"Worker failed: {e}"],
            'fatal_error': True
        }


@dataclass
class StressTestConfig:
    """压力测试配置"""
    num_processes: int = 8
    num_queues: int = 4
    messages_per_process: int = 1000
    message_size: int = 1024
    test_duration: int = 30
    lifecycle_cycles: int = 100
    memory_threshold_mb: int = 100


class MultiprocessStressTester:
    """多进程压力测试器"""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.results = {}
        self.process_pool = None
        
    def setup_shared_state(self):
        """设置共享状态"""
        self.shared_state = {
            'start_time': time.time(),
            'stop_signal': False,
            'total_sent': 0,
            'total_received': 0,
            'error_count': 0,
            'active_processes': 0,
            'memory_samples': []
        }
        # 为了兼容，也设置results
        self.results = self.shared_state
    
    def monitor_memory_usage(self, duration: int):
        """监控内存使用情况"""
        def memory_monitor():
            try:
                import psutil
                process = psutil.Process()
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    try:
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        self.shared_state['memory_samples'].append({
                            'timestamp': time.time(),
                            'memory_mb': memory_mb,
                            'active_processes': self.shared_state.get('active_processes', 0)
                        })
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"Memory monitor error: {e}")
                        break
            except ImportError:
                print("psutil not available for memory monitoring")
        
        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()
        return monitor_thread

    def stress_producer_worker(self, worker_id: int, queue_names: List[str], 
                             message_count: int, message_size: int) -> Dict[str, Any]:
        """压力测试生产者工作进程"""
        try:
            # 尝试导入真实的 SageQueue
            try:
                from sage.extensions.sage_queue.python.sage_queue import SageQueue
                use_real_queue = True
            except ImportError:
                from ..mock_sage_queue import MockSageQueue as SageQueue
                use_real_queue = False
            
            stats = {
                'worker_id': worker_id,
                'messages_sent': 0,
                'errors': [],
                'start_time': time.time(),
                'queue_type': 'real' if use_real_queue else 'mock'
            }
            
            # 创建多个队列连接
            queues = {}
            for queue_name in queue_names:
                try:
                    queues[queue_name] = SageQueue(queue_name, maxsize=10000)
                except Exception as e:
                    stats['errors'].append(f"Queue creation failed: {e}")
                    continue
            
            if not queues:
                stats['errors'].append("No queues available")
                return stats
            
            # 生成测试数据
            test_data = DataGenerator.string(message_size)
            
            # 压力发送消息
            for i in range(message_count):
                if self.shared_state.get('stop_signal', False):
                    break
                
                # 轮换队列发送
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
                    
                    # 定期更新共享统计
                    if i % 100 == 0:
                        self.shared_state['total_sent'] = self.shared_state.get('total_sent', 0) + 100
                
                except Exception as e:
                    stats['errors'].append(f"Send error at message {i}: {e}")
                    if len(stats['errors']) > 10:  # 限制错误记录数量
                        break
            
            stats['end_time'] = time.time()
            stats['duration'] = stats['end_time'] - stats['start_time']
            
            # 清理队列
            for queue in queues.values():
                try:
                    queue.close()
                except:
                    pass
            
            self.shared_state['active_processes'] = self.shared_state.get('active_processes', 1) - 1
            return stats
            
        except Exception as e:
            return {
                'worker_id': worker_id,
                'messages_sent': 0,
                'errors': [f"Worker failed: {e}"],
                'fatal_error': True
            }

    def stress_consumer_worker(self, worker_id: int, queue_names: List[str], 
                             expected_messages: int, timeout: float) -> Dict[str, Any]:
        """压力测试消费者工作进程"""
        try:
            # 尝试导入真实的 SageQueue
            try:
                from sage.extensions.sage_queue.python.sage_queue import SageQueue
                use_real_queue = True
            except ImportError:
                from ..mock_sage_queue import MockSageQueue as SageQueue
                use_real_queue = False
            
            stats = {
                'worker_id': worker_id,
                'messages_received': 0,
                'errors': [],
                'start_time': time.time(),
                'queue_type': 'real' if use_real_queue else 'mock'
            }
            
            # 创建多个队列连接
            queues = {}
            for queue_name in queue_names:
                try:
                    queues[queue_name] = SageQueue(queue_name)
                except Exception as e:
                    stats['errors'].append(f"Queue connection failed: {e}")
                    continue
            
            if not queues:
                stats['errors'].append("No queues available")
                return stats
            
            # 压力接收消息
            received_count = 0
            start_time = time.time()
            
            while received_count < expected_messages and not self.shared_state.get('stop_signal', False):
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
                        
                        # 定期更新共享统计
                        if received_count % 100 == 0:
                            self.shared_state['total_received'] = self.shared_state.get('total_received', 0) + 100
                        
                        if received_count >= expected_messages:
                            break
                            
                    except Exception as e:
                        if "timeout" not in str(e).lower() and "empty" not in str(e).lower():
                            stats['errors'].append(f"Receive error: {e}")
                
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
            
            self.shared_state['active_processes'] = self.shared_state.get('active_processes', 1) - 1
            return stats
            
        except Exception as e:
            return {
                'worker_id': worker_id,
                'messages_received': 0,
                'errors': [f"Worker failed: {e}"],
                'fatal_error': True
            }

    def lifecycle_stress_worker(self, worker_id: int, cycles: int) -> Dict[str, Any]:
        """生命周期压力测试工作进程"""
        try:
            # 尝试导入真实的 SageQueue
            try:
                from sage.extensions.sage_queue.python.sage_queue import SageQueue
                use_real_queue = True
            except ImportError:
                from ..mock_sage_queue import MockSageQueue as SageQueue
                use_real_queue = False
            
            stats = {
                'worker_id': worker_id,
                'cycles_completed': 0,
                'creation_errors': 0,
                'destruction_errors': 0,
                'operation_errors': 0,
                'start_time': time.time(),
                'queue_type': 'real' if use_real_queue else 'mock'
            }
            
            for cycle in range(cycles):
                if self.shared_state.get('stop_signal', False):
                    break
                
                queue_name = f"lifecycle_test_{worker_id}_{cycle}"
                queue = None
                
                try:
                    # 创建队列
                    queue = SageQueue(queue_name, maxsize=1000)
                    
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
                
                # 强制垃圾回收
                if cycle % 10 == 0:
                    gc.collect()
            
            stats['end_time'] = time.time()
            stats['duration'] = stats['end_time'] - stats['start_time']
            return stats
            
        except Exception as e:
            return {
                'worker_id': worker_id,
                'cycles_completed': 0,
                'errors': [f"Worker failed: {e}"],
                'fatal_error': True
            }


@pytest.mark.stress
@pytest.mark.multiprocess
class TestMultiprocessStress:
    """多进程压力测试类"""
    
    def test_concurrent_read_write_stress(self):
        """测试多进程并发读写压力"""
        config = StressTestConfig(
            num_processes=8,
            num_queues=4,
            messages_per_process=500,
            message_size=1024,
            test_duration=30
        )
        
        tester = MultiprocessStressTester(config)
        tester.setup_shared_state()
        
        # 启动内存监控
        memory_monitor = tester.monitor_memory_usage(config.test_duration + 10)
        
        queue_names = [f"stress_queue_{i}" for i in range(config.num_queues)]
        
        # 启动生产者和消费者进程
        with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
            futures = []
            
            # 启动生产者进程
            num_producers = config.num_processes // 2
            for i in range(num_producers):
                future = executor.submit(
                    stress_producer_worker_func,
                    i,
                    queue_names,
                    config.messages_per_process,
                    config.message_size
                )
                futures.append(('producer', future))
            
            # 启动消费者进程
            num_consumers = config.num_processes - num_producers
            expected_per_consumer = (num_producers * config.messages_per_process) // num_consumers
            
            for i in range(num_consumers):
                future = executor.submit(
                    stress_consumer_worker_func,
                    i + num_producers,
                    queue_names,
                    expected_per_consumer,
                    config.test_duration
                )
                futures.append(('consumer', future))
            
            # 等待所有进程完成
            producer_stats = []
            consumer_stats = []
            
            for worker_type, future in futures:
                try:
                    result = future.result(timeout=config.test_duration + 10)
                    if worker_type == 'producer':
                        producer_stats.append(result)
                    else:
                        consumer_stats.append(result)
                except Exception as e:
                    print(f"Process failed: {e}")
        
        # 停止内存监控
        tester.shared_state['stop_signal'] = True
        
        # 分析结果
        self._analyze_stress_results(producer_stats, consumer_stats, tester.shared_state)

    def test_lifecycle_management_stress(self):
        """测试多进程生命周期管控压力"""
        config = StressTestConfig(
            num_processes=6,
            lifecycle_cycles=50,
            test_duration=60
        )
        
        tester = MultiprocessStressTester(config)
        tester.setup_shared_state()
        
        # 启动内存监控
        memory_monitor = tester.monitor_memory_usage(config.test_duration + 10)
        
        # 启动生命周期压力测试
        with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
            futures = []
            
            for i in range(config.num_processes):
                future = executor.submit(
                    tester.lifecycle_stress_worker,
                    i,
                    config.lifecycle_cycles
                )
                futures.append(future)
            
            # 等待所有进程完成
            lifecycle_stats = []
            for future in futures:
                try:
                    result = future.result(timeout=config.test_duration + 10)
                    lifecycle_stats.append(result)
                except Exception as e:
                    print(f"Lifecycle process failed: {e}")
        
        # 停止监控
        tester.shared_state['stop_signal'] = True
        
        # 分析生命周期结果
        self._analyze_lifecycle_results(lifecycle_stats, tester.shared_state)

    def test_memory_pressure_stress(self):
        """测试内存压力下的多进程操作"""
        config = StressTestConfig(
            num_processes=4,
            num_queues=2,
            messages_per_process=2000,
            message_size=4096,  # 更大的消息
            test_duration=45,
            memory_threshold_mb=200
        )
        
        tester = MultiprocessStressTester(config)
        tester.setup_shared_state()
        
        # 启动内存监控
        memory_monitor = tester.monitor_memory_usage(config.test_duration + 10)
        
        queue_names = [f"memory_stress_queue_{i}" for i in range(config.num_queues)]
        
        # 分阶段执行压力测试
        phases = [
            ("warm_up", 0.2),
            ("ramp_up", 0.3),
            ("peak_load", 0.3),
            ("cool_down", 0.2)
        ]
        
        all_stats = []
        
        for phase_name, duration_ratio in phases:
            phase_duration = int(config.test_duration * duration_ratio)
            print(f"Starting phase: {phase_name} (duration: {phase_duration}s)")
            
            with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
                futures = []
                
                # 调整每个阶段的负载
                if phase_name == "peak_load":
                    messages_per_process = config.messages_per_process
                    message_size = config.message_size
                else:
                    messages_per_process = config.messages_per_process // 2
                    message_size = config.message_size // 2
                
                # 启动混合工作负载
                for i in range(config.num_processes // 2):
                    # 生产者
                    future = executor.submit(
                        stress_producer_worker_func,
                        f"{phase_name}_prod_{i}",
                        queue_names,
                        messages_per_process,
                        message_size
                    )
                    futures.append(('producer', future))
                    
                    # 消费者
                    future = executor.submit(
                        stress_consumer_worker_func,
                        f"{phase_name}_cons_{i}",
                        queue_names,
                        messages_per_process,
                        phase_duration
                    )
                    futures.append(('consumer', future))
                
                # 收集阶段结果
                phase_stats = []
                for worker_type, future in futures:
                    try:
                        result = future.result(timeout=phase_duration + 5)
                        result['phase'] = phase_name
                        phase_stats.append(result)
                    except Exception as e:
                        print(f"Phase {phase_name} process failed: {e}")
                
                all_stats.extend(phase_stats)
            
            # 阶段间休息
            time.sleep(1)
        
        # 停止监控
        tester.shared_state['stop_signal'] = True
        
        # 分析内存压力结果
        self._analyze_memory_pressure_results(all_stats, tester.shared_state, config)

    def test_extreme_concurrency_stress(self):
        """测试极限并发场景"""
        config = StressTestConfig(
            num_processes=16,  # 极限并发
            num_queues=8,
            messages_per_process=100,
            message_size=512,
            test_duration=20
        )
        
        tester = MultiprocessStressTester(config)
        tester.setup_shared_state()
        
        # 启动内存监控
        memory_monitor = tester.monitor_memory_usage(config.test_duration + 10)
        
        queue_names = [f"extreme_queue_{i}" for i in range(config.num_queues)]
        
        # 极限并发测试
        with ProcessPoolExecutor(max_workers=config.num_processes) as executor:
            futures = []
            
            # 混合启动大量进程
            for i in range(config.num_processes):
                if i % 3 == 0:
                    # 生产者
                    future = executor.submit(
                        stress_producer_worker_func,
                        f"extreme_prod_{i}",
                        queue_names,
                        config.messages_per_process,
                        config.message_size
                    )
                    futures.append(('producer', future))
                elif i % 3 == 1:
                    # 消费者
                    future = executor.submit(
                        stress_consumer_worker_func,
                        f"extreme_cons_{i}",
                        queue_names,
                        config.messages_per_process,
                        config.test_duration
                    )
                    futures.append(('consumer', future))
                else:
                    # 生命周期测试
                    future = executor.submit(
                        tester.lifecycle_stress_worker,
                        f"extreme_lifecycle_{i}",
                        20  # 较少的循环次数
                    )
                    futures.append(('lifecycle', future))
            
            # 收集结果
            extreme_stats = []
            for worker_type, future in futures:
                try:
                    result = future.result(timeout=config.test_duration + 10)
                    result['worker_type'] = worker_type
                    extreme_stats.append(result)
                except Exception as e:
                    print(f"Extreme concurrency process failed: {e}")
        
        # 停止监控
        tester.shared_state['stop_signal'] = True
        
        # 分析极限并发结果
        self._analyze_extreme_concurrency_results(extreme_stats, tester.shared_state)

    def _analyze_stress_results(self, producer_stats: List[Dict], 
                               consumer_stats: List[Dict], shared_state: Dict):
        """分析压力测试结果"""
        print("\n=== 多进程并发读写压力测试结果 ===")
        
        # 生产者统计
        total_sent = sum(stat['messages_sent'] for stat in producer_stats)
        producer_errors = sum(len(stat.get('errors', [])) for stat in producer_stats)
        avg_producer_throughput = total_sent / max(stat.get('duration', 1) for stat in producer_stats)
        
        print(f"生产者统计:")
        print(f"  - 总消息发送: {total_sent}")
        print(f"  - 发送错误数: {producer_errors}")
        print(f"  - 平均吞吐量: {avg_producer_throughput:.2f} msg/s")
        
        # 消费者统计
        total_received = sum(stat['messages_received'] for stat in consumer_stats)
        consumer_errors = sum(len(stat.get('errors', [])) for stat in consumer_stats)
        avg_consumer_throughput = total_received / max(stat.get('duration', 1) for stat in consumer_stats)
        
        print(f"消费者统计:")
        print(f"  - 总消息接收: {total_received}")
        print(f"  - 接收错误数: {consumer_errors}")
        print(f"  - 平均吞吐量: {avg_consumer_throughput:.2f} msg/s")
        
        # 内存使用统计
        memory_samples = list(shared_state.get('memory_samples', []))
        if memory_samples:
            max_memory = max(sample['memory_mb'] for sample in memory_samples)
            avg_memory = sum(sample['memory_mb'] for sample in memory_samples) / len(memory_samples)
            print(f"内存使用:")
            print(f"  - 最大内存: {max_memory:.2f} MB")
            print(f"  - 平均内存: {avg_memory:.2f} MB")
        
        # 断言验证
        assert total_sent > 0, "没有消息被发送"
        assert total_received > 0, "没有消息被接收"
        assert producer_errors < total_sent * 0.1, f"生产者错误率过高: {producer_errors}/{total_sent}"
        assert consumer_errors < total_received * 0.1, f"消费者错误率过高: {consumer_errors}/{total_received}"

    def _analyze_lifecycle_results(self, lifecycle_stats: List[Dict], shared_state: Dict):
        """分析生命周期测试结果"""
        print("\n=== 多进程生命周期管控压力测试结果 ===")
        
        total_cycles = sum(stat['cycles_completed'] for stat in lifecycle_stats)
        creation_errors = sum(stat['creation_errors'] for stat in lifecycle_stats)
        destruction_errors = sum(stat['destruction_errors'] for stat in lifecycle_stats)
        operation_errors = sum(stat['operation_errors'] for stat in lifecycle_stats)
        
        print(f"生命周期统计:")
        print(f"  - 总循环完成: {total_cycles}")
        print(f"  - 创建错误: {creation_errors}")
        print(f"  - 销毁错误: {destruction_errors}")
        print(f"  - 操作错误: {operation_errors}")
        
        # 内存使用统计
        memory_samples = list(shared_state.get('memory_samples', []))
        if memory_samples:
            memory_trend = [sample['memory_mb'] for sample in memory_samples[-10:]]  # 最后10个样本
            memory_growth = memory_trend[-1] - memory_trend[0] if len(memory_trend) > 1 else 0
            print(f"内存趋势: {memory_growth:+.2f} MB (最后10个样本)")
        
        # 断言验证
        assert total_cycles > 0, "没有完成任何生命周期循环"
        assert creation_errors == 0, f"队列创建失败: {creation_errors}"
        assert destruction_errors < total_cycles * 0.05, f"队列销毁失败率过高: {destruction_errors}/{total_cycles}"

    def _analyze_memory_pressure_results(self, all_stats: List[Dict], 
                                       shared_state: Dict, config: StressTestConfig):
        """分析内存压力测试结果"""
        print("\n=== 内存压力下多进程操作测试结果 ===")
        
        # 按阶段分析
        phases = {}
        for stat in all_stats:
            phase = stat.get('phase', 'unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(stat)
        
        for phase, stats in phases.items():
            total_ops = sum(stat.get('messages_sent', 0) + stat.get('messages_received', 0) for stat in stats)
            total_errors = sum(len(stat.get('errors', [])) for stat in stats)
            print(f"阶段 {phase}: {total_ops} 操作, {total_errors} 错误")
        
        # 内存使用分析
        memory_samples = list(shared_state.get('memory_samples', []))
        if memory_samples:
            peak_memory = max(sample['memory_mb'] for sample in memory_samples)
            print(f"峰值内存使用: {peak_memory:.2f} MB")
            
            # 检查内存阈值
            assert peak_memory < config.memory_threshold_mb, f"内存使用超过阈值: {peak_memory} > {config.memory_threshold_mb} MB"

    def _analyze_extreme_concurrency_results(self, extreme_stats: List[Dict], shared_state: Dict):
        """分析极限并发测试结果"""
        print("\n=== 极限并发场景测试结果 ===")
        
        # 按工作类型统计
        by_type = {}
        for stat in extreme_stats:
            worker_type = stat.get('worker_type', 'unknown')
            if worker_type not in by_type:
                by_type[worker_type] = []
            by_type[worker_type].append(stat)
        
        for worker_type, stats in by_type.items():
            successful = len([s for s in stats if not s.get('fatal_error', False)])
            failed = len(stats) - successful
            print(f"{worker_type}: {successful} 成功, {failed} 失败")
        
        # 系统稳定性检查
        total_processes = len(extreme_stats)
        successful_processes = len([s for s in extreme_stats if not s.get('fatal_error', False)])
        success_rate = successful_processes / total_processes if total_processes > 0 else 0
        
        print(f"系统稳定性: {success_rate:.2%} ({successful_processes}/{total_processes})")
        
        # 断言验证
        assert success_rate >= 0.8, f"极限并发下系统稳定性不足: {success_rate:.2%}"


# 便利函数用于独立运行压力测试
def run_stress_tests():
    """运行所有压力测试"""
    import subprocess
    import sys
    
    test_commands = [
        "python -m pytest stress/test_multiprocess_stress.py::TestMultiprocessStress::test_concurrent_read_write_stress -v",
        "python -m pytest stress/test_multiprocess_stress.py::TestMultiprocessStress::test_lifecycle_management_stress -v",
        "python -m pytest stress/test_multiprocess_stress.py::TestMultiprocessStress::test_memory_pressure_stress -v",
        "python -m pytest stress/test_multiprocess_stress.py::TestMultiprocessStress::test_extreme_concurrency_stress -v"
    ]
    
    for cmd in test_commands:
        print(f"\n{'='*60}")
        print(f"执行: {cmd}")
        print('='*60)
        result = subprocess.run(cmd.split(), capture_output=False)
        if result.returncode != 0:
            print(f"测试失败: {cmd}")
            return False
    
    return True


if __name__ == "__main__":
    # 独立运行时执行所有压力测试
    success = run_stress_tests()
    sys.exit(0 if success else 1)
