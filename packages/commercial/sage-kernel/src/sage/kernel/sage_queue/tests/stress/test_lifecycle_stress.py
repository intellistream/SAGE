"""
SAGE Queue 生命周期管控专项压力测试

专门测试队列的创建、销毁、资源管理等生命周期相关的压力场景
"""

import pytest
import time
import multiprocessing as mp
import threading
import gc
import psutil
import os
import signal
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import weakref


@dataclass
class LifecycleStressConfig:
    """生命周期压力测试配置"""
    concurrent_creators: int = 8
    concurrent_destructors: int = 8
    queues_per_creator: int = 50
    creation_burst_size: int = 10
    destruction_delay: float = 0.1
    memory_check_interval: float = 1.0
    max_memory_growth_mb: float = 50.0
    test_duration: int = 60


class QueueLifecycleMonitor:
    """队列生命周期监控器"""
    
    def __init__(self):
        self.created_queues = mp.Manager().dict()
        self.destroyed_queues = mp.Manager().dict()
        self.active_queues = mp.Manager().dict()
        self.memory_samples = mp.Manager().list()
        self.error_log = mp.Manager().list()
        self.stop_monitoring = mp.Event()
    
    def record_creation(self, queue_id: str, worker_id: str, timestamp: float):
        """记录队列创建"""
        self.created_queues[queue_id] = {
            'worker_id': worker_id,
            'created_at': timestamp,
            'process_id': os.getpid()
        }
        self.active_queues[queue_id] = True
    
    def record_destruction(self, queue_id: str, worker_id: str, timestamp: float):
        """记录队列销毁"""
        self.destroyed_queues[queue_id] = {
            'worker_id': worker_id,
            'destroyed_at': timestamp,
            'process_id': os.getpid()
        }
        if queue_id in self.active_queues:
            del self.active_queues[queue_id]
    
    def record_error(self, error_type: str, error_msg: str, worker_id: str):
        """记录错误"""
        self.error_log.append({
            'error_type': error_type,
            'error_msg': error_msg,
            'worker_id': worker_id,
            'timestamp': time.time(),
            'process_id': os.getpid()
        })
    
    def start_memory_monitoring(self):
        """启动内存监控"""
        def memory_monitor():
            process = psutil.Process()
            while not self.stop_monitoring.is_set():
                try:
                    memory_info = process.memory_info()
                    self.memory_samples.append({
                        'timestamp': time.time(),
                        'rss_mb': memory_info.rss / 1024 / 1024,
                        'vms_mb': memory_info.vms / 1024 / 1024,
                        'active_queues': len(self.active_queues),
                        'total_created': len(self.created_queues),
                        'total_destroyed': len(self.destroyed_queues)
                    })
                    time.sleep(1.0)
                except Exception as e:
                    self.record_error('memory_monitor', str(e), 'monitor')
                    break
        
        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()
        return monitor_thread
    
    def stop_memory_monitoring(self):
        """停止内存监控"""
        self.stop_monitoring.set()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_created': len(self.created_queues),
            'total_destroyed': len(self.destroyed_queues),
            'active_queues': len(self.active_queues),
            'total_errors': len(self.error_log),
            'memory_samples': len(self.memory_samples)
        }


def lifecycle_creator_worker(worker_id: int, config: LifecycleStressConfig, 
                            monitor: QueueLifecycleMonitor) -> Dict[str, Any]:
    """生命周期创建者工作进程"""
    try:
        # 尝试导入真实的 SageQueue
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            use_real_queue = True
        except ImportError:
            from ...mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'created_count': 0,
            'creation_errors': 0,
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock',
            'process_id': os.getpid()
        }
        
        created_queues = []  # 本地跟踪创建的队列
        
        # 分批创建队列
        for batch in range(config.queues_per_creator // config.creation_burst_size):
            batch_start = time.time()
            
            # 批量创建
            for i in range(config.creation_burst_size):
                queue_id = f"lifecycle_{worker_id}_{batch}_{i}_{int(time.time()*1000000)}"
                
                try:
                    # 创建队列
                    queue = SageQueue(queue_id, maxsize=1000, auto_cleanup=True)
                    created_queues.append((queue_id, queue))
                    
                    # 记录创建
                    monitor.record_creation(queue_id, f"creator_{worker_id}", time.time())
                    stats['created_count'] += 1
                    
                    # 执行基本操作验证队列可用性
                    queue.put(f"test_message_{i}")
                    received = queue.get()
                    
                    if received != f"test_message_{i}":
                        monitor.record_error('operation_mismatch', 
                                           f"Expected test_message_{i}, got {received}", 
                                           f"creator_{worker_id}")
                
                except Exception as e:
                    stats['creation_errors'] += 1
                    monitor.record_error('creation_failed', str(e), f"creator_{worker_id}")
            
            batch_duration = time.time() - batch_start
            
            # 控制创建速率，避免过快创建导致资源耗尽
            if batch_duration < 0.1:
                time.sleep(0.1 - batch_duration)
        
        # 保持队列活跃一段时间
        active_time = min(config.test_duration * 0.3, 10)  # 最多10秒
        time.sleep(active_time)
        
        # 清理部分队列（模拟正常使用中的清理）
        cleanup_count = len(created_queues) // 2
        for i in range(cleanup_count):
            queue_id, queue = created_queues[i]
            try:
                queue.close()
                monitor.record_destruction(queue_id, f"creator_{worker_id}", time.time())
            except Exception as e:
                monitor.record_error('cleanup_failed', str(e), f"creator_{worker_id}")
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        return stats
    
    except Exception as e:
        return {
            'worker_id': worker_id,
            'created_count': 0,
            'creation_errors': 1,
            'fatal_error': str(e),
            'process_id': os.getpid()
        }


def lifecycle_destructor_worker(worker_id: int, config: LifecycleStressConfig,
                               monitor: QueueLifecycleMonitor, delay: float = 5.0) -> Dict[str, Any]:
    """生命周期销毁者工作进程"""
    try:
        # 尝试导入真实的 SageQueue
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            use_real_queue = True
        except ImportError:
            from ...mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        
        stats = {
            'worker_id': worker_id,
            'destroyed_count': 0,
            'destruction_errors': 0,
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock',
            'process_id': os.getpid()
        }
        
        # 等待一些队列被创建
        time.sleep(delay)
        
        # 持续监控并销毁活跃队列
        destruction_start = time.time()
        while time.time() - destruction_start < config.test_duration * 0.5:
            # 获取当前活跃队列列表
            active_queue_ids = list(monitor.active_queues.keys())
            
            if not active_queue_ids:
                time.sleep(1.0)
                continue
            
            # 随机选择一些队列进行销毁
            import random
            target_count = min(len(active_queue_ids) // 4, 5)  # 每次销毁25%或最多5个
            targets = random.sample(active_queue_ids, target_count)
            
            for queue_id in targets:
                try:
                    # 尝试连接并销毁队列
                    queue = SageQueue(queue_id)
                    queue.destroy()
                    
                    monitor.record_destruction(queue_id, f"destructor_{worker_id}", time.time())
                    stats['destroyed_count'] += 1
                    
                except Exception as e:
                    stats['destruction_errors'] += 1
                    monitor.record_error('destruction_failed', str(e), f"destructor_{worker_id}")
            
            time.sleep(config.destruction_delay)
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        return stats
    
    except Exception as e:
        return {
            'worker_id': worker_id,
            'destroyed_count': 0,
            'destruction_errors': 1,
            'fatal_error': str(e),
            'process_id': os.getpid()
        }


def resource_leak_detector_worker(config: LifecycleStressConfig,
                                 monitor: QueueLifecycleMonitor) -> Dict[str, Any]:
    """资源泄漏检测工作进程"""
    try:
        # 尝试导入真实的 SageQueue
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            use_real_queue = True
        except ImportError:
            from ...mock_sage_queue import MockSageQueue as SageQueue
            use_real_queue = False
        
        stats = {
            'leak_detections': 0,
            'resource_warnings': 0,
            'start_time': time.time(),
            'queue_type': 'real' if use_real_queue else 'mock'
        }
        
        # 创建短生命周期队列来检测泄漏
        leak_test_cycles = config.test_duration // 2  # 每2秒一个周期
        
        for cycle in range(leak_test_cycles):
            cycle_start = time.time()
            temp_queues = []
            
            try:
                # 创建临时队列
                for i in range(5):
                    queue_id = f"leak_test_{cycle}_{i}_{int(time.time()*1000000)}"
                    queue = SageQueue(queue_id, maxsize=100)
                    temp_queues.append(queue)
                    
                    # 执行一些操作
                    queue.put(f"leak_test_data_{i}")
                    queue.get()
                
                # 立即销毁
                for queue in temp_queues:
                    queue.destroy()
                
                # 强制垃圾回收
                gc.collect()
                
                # 检查内存增长
                if len(monitor.memory_samples) > 0:
                    recent_memory = monitor.memory_samples[-1]['rss_mb']
                    if cycle > 0 and len(monitor.memory_samples) > 10:
                        baseline_memory = monitor.memory_samples[max(0, len(monitor.memory_samples)-10)]['rss_mb']
                        memory_growth = recent_memory - baseline_memory
                        
                        if memory_growth > config.max_memory_growth_mb:
                            stats['leak_detections'] += 1
                            monitor.record_error('potential_leak', 
                                               f"Memory growth: {memory_growth:.2f} MB in 10 samples",
                                               'leak_detector')
                
            except Exception as e:
                stats['resource_warnings'] += 1
                monitor.record_error('leak_test_failed', str(e), 'leak_detector')
            
            # 控制检测频率
            cycle_duration = time.time() - cycle_start
            if cycle_duration < 2.0:
                time.sleep(2.0 - cycle_duration)
        
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        return stats
    
    except Exception as e:
        return {
            'leak_detections': 0,
            'resource_warnings': 1,
            'fatal_error': str(e)
        }


@pytest.mark.stress
@pytest.mark.lifecycle
class TestLifecycleStress:
    """生命周期管控压力测试类"""
    
    def test_concurrent_creation_destruction(self):
        """测试并发创建和销毁压力"""
        config = LifecycleStressConfig(
            concurrent_creators=6,
            concurrent_destructors=4,
            queues_per_creator=30,
            creation_burst_size=5,
            test_duration=45
        )
        
        monitor = QueueLifecycleMonitor()
        memory_monitor_thread = monitor.start_memory_monitoring()
        
        try:
            with ProcessPoolExecutor(max_workers=config.concurrent_creators + config.concurrent_destructors) as executor:
                futures = []
                
                # 启动创建者进程
                for i in range(config.concurrent_creators):
                    future = executor.submit(lifecycle_creator_worker, i, config, monitor)
                    futures.append(('creator', future))
                
                # 启动销毁者进程
                for i in range(config.concurrent_destructors):
                    future = executor.submit(lifecycle_destructor_worker, 
                                           i + config.concurrent_creators, config, monitor, 
                                           delay=5.0 + i * 2.0)  # 错开启动时间
                    futures.append(('destructor', future))
                
                # 收集结果
                creator_stats = []
                destructor_stats = []
                
                for worker_type, future in futures:
                    try:
                        result = future.result(timeout=config.test_duration + 10)
                        if worker_type == 'creator':
                            creator_stats.append(result)
                        else:
                            destructor_stats.append(result)
                    except Exception as e:
                        print(f"Lifecycle {worker_type} process failed: {e}")
        
        finally:
            monitor.stop_memory_monitoring()
        
        # 分析结果
        self._analyze_lifecycle_stress_results(creator_stats, destructor_stats, monitor)

    def test_resource_leak_detection(self):
        """测试资源泄漏检测"""
        config = LifecycleStressConfig(
            concurrent_creators=4,
            queues_per_creator=20,
            creation_burst_size=5,
            test_duration=30,
            max_memory_growth_mb=30.0
        )
        
        monitor = QueueLifecycleMonitor()
        memory_monitor_thread = monitor.start_memory_monitoring()
        
        try:
            with ProcessPoolExecutor(max_workers=config.concurrent_creators + 2) as executor:
                futures = []
                
                # 启动创建者进程
                for i in range(config.concurrent_creators):
                    future = executor.submit(lifecycle_creator_worker, i, config, monitor)
                    futures.append(('creator', future))
                
                # 启动泄漏检测进程
                future = executor.submit(resource_leak_detector_worker, config, monitor)
                futures.append(('leak_detector', future))
                
                # 启动一个销毁者进程
                future = executor.submit(lifecycle_destructor_worker, 
                                       config.concurrent_creators, config, monitor, delay=10.0)
                futures.append(('destructor', future))
                
                # 收集结果
                all_stats = []
                for worker_type, future in futures:
                    try:
                        result = future.result(timeout=config.test_duration + 10)
                        result['worker_type'] = worker_type
                        all_stats.append(result)
                    except Exception as e:
                        print(f"Resource leak test {worker_type} process failed: {e}")
        
        finally:
            monitor.stop_memory_monitoring()
        
        # 分析泄漏检测结果
        self._analyze_leak_detection_results(all_stats, monitor, config)

    def test_rapid_lifecycle_cycles(self):
        """测试快速生命周期循环"""
        config = LifecycleStressConfig(
            concurrent_creators=8,
            queues_per_creator=100,
            creation_burst_size=20,
            destruction_delay=0.01,  # 非常快的销毁
            test_duration=40
        )
        
        monitor = QueueLifecycleMonitor()
        memory_monitor_thread = monitor.start_memory_monitoring()
        
        def rapid_cycle_worker(worker_id: int) -> Dict[str, Any]:
            """快速循环工作进程"""
            try:
                # 尝试导入真实的 SageQueue
                try:
                    from sage.extensions.sage_queue.python.sage_queue import SageQueue
                    use_real_queue = True
                except ImportError:
                    from ...mock_sage_queue import MockSageQueue as SageQueue
                    use_real_queue = False
                
                stats = {
                    'worker_id': worker_id,
                    'rapid_cycles': 0,
                    'cycle_errors': 0,
                    'start_time': time.time(),
                    'queue_type': 'real' if use_real_queue else 'mock'
                }
                
                cycle_count = 0
                while time.time() - stats['start_time'] < config.test_duration:
                    queue_id = f"rapid_{worker_id}_{cycle_count}_{int(time.time()*1000000)}"
                    
                    try:
                        # 快速创建-使用-销毁循环
                        queue = SageQueue(queue_id, maxsize=10)
                        monitor.record_creation(queue_id, f"rapid_{worker_id}", time.time())
                        
                        # 简单操作
                        queue.put("rapid_test")
                        queue.get()
                        
                        # 立即销毁
                        queue.destroy()
                        monitor.record_destruction(queue_id, f"rapid_{worker_id}", time.time())
                        
                        stats['rapid_cycles'] += 1
                        cycle_count += 1
                        
                        # 非常短的间隔
                        time.sleep(0.001)
                        
                    except Exception as e:
                        stats['cycle_errors'] += 1
                        monitor.record_error('rapid_cycle_failed', str(e), f"rapid_{worker_id}")
                
                stats['end_time'] = time.time()
                stats['duration'] = stats['end_time'] - stats['start_time']
                return stats
                
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'rapid_cycles': 0,
                    'cycle_errors': 1,
                    'fatal_error': str(e)
                }
        
        try:
            with ProcessPoolExecutor(max_workers=config.concurrent_creators) as executor:
                futures = []
                
                for i in range(config.concurrent_creators):
                    future = executor.submit(rapid_cycle_worker, i)
                    futures.append(future)
                
                # 收集结果
                rapid_stats = []
                for future in futures:
                    try:
                        result = future.result(timeout=config.test_duration + 10)
                        rapid_stats.append(result)
                    except Exception as e:
                        print(f"Rapid cycle process failed: {e}")
        
        finally:
            monitor.stop_memory_monitoring()
        
        # 分析快速循环结果
        self._analyze_rapid_cycle_results(rapid_stats, monitor)

    def test_memory_pressure_lifecycle(self):
        """测试内存压力下的生命周期管控"""
        config = LifecycleStressConfig(
            concurrent_creators=4,
            queues_per_creator=50,
            creation_burst_size=10,
            test_duration=50,
            max_memory_growth_mb=80.0
        )
        
        monitor = QueueLifecycleMonitor()
        memory_monitor_thread = monitor.start_memory_monitoring()
        
        def memory_pressure_worker(worker_id: int) -> Dict[str, Any]:
            """内存压力工作进程"""
            try:
                # 尝试导入真实的 SageQueue
                try:
                    from sage.extensions.sage_queue.python.sage_queue import SageQueue
                    use_real_queue = True
                except ImportError:
                    from ...mock_sage_queue import MockSageQueue as SageQueue
                    use_real_queue = False
                
                stats = {
                    'worker_id': worker_id,
                    'pressure_cycles': 0,
                    'memory_errors': 0,
                    'start_time': time.time(),
                    'queue_type': 'real' if use_real_queue else 'mock'
                }
                
                active_queues = []
                large_data = "X" * (10 * 1024)  # 10KB data per message
                
                while time.time() - stats['start_time'] < config.test_duration:
                    try:
                        # 创建队列并填充大量数据
                        queue_id = f"pressure_{worker_id}_{stats['pressure_cycles']}"
                        queue = SageQueue(queue_id, maxsize=100)
                        
                        # 填充大量数据
                        for i in range(50):
                            queue.put(f"{large_data}_{i}")
                        
                        active_queues.append((queue_id, queue))
                        monitor.record_creation(queue_id, f"pressure_{worker_id}", time.time())
                        
                        # 当队列数量达到一定值时，清理一些旧队列
                        if len(active_queues) > 10:
                            old_queue_id, old_queue = active_queues.pop(0)
                            try:
                                # 清空队列
                                while not old_queue.empty():
                                    old_queue.get_nowait()
                                old_queue.destroy()
                                monitor.record_destruction(old_queue_id, f"pressure_{worker_id}", time.time())
                            except:
                                pass
                        
                        stats['pressure_cycles'] += 1
                        time.sleep(0.1)
                        
                    except Exception as e:
                        stats['memory_errors'] += 1
                        monitor.record_error('memory_pressure_failed', str(e), f"pressure_{worker_id}")
                
                # 清理剩余队列
                for queue_id, queue in active_queues:
                    try:
                        queue.destroy()
                        monitor.record_destruction(queue_id, f"pressure_{worker_id}", time.time())
                    except:
                        pass
                
                stats['end_time'] = time.time()
                stats['duration'] = stats['end_time'] - stats['start_time']
                return stats
                
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'pressure_cycles': 0,
                    'memory_errors': 1,
                    'fatal_error': str(e)
                }
        
        try:
            with ProcessPoolExecutor(max_workers=config.concurrent_creators) as executor:
                futures = []
                
                for i in range(config.concurrent_creators):
                    future = executor.submit(memory_pressure_worker, i)
                    futures.append(future)
                
                # 收集结果
                pressure_stats = []
                for future in futures:
                    try:
                        result = future.result(timeout=config.test_duration + 15)
                        pressure_stats.append(result)
                    except Exception as e:
                        print(f"Memory pressure process failed: {e}")
        
        finally:
            monitor.stop_memory_monitoring()
        
        # 分析内存压力结果
        self._analyze_memory_pressure_lifecycle_results(pressure_stats, monitor, config)

    def _analyze_lifecycle_stress_results(self, creator_stats: List[Dict], 
                                        destructor_stats: List[Dict], 
                                        monitor: QueueLifecycleMonitor):
        """分析生命周期压力测试结果"""
        print("\n=== 并发创建销毁压力测试结果 ===")
        
        # 创建者统计
        total_created = sum(stat['created_count'] for stat in creator_stats)
        creation_errors = sum(stat['creation_errors'] for stat in creator_stats)
        
        print(f"创建者统计:")
        print(f"  - 总创建: {total_created}")
        print(f"  - 创建错误: {creation_errors}")
        print(f"  - 成功率: {(total_created/(total_created+creation_errors))*100:.1f}%")
        
        # 销毁者统计
        total_destroyed = sum(stat['destroyed_count'] for stat in destructor_stats)
        destruction_errors = sum(stat['destruction_errors'] for stat in destructor_stats)
        
        print(f"销毁者统计:")
        print(f"  - 总销毁: {total_destroyed}")
        print(f"  - 销毁错误: {destruction_errors}")
        print(f"  - 成功率: {(total_destroyed/(total_destroyed+destruction_errors))*100:.1f}%")
        
        # 监控统计
        monitor_stats = monitor.get_statistics()
        print(f"监控统计:")
        print(f"  - 记录创建: {monitor_stats['total_created']}")
        print(f"  - 记录销毁: {monitor_stats['total_destroyed']}")
        print(f"  - 仍活跃: {monitor_stats['active_queues']}")
        print(f"  - 总错误: {monitor_stats['total_errors']}")
        
        # 内存分析
        if monitor_stats['memory_samples'] > 0:
            memory_samples = list(monitor.memory_samples)
            if memory_samples:
                initial_memory = memory_samples[0]['rss_mb']
                final_memory = memory_samples[-1]['rss_mb']
                peak_memory = max(sample['rss_mb'] for sample in memory_samples)
                
                print(f"内存使用:")
                print(f"  - 初始内存: {initial_memory:.2f} MB")
                print(f"  - 最终内存: {final_memory:.2f} MB")
                print(f"  - 峰值内存: {peak_memory:.2f} MB")
                print(f"  - 内存增长: {final_memory - initial_memory:+.2f} MB")
        
        # 断言验证
        assert total_created > 0, "没有队列被创建"
        assert creation_errors < total_created * 0.1, f"创建错误率过高: {creation_errors}/{total_created}"
        assert destruction_errors < total_destroyed * 0.1, f"销毁错误率过高: {destruction_errors}/{total_destroyed}"

    def _analyze_leak_detection_results(self, all_stats: List[Dict], 
                                      monitor: QueueLifecycleMonitor, 
                                      config: LifecycleStressConfig):
        """分析泄漏检测结果"""
        print("\n=== 资源泄漏检测测试结果 ===")
        
        leak_detector_stats = [s for s in all_stats if s.get('worker_type') == 'leak_detector']
        if leak_detector_stats:
            leak_stats = leak_detector_stats[0]
            print(f"泄漏检测统计:")
            print(f"  - 检测到泄漏: {leak_stats.get('leak_detections', 0)}")
            print(f"  - 资源警告: {leak_stats.get('resource_warnings', 0)}")
        
        # 内存增长分析
        memory_samples = list(monitor.memory_samples)
        if len(memory_samples) > 10:
            # 分析内存趋势
            early_samples = memory_samples[:5]
            late_samples = memory_samples[-5:]
            
            early_avg = sum(s['rss_mb'] for s in early_samples) / len(early_samples)
            late_avg = sum(s['rss_mb'] for s in late_samples) / len(late_samples)
            memory_growth = late_avg - early_avg
            
            print(f"内存趋势分析:")
            print(f"  - 早期平均: {early_avg:.2f} MB")
            print(f"  - 后期平均: {late_avg:.2f} MB")
            print(f"  - 内存增长: {memory_growth:+.2f} MB")
            
            # 检查内存增长是否超过阈值
            assert abs(memory_growth) < config.max_memory_growth_mb, \
                f"内存增长超过阈值: {memory_growth:.2f} > {config.max_memory_growth_mb} MB"

    def _analyze_rapid_cycle_results(self, rapid_stats: List[Dict], monitor: QueueLifecycleMonitor):
        """分析快速循环结果"""
        print("\n=== 快速生命周期循环测试结果 ===")
        
        total_cycles = sum(stat['rapid_cycles'] for stat in rapid_stats)
        total_errors = sum(stat['cycle_errors'] for stat in rapid_stats)
        
        if rapid_stats:
            avg_duration = sum(stat.get('duration', 0) for stat in rapid_stats) / len(rapid_stats)
            avg_cycle_rate = total_cycles / avg_duration if avg_duration > 0 else 0
        else:
            avg_cycle_rate = 0
        
        print(f"快速循环统计:")
        print(f"  - 总循环数: {total_cycles}")
        print(f"  - 循环错误: {total_errors}")
        print(f"  - 平均循环率: {avg_cycle_rate:.1f} cycles/sec")
        print(f"  - 错误率: {(total_errors/(total_cycles+total_errors))*100:.2f}%")
        
        # 断言验证
        assert total_cycles > 0, "没有完成任何快速循环"
        assert total_errors < total_cycles * 0.05, f"快速循环错误率过高: {total_errors}/{total_cycles}"

    def _analyze_memory_pressure_lifecycle_results(self, pressure_stats: List[Dict], 
                                                  monitor: QueueLifecycleMonitor,
                                                  config: LifecycleStressConfig):
        """分析内存压力生命周期结果"""
        print("\n=== 内存压力生命周期测试结果 ===")
        
        total_cycles = sum(stat['pressure_cycles'] for stat in pressure_stats)
        total_errors = sum(stat['memory_errors'] for stat in pressure_stats)
        
        print(f"内存压力统计:")
        print(f"  - 压力循环: {total_cycles}")
        print(f"  - 内存错误: {total_errors}")
        
        # 内存使用分析
        memory_samples = list(monitor.memory_samples)
        if memory_samples:
            peak_memory = max(sample['rss_mb'] for sample in memory_samples)
            final_memory = memory_samples[-1]['rss_mb']
            initial_memory = memory_samples[0]['rss_mb']
            
            print(f"内存使用分析:")
            print(f"  - 峰值内存: {peak_memory:.2f} MB")
            print(f"  - 内存增长: {final_memory - initial_memory:+.2f} MB")
            
            # 检查内存使用是否合理
            assert final_memory - initial_memory < config.max_memory_growth_mb, \
                f"内存增长超过限制: {final_memory - initial_memory:.2f} > {config.max_memory_growth_mb} MB"
        
        # 断言验证
        assert total_cycles > 0, "没有完成任何内存压力循环"
        assert total_errors < total_cycles * 0.1, f"内存压力错误率过高: {total_errors}/{total_cycles}"


if __name__ == "__main__":
    # 运行生命周期压力测试
    pytest.main([__file__, "-v", "--tb=short"])
