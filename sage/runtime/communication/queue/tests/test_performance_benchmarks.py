#!/usr/bin/env python3
"""
队列描述符性能基准测试

测试不同队列类型在各种场景下的性能：
1. 单线程吞吐量测试
2. 多线程并发性能测试
3. 多进程并发性能测试（支持的队列类型）
4. 内存使用情况测试
5. 延迟测试
"""

import sys
import os
import time
import threading
import multiprocessing
import psutil
import statistics
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
import gc

# 添加项目路径
sys.path.insert(0, '/api-rework')

try:
    from sage.runtime.communication.queue import (
        PythonQueueDescriptor,
        RayQueueDescriptor,  
        SageQueueDescriptor
    )
    print("✓ 成功导入队列描述符")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.results = {}
        self.process = psutil.Process()
    
    def measure_memory_usage(self) -> Dict[str, float]:
        """测量内存使用情况"""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # 物理内存
            'vms_mb': memory_info.vms / 1024 / 1024,  # 虚拟内存
            'percent': self.process.memory_percent()   # 内存使用百分比
        }
    
    def single_thread_throughput_test(self, queue_desc, num_items: int = 10000) -> Dict[str, Any]:
        """单线程吞吐量测试"""
        print(f"\n--- 单线程吞吐量测试 ({queue_desc.queue_type}) ---")
        
        # 内存基线
        gc.collect()
        memory_before = self.measure_memory_usage()
        
        # 写入测试
        start_time = time.time()
        for i in range(num_items):
            queue_desc.put(f"item_{i}")
        write_end_time = time.time()
        
        write_duration = write_end_time - start_time
        write_throughput = num_items / write_duration
        
        # 读取测试
        read_start_time = time.time()
        items = []
        for i in range(num_items):
            items.append(queue_desc.get())
        read_end_time = time.time()
        
        read_duration = read_end_time - read_start_time
        read_throughput = num_items / read_duration
        
        # 内存测量
        memory_after = self.measure_memory_usage()
        memory_delta = memory_after['rss_mb'] - memory_before['rss_mb']
        
        result = {
            'queue_type': queue_desc.queue_type,
            'num_items': num_items,
            'write_duration': write_duration,
            'read_duration': read_duration,
            'write_throughput': write_throughput,
            'read_throughput': read_throughput,
            'total_duration': write_duration + read_duration,
            'memory_delta_mb': memory_delta,
            'memory_before': memory_before,
            'memory_after': memory_after
        }
        
        print(f"写入: {write_throughput:.0f} items/sec, 读取: {read_throughput:.0f} items/sec")
        print(f"内存变化: {memory_delta:.2f} MB")
        
        return result
    
    def multi_thread_throughput_test(self, queue_desc, num_threads: int = 4, 
                                   items_per_thread: int = 2500) -> Dict[str, Any]:
        """多线程吞吐量测试"""
        print(f"\n--- 多线程吞吐量测试 ({queue_desc.queue_type}) ---")
        print(f"配置: {num_threads}个线程, 每个处理{items_per_thread}个项目")
        
        gc.collect()
        memory_before = self.measure_memory_usage()
        
        # 生产者线程函数
        def producer_worker(thread_id: int, items: int):
            start_time = time.time()
            for i in range(items):
                queue_desc.put(f"thread_{thread_id}_item_{i}")
            end_time = time.time()
            return {
                'thread_id': thread_id,
                'duration': end_time - start_time,
                'throughput': items / (end_time - start_time)
            }
        
        # 消费者线程函数
        def consumer_worker(thread_id: int, items: int):
            start_time = time.time()
            consumed = []
            for i in range(items):
                try:
                    item = queue_desc.get(timeout=5.0)
                    consumed.append(item)
                except:
                    break
            end_time = time.time()
            return {
                'thread_id': thread_id,
                'duration': end_time - start_time,
                'consumed': len(consumed),
                'throughput': len(consumed) / (end_time - start_time) if end_time > start_time else 0
            }
        
        # 运行生产者线程
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            producer_futures = []
            for i in range(num_threads):
                future = executor.submit(producer_worker, i, items_per_thread)
                producer_futures.append(future)
            
            producer_results = []
            for future in as_completed(producer_futures):
                result = future.result()
                producer_results.append(result)
        
        producer_end_time = time.time()
        
        # 运行消费者线程
        consumer_start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            consumer_futures = []
            for i in range(num_threads):
                future = executor.submit(consumer_worker, i, items_per_thread)
                consumer_futures.append(future)
            
            consumer_results = []
            for future in as_completed(consumer_futures):
                result = future.result()
                consumer_results.append(result)
        
        consumer_end_time = time.time()
        
        memory_after = self.measure_memory_usage()
        
        # 计算统计数据
        total_items = num_threads * items_per_thread
        producer_throughputs = [r['throughput'] for r in producer_results]
        consumer_throughputs = [r['throughput'] for r in consumer_results]
        total_consumed = sum(r['consumed'] for r in consumer_results)
        
        result = {
            'queue_type': queue_desc.queue_type,
            'num_threads': num_threads,
            'items_per_thread': items_per_thread,
            'total_items': total_items,
            'producer_duration': producer_end_time - start_time,
            'consumer_duration': consumer_end_time - consumer_start_time,
            'total_consumed': total_consumed,
            'avg_producer_throughput': statistics.mean(producer_throughputs),
            'max_producer_throughput': max(producer_throughputs),
            'avg_consumer_throughput': statistics.mean(consumer_throughputs),
            'max_consumer_throughput': max(consumer_throughputs),
            'memory_delta_mb': memory_after['rss_mb'] - memory_before['rss_mb'],
            'producer_results': producer_results,
            'consumer_results': consumer_results
        }
        
        print(f"生产者平均吞吐量: {result['avg_producer_throughput']:.0f} items/sec")
        print(f"消费者平均吞吐量: {result['avg_consumer_throughput']:.0f} items/sec")
        print(f"总消费项目: {total_consumed}/{total_items}")
        
        return result
    
    def latency_test(self, queue_desc, num_samples: int = 1000) -> Dict[str, Any]:
        """延迟测试"""
        print(f"\n--- 延迟测试 ({queue_desc.queue_type}) ---")
        
        latencies = []
        
        for i in range(num_samples):
            # 测量单次put-get循环的延迟
            start_time = time.perf_counter()
            queue_desc.put(f"latency_test_{i}")
            item = queue_desc.get()
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        result = {
            'queue_type': queue_desc.queue_type,
            'num_samples': num_samples,
            'avg_latency_ms': statistics.mean(latencies),
            'median_latency_ms': statistics.median(latencies),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18],  # 95th percentile
            'p99_latency_ms': statistics.quantiles(latencies, n=100)[98],  # 99th percentile
            'stddev_latency_ms': statistics.stdev(latencies)
        }
        
        print(f"平均延迟: {result['avg_latency_ms']:.3f}ms")
        print(f"中位延迟: {result['median_latency_ms']:.3f}ms")
        print(f"P95延迟: {result['p95_latency_ms']:.3f}ms")
        print(f"P99延迟: {result['p99_latency_ms']:.3f}ms")
        
        return result
    
    def queue_size_performance_test(self, queue_desc, max_size: int = 100000, 
                                   step_size: int = 10000) -> Dict[str, Any]:
        """队列大小对性能的影响测试"""
        print(f"\n--- 队列大小性能测试 ({queue_desc.queue_type}) ---")
        
        size_results = []
        
        for current_size in range(step_size, max_size + 1, step_size):
            print(f"测试队列大小: {current_size}")
            
            # 填充队列到指定大小
            start_fill_time = time.time()
            for i in range(current_size):
                queue_desc.put(f"size_test_{i}")
            fill_duration = time.time() - start_fill_time
            
            # 测量读取性能
            start_read_time = time.time()
            for i in range(min(1000, current_size)):  # 读取最多1000个项目
                queue_desc.get()
            read_duration = time.time() - start_read_time
            
            # 清空剩余项目
            while not queue_desc.empty():
                try:
                    queue_desc.get_nowait()
                except:
                    break
            
            memory_usage = self.measure_memory_usage()
            
            size_results.append({
                'queue_size': current_size,
                'fill_duration': fill_duration,
                'fill_throughput': current_size / fill_duration,
                'read_duration': read_duration,
                'read_throughput': min(1000, current_size) / read_duration,
                'memory_mb': memory_usage['rss_mb']
            })
        
        result = {
            'queue_type': queue_desc.queue_type,
            'max_size': max_size,
            'step_size': step_size,
            'size_results': size_results
        }
        
        return result
    
    def run_all_benchmarks(self):
        """运行所有基准测试"""
        print("🚀 开始运行队列性能基准测试")
        
        # 测试队列类型配置
        queue_configs = [
            {
                'name': 'Python线程队列',
                'creator': lambda: PythonQueueDescriptor("perf_python_thread", maxsize=50000, use_multiprocessing=False)
            },
            {
                'name': 'Python多进程队列',
                'creator': lambda: PythonQueueDescriptor("perf_python_mp", maxsize=50000, use_multiprocessing=True)
            }
        ]
        
        # 添加可选队列类型
        try:
            import ray
            queue_configs.append({
                'name': 'Ray队列',
                'creator': lambda: RayQueueDescriptor(queue_id="perf_ray", maxsize=50000)
            })
        except ImportError:
            print("⚠️ Ray不可用，跳过Ray队列测试")
        
        try:
            queue_configs.append({
                'name': 'SAGE队列',
                'creator': lambda: SageQueueDescriptor(queue_id="perf_sage", maxsize=50*1024*1024)
            })
        except Exception:
            print("⚠️ SAGE队列不可用，跳过SAGE队列测试")
        
        # 运行所有测试
        for config in queue_configs:
            queue_name = config['name']
            print(f"\n{'='*60}")
            print(f"测试队列类型: {queue_name}")
            print(f"{'='*60}")
            
            try:
                queue_desc = config['creator']()
                
                # 运行各种基准测试
                self.results[queue_name] = {
                    'single_thread': self.single_thread_throughput_test(queue_desc, 5000),
                    'multi_thread': self.multi_thread_throughput_test(queue_desc, 4, 1250),
                    'latency': self.latency_test(queue_desc, 500),
                    'queue_size': self.queue_size_performance_test(queue_desc, 50000, 10000)
                }
                
                print(f"✅ {queue_name} 基准测试完成")
                
            except Exception as e:
                print(f"❌ {queue_name} 基准测试失败: {e}")
                import traceback
                traceback.print_exc()
    
    def generate_benchmark_report(self):
        """生成基准测试报告"""
        print(f"\n{'='*60}")
        print("基准测试结果报告")
        print(f"{'='*60}")
        
        if not self.results:
            print("❌ 没有测试结果")
            return
        
        # 生成汇总表
        print("\n📊 性能汇总表:")
        print(f"{'队列类型':<15} {'单线程写入':<12} {'单线程读取':<12} {'多线程写入':<12} {'多线程读取':<12} {'平均延迟':<10}")
        print("-" * 80)
        
        for queue_name, results in self.results.items():
            single_thread = results.get('single_thread', {})
            multi_thread = results.get('multi_thread', {})
            latency = results.get('latency', {})
            
            write_throughput = f"{single_thread.get('write_throughput', 0):.0f}"
            read_throughput = f"{single_thread.get('read_throughput', 0):.0f}"
            mt_write_throughput = f"{multi_thread.get('avg_producer_throughput', 0):.0f}"
            mt_read_throughput = f"{multi_thread.get('avg_consumer_throughput', 0):.0f}"
            avg_latency = f"{latency.get('avg_latency_ms', 0):.2f}ms"
            
            print(f"{queue_name:<15} {write_throughput:<12} {read_throughput:<12} {mt_write_throughput:<12} {mt_read_throughput:<12} {avg_latency:<10}")
        
        # 详细报告
        print(f"\n📝 详细性能报告:")
        for queue_name, results in self.results.items():
            print(f"\n--- {queue_name} ---")
            
            if 'single_thread' in results:
                st = results['single_thread']
                print(f"单线程: 写入 {st['write_throughput']:.0f} items/sec, 读取 {st['read_throughput']:.0f} items/sec")
                print(f"         内存使用 {st['memory_delta_mb']:.2f} MB")
            
            if 'multi_thread' in results:
                mt = results['multi_thread']
                print(f"多线程: 生产者平均 {mt['avg_producer_throughput']:.0f} items/sec")
                print(f"        消费者平均 {mt['avg_consumer_throughput']:.0f} items/sec")
                print(f"        消费成功率 {mt['total_consumed']/mt['total_items']*100:.1f}%")
            
            if 'latency' in results:
                lat = results['latency']
                print(f"延迟: 平均 {lat['avg_latency_ms']:.3f}ms, P95 {lat['p95_latency_ms']:.3f}ms, P99 {lat['p99_latency_ms']:.3f}ms")
        
        # 保存详细报告到文件
        self._save_detailed_report()
    
    def _save_detailed_report(self):
        """保存详细报告到文件"""
        import json
        from pathlib import Path
        
        report_file = Path("benchmark_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细基准测试报告已保存到: {report_file.absolute()}")


def run_performance_benchmarks():
    """运行性能基准测试"""
    benchmark = PerformanceBenchmark()
    
    try:
        benchmark.run_all_benchmarks()
        benchmark.generate_benchmark_report()
        return True
    except Exception as e:
        print(f"❌ 性能基准测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_performance_benchmarks()
    sys.exit(0 if success else 1)
