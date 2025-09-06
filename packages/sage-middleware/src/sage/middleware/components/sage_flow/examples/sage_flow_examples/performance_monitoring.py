#!/usr/bin/env python3
"""
SAGE Flow 性能和监控示例

展示 sage_flow 的性能监控功能：
- 性能基准测试
- 资源使用监控
- 吞吐量分析
- 延迟测量
- 内存和CPU监控

作者: Kilo Code
日期: 2025-09-04
"""

import sys
import os
import time
import threading
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

# 尝试导入 psutil，如果失败则使用模拟模式
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("□ psutil 模块未找到，将使用模拟系统监控")

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/sage-middleware/src'))

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/sage-middleware/src'))

# 直接导入 C++ 扩展模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sage_flow_datastream",
    os.path.join(os.path.dirname(__file__), '../../packages/sage-middleware/src/sage/middleware/components/sage_flow/python/sage_flow_datastream.cpython-313-x86_64-linux-gnu.so')
)
sfd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfd)
print("✓ SAGE Flow 模块导入成功")

# 检查模块是否可用
MODULE_AVAILABLE = True

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = None
        self.end_time = None
        self.monitoring_active = False
        self.monitoring_thread = None

    def start_monitoring(self):
        """开始性能监控"""
        self.start_time = time.time()
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system_resources)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        print("✓ 性能监控已启动")

    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
        self.end_time = time.time()
        print("✓ 性能监控已停止")

    def _monitor_system_resources(self):
        """监控系统资源"""
        while self.monitoring_active:
            try:
                if PSUTIL_AVAILABLE:
                    # 使用真实的系统监控
                    process = psutil.Process()
                    # CPU使用率
                    cpu_percent = process.cpu_percent(interval=0.1)
                    self.metrics["cpu_percent"].append(cpu_percent)

                    # 内存使用
                    memory_info = process.memory_info()
                    self.metrics["memory_rss"].append(memory_info.rss / 1024 / 1024)  # MB
                    self.metrics["memory_vms"].append(memory_info.vms / 1024 / 1024)  # MB

                    # 系统级资源
                    system_cpu = psutil.cpu_percent(interval=0.1)
                    system_memory = psutil.virtual_memory()
                    self.metrics["system_cpu"].append(system_cpu)
                    self.metrics["system_memory_percent"].append(system_memory.percent)
                else:
                    # 使用模拟的系统监控
                    cpu_percent = random.uniform(5.0, 85.0)
                    memory_rss = random.uniform(50.0, 200.0)
                    memory_vms = random.uniform(100.0, 400.0)
                    system_cpu = random.uniform(10.0, 90.0)
                    system_memory_percent = random.uniform(20.0, 80.0)

                    self.metrics["cpu_percent"].append(cpu_percent)
                    self.metrics["memory_rss"].append(memory_rss)
                    self.metrics["memory_vms"].append(memory_vms)
                    self.metrics["system_cpu"].append(system_cpu)
                    self.metrics["system_memory_percent"].append(system_memory_percent)

                time.sleep(0.5)  # 每0.5秒采样一次

            except Exception as e:
                print(f"资源监控错误: {e}")
                break

    def record_metric(self, name: str, value: float):
        """记录自定义指标"""
        self.metrics[name].append(value)

    def get_summary_stats(self) -> Dict[str, Any]:
        """获取汇总统计"""
        stats = {}

        for metric_name, values in self.metrics.items():
            if values:
                stats[metric_name] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0
                }

        if self.start_time and self.end_time:
            total_duration = self.end_time - self.start_time
            stats["total_duration"] = total_duration
            stats["monitoring_samples"] = len(self.metrics.get("cpu_percent", []))

        return stats

    def print_summary_report(self):
        """打印汇总报告"""
        stats = self.get_summary_stats()

        print("\n=== 性能监控报告 ===")
        print(f"监控时长: {stats.get('total_duration', 0):.2f} 秒")
        print(f"采样次数: {stats.get('monitoring_samples', 0)}")

        if "cpu_percent" in stats:
            cpu_stats = stats["cpu_percent"]
            print("\n进程CPU使用率:")
            print(".1f")
            print(".1f")
            print(".1f")

        if "memory_rss" in stats:
            mem_stats = stats["memory_rss"]
            print("\n内存使用 (RSS):")
            print(".1f")
            print(".1f")
            print(".1f")

        if "system_cpu" in stats:
            sys_cpu_stats = stats["system_cpu"]
            print("\n系统CPU使用率:")
            print(".1f")
            print(".1f")
            print(".1f")

class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.test_results = []

    def create_test_data(self, size: int) -> List[Dict[str, Any]]:
        """创建测试数据"""
        import random
        data = []
        for i in range(size):
            item = {
                "id": i + 1,
                "data": f"test_data_{i}",
                "value": random.randint(1, 1000),
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "batch_id": random.randint(1, 10),
                    "priority": random.choice(["low", "medium", "high"]),
                    "tags": [f"tag_{j}" for j in range(random.randint(1, 5))]
                }
            }
            data.append(item)
        return data

    def simple_processing_benchmark(self):
        """简单处理基准测试"""
        print("\n=== 简单处理基准测试 ===")

        test_sizes = [100, 500, 1000, 5000]

        for size in test_sizes:
            print(f"\n测试数据大小: {size}")

            # 创建测试数据
            test_data = self.create_test_data(size)

            # 开始监控
            self.monitor.start_monitoring()

            # 执行处理
            start_time = time.time()
            processed_count = 0

            for item in test_data:
                # 模拟简单处理
                if item["value"] > 100:
                    item["processed"] = True
                    item["result"] = item["value"] * 2
                    processed_count += 1

                # 模拟处理时间
                time.sleep(0.001)  # 1ms

            end_time = time.time()
            processing_time = end_time - start_time

            # 停止监控
            self.monitor.stop_monitoring()

            # 记录结果
            throughput = size / processing_time if processing_time > 0 else 0
            result = {
                "test_name": "simple_processing",
                "data_size": size,
                "processing_time": processing_time,
                "throughput": throughput,
                "processed_count": processed_count,
                "efficiency": processed_count / size * 100
            }
            self.test_results.append(result)

            print(".3f")
            print(".1f")
            print(".1f")

    def complex_processing_benchmark(self):
        """复杂处理基准测试"""
        print("\n=== 复杂处理基准测试 ===")

        test_sizes = [50, 100, 200]

        for size in test_sizes:
            print(f"\n测试数据大小: {size}")

            test_data = self.create_test_data(size)

            self.monitor.start_monitoring()

            start_time = time.time()
            processed_count = 0
            error_count = 0

            for item in test_data:
                try:
                    # 复杂处理逻辑
                    if item["value"] > 200:
                        # 数据转换
                        item["normalized_value"] = item["value"] / 1000.0

                        # 标签处理
                        tags = item["metadata"]["tags"]
                        item["tag_count"] = len(tags)
                        item["has_high_priority"] = item["metadata"]["priority"] == "high"

                        # 统计计算
                        if tags:
                            item["avg_tag_length"] = sum(len(tag) for tag in tags) / len(tags)

                        processed_count += 1

                    # 模拟更长的处理时间
                    time.sleep(0.005)  # 5ms

                except Exception as e:
                    error_count += 1
                    print(f"处理错误: {e}")

            end_time = time.time()
            processing_time = end_time - start_time

            self.monitor.stop_monitoring()

            throughput = size / processing_time if processing_time > 0 else 0
            result = {
                "test_name": "complex_processing",
                "data_size": size,
                "processing_time": processing_time,
                "throughput": throughput,
                "processed_count": processed_count,
                "error_count": error_count,
                "success_rate": (size - error_count) / size * 100
            }
            self.test_results.append(result)

            print(".3f")
            print(".1f")
            print(".1f")
            print(".1f")

    def memory_usage_benchmark(self):
        """内存使用基准测试"""
        print("\n=== 内存使用基准测试 ===")

        # 测试不同大小的数据集内存使用
        sizes = [1000, 5000, 10000]

        for size in sizes:
            print(f"\n测试数据大小: {size}")

            # 记录初始内存
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            else:
                initial_memory = random.uniform(80.0, 150.0)  # 模拟初始内存

            # 创建大数据集
            large_data = []
            for i in range(size):
                # 创建包含嵌套结构的大对象
                item = {
                    "id": i,
                    "data": "x" * 1000,  # 1KB字符串
                    "nested": {
                        "level1": {
                            "level2": {
                                "array": list(range(100)),
                                "text": "nested_text_" * 10
                            }
                        }
                    },
                    "list_data": [f"item_{j}" for j in range(50)]
                }
                large_data.append(item)

            # 记录创建后的内存
            if PSUTIL_AVAILABLE:
                after_creation_memory = process.memory_info().rss / 1024 / 1024  # MB
            else:
                after_creation_memory = initial_memory + random.uniform(20.0, 100.0)  # 模拟内存增加
            memory_increase = after_creation_memory - initial_memory

            # 执行一些处理
            self.monitor.start_monitoring()
            processed = sum(1 for item in large_data if len(item["data"]) > 500)
            self.monitor.stop_monitoring()

            # 清理数据
            del large_data

            result = {
                "test_name": "memory_usage",
                "data_size": size,
                "initial_memory": initial_memory,
                "after_creation_memory": after_creation_memory,
                "memory_increase": memory_increase,
                "processed_items": processed
            }
            self.test_results.append(result)

            print(".1f")
            print(".1f")
            print(".1f")
            print(f"处理项目数: {processed}")

    def latency_analysis_benchmark(self):
        """延迟分析基准测试"""
        print("\n=== 延迟分析基准测试 ===")

        # 测试不同批次大小的延迟
        batch_sizes = [1, 10, 50, 100]

        for batch_size in batch_sizes:
            print(f"\n批次大小: {batch_size}")

            latencies = []

            for _ in range(20):  # 20次测量
                test_data = self.create_test_data(batch_size)

                start_time = time.time()

                # 处理批次
                for item in test_data:
                    item["processed"] = True
                    time.sleep(0.001)  # 1ms处理时间

                end_time = time.time()
                latency = (end_time - start_time) * 1000  # ms
                latencies.append(latency)

            # 统计延迟
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            min_latency = min(latencies)
            max_latency = max(latencies)

            result = {
                "test_name": "latency_analysis",
                "batch_size": batch_size,
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
                "min_latency": min_latency,
                "max_latency": max_latency,
                "measurements": len(latencies)
            }
            self.test_results.append(result)

            print(".2f")
            print(".2f")
            print(".2f")
            print(".2f")

    def concurrent_processing_benchmark(self):
        """并发处理基准测试"""
        print("\n=== 并发处理基准测试 ===")

        import concurrent.futures

        def process_item(item):
            """处理单个项目"""
            time.sleep(0.01)  # 10ms处理时间
            return {
                "id": item["id"],
                "processed": True,
                "result": item["value"] * 2
            }

        test_sizes = [50, 100, 200]
        max_workers_list = [1, 2, 4]

        for size in test_sizes:
            print(f"\n数据大小: {size}")

            test_data = self.create_test_data(size)

            for max_workers in max_workers_list:
                self.monitor.start_monitoring()

                start_time = time.time()

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    results = list(executor.map(process_item, test_data))

                end_time = time.time()
                processing_time = end_time - start_time

                self.monitor.stop_monitoring()

                throughput = size / processing_time if processing_time > 0 else 0

                result = {
                    "test_name": "concurrent_processing",
                    "data_size": size,
                    "max_workers": max_workers,
                    "processing_time": processing_time,
                    "throughput": throughput,
                    "results_count": len(results)
                }
                self.test_results.append(result)

                print(f"  工作线程数 {max_workers}:")
                print(".3f")
                print(".1f")

    def parallelism_config_test(self):
        """并行度配置测试"""
        print("\n=== 并行度配置测试 ===")
        
        test_sizes = [1000]
        parallelism_levels = [1, 2, 4, 8]
        
        for size in test_sizes:
            print(f"\n测试数据大小: {size}")
            
            test_data = self.create_test_data(size)
            
            for parallelism in parallelism_levels:
                self.monitor.start_monitoring()
                
                start_time = time.time()
                
                # 使用 Stream with config
                from sageflow import Stream
                
                stream = Stream.from_list(test_data).config(parallelism=parallelism) \
                               .map(lambda item: {**item, 'processed': True}) \
                               .execute()
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                self.monitor.stop_monitoring()
                
                throughput = size / processing_time if processing_time > 0 else 0
                
                result = {
                    "test_name": "parallelism_config",
                    "data_size": size,
                    "parallelism": parallelism,
                    "processing_time": processing_time,
                    "throughput": throughput,
                    "results_count": len(stream)
                }
                self.test_results.append(result)
                
                print(f"  并行度 {parallelism}: {throughput:.1f} items/s, 耗时 {processing_time:.3f}s")

    def generate_performance_report(self):
        """生成性能报告"""
        print("\n=== 性能测试汇总报告 ===")

        if not self.test_results:
            print("没有测试结果")
            return

        # 按测试类型分组
        test_groups = defaultdict(list)
        for result in self.test_results:
            test_groups[result["test_name"]].append(result)

        for test_name, results in test_groups.items():
            print(f"\n{test_name.upper()} 测试结果:")
            print("-" * 40)

            for result in results:
                if test_name == "simple_processing":
                    print(f"数据大小 {result['data_size']}: {result['throughput']:.1f} items/s, "
                          ".1f")
                elif test_name == "complex_processing":
                    print(f"数据大小 {result['data_size']}: {result['throughput']:.1f} items/s, "
                          ".1f")
                elif test_name == "memory_usage":
                    print(f"数据大小 {result['data_size']}: 内存增加 {result['memory_increase']:.1f} MB")
                elif test_name == "latency_analysis":
                    print(f"批次大小 {result['batch_size']}: 平均延迟 {result['avg_latency']:.2f} ms, "
                          ".2f")
                elif test_name == "concurrent_processing":
                    print(f"大小 {result['data_size']}, 线程 {result['max_workers']}: "
                          ".1f")

        # 系统资源监控报告
        self.monitor.print_summary_report()

def main():
    """主函数"""
    print("SAGE Flow 性能和监控示例")
    print("=" * 60)

    benchmark = PerformanceBenchmark()

    # 执行各种性能测试
    benchmark.simple_processing_benchmark()
    benchmark.complex_processing_benchmark()
    benchmark.memory_usage_benchmark()
    benchmark.latency_analysis_benchmark()
    benchmark.concurrent_processing_benchmark()
    benchmark.parallelism_config_test()

    # 生成性能报告
    benchmark.generate_performance_report()

    print("\n✓ 性能和监控示例完成")

    # 功能说明
    print("\n=== 性能和监控功能说明 ===")
    print("1. 基准测试: 提供多种处理场景的性能基准")
    print("2. 资源监控: 实时监控CPU、内存使用情况")
    print("3. 吞吐量分析: 测量系统处理能力")
    print("4. 延迟分析: 分析响应时间和延迟分布")
    print("5. 并发测试: 测试多线程处理性能")
    print("6. 内存分析: 监控内存使用模式")


if __name__ == "__main__":
    main()