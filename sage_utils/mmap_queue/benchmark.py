#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue 基准测试
Benchmark test for SAGE high-performance memory-mapped queue
"""

import os
import sys
import time
import threading
import multiprocessing
import statistics
import json
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sage_queue import SageQueue, SageQueueRef, destroy_queue
    print("✓ 成功导入 SageQueue")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


class BenchmarkResult:
    """基准测试结果"""
    def __init__(self, name: str):
        self.name = name
        self.start_time = time.time()
        self.end_time = None
        self.metrics = {}
        self.success = False
    
    def finish(self, success: bool = True, **metrics):
        self.end_time = time.time()
        self.success = success
        self.metrics.update(metrics)
    
    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def to_dict(self):
        return {
            'name': self.name,
            'duration': self.duration,
            'success': self.success,
            'metrics': self.metrics
        }


def benchmark_throughput() -> BenchmarkResult:
    """吞吐量基准测试"""
    result = BenchmarkResult("吞吐量测试")
    
    try:
        queue_name = f"bench_throughput_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 测试不同消息大小的吞吐量
        message_sizes = [64, 256, 1024, 4096]  # bytes
        buffer_size = 1024 * 1024  # 1MB buffer
        
        throughput_results = {}
        
        for msg_size in message_sizes:
            print(f"  测试 {msg_size} 字节消息...")
            
            queue = SageQueue(queue_name + f"_{msg_size}", maxsize=buffer_size)
            
            # 生成测试数据
            test_data = 'x' * msg_size
            message = {"size": msg_size, "data": test_data}
            
            # 写入测试
            num_messages = min(10000, buffer_size // (msg_size + 100))  # 避免溢出
            
            write_start = time.time()
            written = 0
            
            for i in range(num_messages):
                try:
                    message["id"] = i
                    queue.put_nowait(message)
                    written += 1
                except:
                    break
            
            write_time = time.time() - write_start
            
            # 读取测试
            read_start = time.time()
            read = 0
            
            while read < written:
                try:
                    queue.get_nowait()
                    read += 1
                except:
                    break
            
            read_time = time.time() - read_start
            
            # 计算指标
            write_throughput = written / write_time if write_time > 0 else 0
            read_throughput = read / read_time if read_time > 0 else 0
            write_bandwidth = (written * msg_size) / (1024 * 1024) / write_time if write_time > 0 else 0
            read_bandwidth = (read * msg_size) / (1024 * 1024) / read_time if read_time > 0 else 0
            
            throughput_results[msg_size] = {
                'written': written,
                'read': read,
                'write_msg_per_sec': write_throughput,
                'read_msg_per_sec': read_throughput,
                'write_mb_per_sec': write_bandwidth,
                'read_mb_per_sec': read_bandwidth
            }
            
            print(f"    写入: {written} 消息, {write_throughput:.0f} msg/s, {write_bandwidth:.1f} MB/s")
            print(f"    读取: {read} 消息, {read_throughput:.0f} msg/s, {read_bandwidth:.1f} MB/s")
            
            queue.close()
            destroy_queue(queue_name + f"_{msg_size}")
        
        result.finish(True, throughput=throughput_results)
        
    except Exception as e:
        result.finish(False, error=str(e))
    
    return result


def benchmark_latency() -> BenchmarkResult:
    """延迟基准测试"""
    result = BenchmarkResult("延迟测试")
    
    try:
        queue_name = f"bench_latency_{int(time.time())}"
        destroy_queue(queue_name)
        
        queue = SageQueue(queue_name, maxsize=64*1024)
        
        # 测试单次操作延迟
        num_samples = 1000
        message = {"id": 0, "data": "latency_test_message"}
        
        write_latencies = []
        read_latencies = []
        roundtrip_latencies = []
        
        print(f"  采集 {num_samples} 个延迟样本...")
        
        for i in range(num_samples):
            message["id"] = i
            
            # 测试写入延迟
            start = time.time()
            queue.put(message)
            write_lat = time.time() - start
            write_latencies.append(write_lat * 1000)  # 转换为毫秒
            
            # 测试读取延迟
            start = time.time()
            queue.get()
            read_lat = time.time() - start
            read_latencies.append(read_lat * 1000)
            
            # 往返延迟
            roundtrip_latencies.append((write_lat + read_lat) * 1000)
        
        # 计算统计数据
        def calc_stats(data):
            return {
                'mean': statistics.mean(data),
                'median': statistics.median(data),
                'p95': sorted(data)[int(0.95 * len(data))],
                'p99': sorted(data)[int(0.99 * len(data))],
                'min': min(data),
                'max': max(data)
            }
        
        write_stats = calc_stats(write_latencies)
        read_stats = calc_stats(read_latencies)
        roundtrip_stats = calc_stats(roundtrip_latencies)
        
        print(f"  写入延迟 (ms): 平均={write_stats['mean']:.3f}, P95={write_stats['p95']:.3f}")
        print(f"  读取延迟 (ms): 平均={read_stats['mean']:.3f}, P95={read_stats['p95']:.3f}")
        print(f"  往返延迟 (ms): 平均={roundtrip_stats['mean']:.3f}, P95={roundtrip_stats['p99']:.3f}")
        
        queue.close()
        destroy_queue(queue_name)
        
        result.finish(True, 
                     write_latency=write_stats,
                     read_latency=read_stats, 
                     roundtrip_latency=roundtrip_stats)
        
    except Exception as e:
        result.finish(False, error=str(e))
    
    return result


def benchmark_concurrent_access() -> BenchmarkResult:
    """并发访问基准测试"""
    result = BenchmarkResult("并发访问测试")
    
    try:
        queue_name = f"bench_concurrent_{int(time.time())}"
        destroy_queue(queue_name)
        
        queue = SageQueue(queue_name, maxsize=256*1024)  # 256KB buffer
        
        # 测试不同线程数的并发性能
        thread_counts = [1, 2, 4, 8]
        messages_per_thread = 100
        
        concurrent_results = {}
        
        for num_threads in thread_counts:
            print(f"  测试 {num_threads} 线程并发...")
            
            results_data = {'completed_ops': 0, 'total_time': 0, 'errors': 0}
            results_lock = threading.Lock()
            
            def worker(thread_id: int):
                try:
                    start_time = time.time()
                    
                    # 每个线程执行put和get操作
                    for i in range(messages_per_thread):
                        message = {
                            'thread_id': thread_id,
                            'message_id': i,
                            'data': f'thread_{thread_id}_msg_{i}'
                        }
                        
                        # Put
                        queue.put(message, timeout=10.0)
                        
                        # Get
                        queue.get(timeout=10.0)
                    
                    end_time = time.time()
                    
                    with results_lock:
                        results_data['completed_ops'] += messages_per_thread * 2  # put + get
                        results_data['total_time'] = max(results_data['total_time'], end_time - start_time)
                        
                except Exception as e:
                    with results_lock:
                        results_data['errors'] += 1
            
            # 运行并发测试
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
            
            overall_start = time.time()
            
            for t in threads:
                t.start()
            
            for t in threads:
                t.join(timeout=30.0)
            
            overall_end = time.time()
            
            # 计算性能指标
            total_ops = results_data['completed_ops']
            wall_time = overall_end - overall_start
            ops_per_second = total_ops / wall_time if wall_time > 0 else 0
            
            concurrent_results[num_threads] = {
                'total_operations': total_ops,
                'wall_time': wall_time,
                'ops_per_second': ops_per_second,
                'errors': results_data['errors']
            }
            
            print(f"    操作数: {total_ops}, 用时: {wall_time:.3f}s, 性能: {ops_per_second:.0f} ops/s")
        
        queue.close()
        destroy_queue(queue_name)
        
        result.finish(True, concurrent_performance=concurrent_results)
        
    except Exception as e:
        result.finish(False, error=str(e))
    
    return result


def benchmark_memory_efficiency() -> BenchmarkResult:
    """内存效率基准测试"""
    result = BenchmarkResult("内存效率测试")
    
    try:
        queue_name = f"bench_memory_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 测试不同缓冲区大小的内存利用率
        buffer_sizes = [4096, 16384, 65536, 262144]  # 4KB to 256KB
        message_size = 128  # bytes per message
        
        memory_results = {}
        
        for buffer_size in buffer_sizes:
            print(f"  测试 {buffer_size} 字节缓冲区...")
            
            test_queue_name = f"{queue_name}_{buffer_size}"
            queue = SageQueue(test_queue_name, maxsize=buffer_size)
            
            test_message = {"data": "x" * message_size}
            
            # 填满缓冲区
            messages_written = 0
            while True:
                try:
                    test_message["id"] = messages_written
                    queue.put_nowait(test_message)
                    messages_written += 1
                    
                    if messages_written > buffer_size // 50:  # 安全限制
                        break
                        
                except:
                    break
            
            stats = queue.get_stats()
            
            # 计算效率指标
            theoretical_max = buffer_size // (message_size + 20)  # 估计开销
            utilization = stats['utilization']
            efficiency = messages_written / theoretical_max if theoretical_max > 0 else 0
            
            memory_results[buffer_size] = {
                'messages_stored': messages_written,
                'buffer_utilization': utilization,
                'storage_efficiency': efficiency,
                'bytes_per_message': buffer_size / messages_written if messages_written > 0 else 0
            }
            
            print(f"    存储消息: {messages_written}, 利用率: {utilization:.1%}, 效率: {efficiency:.1%}")
            
            queue.close()
            destroy_queue(test_queue_name)
        
        result.finish(True, memory_efficiency=memory_results)
        
    except Exception as e:
        result.finish(False, error=str(e))
    
    return result


def benchmark_multiprocess() -> BenchmarkResult:
    """多进程基准测试"""
    result = BenchmarkResult("多进程测试")
    
    def worker_process(queue_name: str, worker_id: int, num_operations: int) -> Dict[str, Any]:
        """工作进程函数"""
        try:
            queue = SageQueue(queue_name)
            
            start_time = time.time()
            completed = 0
            
            for i in range(num_operations):
                message = {
                    'worker_id': worker_id,
                    'operation_id': i,
                    'timestamp': time.time(),
                    'data': f'process_{worker_id}_op_{i}'
                }
                
                # Put message
                queue.put(message, timeout=15.0)
                
                # Get message (might not be our own)
                retrieved = queue.get(timeout=15.0)
                
                completed += 2  # put + get
            
            end_time = time.time()
            queue.close()
            
            return {
                'worker_id': worker_id,
                'completed': completed,
                'duration': end_time - start_time,
                'ops_per_sec': completed / (end_time - start_time) if end_time > start_time else 0
            }
            
        except Exception as e:
            return {
                'worker_id': worker_id,
                'error': str(e),
                'completed': completed if 'completed' in locals() else 0
            }
    
    try:
        queue_name = f"bench_multiproc_{int(time.time())}"
        destroy_queue(queue_name)
        
        # 创建主队列
        main_queue = SageQueue(queue_name, maxsize=512*1024)  # 512KB buffer
        main_queue.close()  # 关闭但不销毁
        
        num_processes = min(4, multiprocessing.cpu_count())
        operations_per_process = 50
        
        print(f"  启动 {num_processes} 个进程，每个执行 {operations_per_process} 次操作...")
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = []
            for worker_id in range(num_processes):
                future = executor.submit(worker_process, queue_name, worker_id, operations_per_process)
                futures.append(future)
            
            # 收集结果
            worker_results = []
            for future in futures:
                try:
                    worker_result = future.result(timeout=60)
                    worker_results.append(worker_result)
                except Exception as e:
                    worker_results.append({'error': str(e), 'completed': 0})
        
        # 分析结果
        successful_workers = [r for r in worker_results if 'error' not in r]
        total_completed = sum(r['completed'] for r in successful_workers)
        avg_ops_per_sec = statistics.mean([r['ops_per_sec'] for r in successful_workers]) if successful_workers else 0
        
        print(f"    成功进程: {len(successful_workers)}/{num_processes}")
        print(f"    总操作数: {total_completed}")
        print(f"    平均性能: {avg_ops_per_sec:.0f} ops/s per process")
        
        destroy_queue(queue_name)
        
        result.finish(True, 
                     processes=num_processes,
                     successful_processes=len(successful_workers),
                     total_operations=total_completed,
                     avg_ops_per_sec=avg_ops_per_sec,
                     worker_results=worker_results)
        
    except Exception as e:
        result.finish(False, error=str(e))
        try:
            destroy_queue(queue_name)
        except:
            pass
    
    return result


def run_benchmarks():
    """运行所有基准测试"""
    print("SAGE Memory-Mapped Queue 基准测试套件")
    print("=" * 60)
    
    benchmarks = [
        benchmark_throughput,
        benchmark_latency,
        benchmark_concurrent_access,
        benchmark_memory_efficiency,
        benchmark_multiprocess,
    ]
    
    results = []
    
    for benchmark_func in benchmarks:
        print(f"\n运行 {benchmark_func.__doc__ or benchmark_func.__name__}...")
        try:
            benchmark_result = benchmark_func()
            results.append(benchmark_result)
            
            if benchmark_result.success:
                print(f"✓ 完成 ({benchmark_result.duration:.1f}s)")
            else:
                print(f"✗ 失败: {benchmark_result.metrics.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"✗ 执行异常: {e}")
            failed_result = BenchmarkResult(benchmark_func.__name__)
            failed_result.finish(False, error=str(e))
            results.append(failed_result)
    
    # 生成报告
    print("\n" + "=" * 60)
    print("基准测试报告")
    print("-" * 60)
    
    successful = 0
    failed = 0
    
    for benchmark_result in results:
        if benchmark_result.success:
            print(f"✓ {benchmark_result.name}: {benchmark_result.duration:.1f}s")
            successful += 1
        else:
            print(f"✗ {benchmark_result.name}: 失败")
            failed += 1
    
    print(f"\n总计: {successful} 成功, {failed} 失败")
    
    # 保存详细结果到JSON
    report_data = {
        'timestamp': time.time(),
        'results': [r.to_dict() for r in results]
    }
    
    report_file = f"benchmark_report_{int(time.time())}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"详细报告已保存到: {report_file}")
    
    return successful == len(benchmarks)


if __name__ == "__main__":
    # 设置多进程启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
    
    success = run_benchmarks()
    sys.exit(0 if success else 1)
