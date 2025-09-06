import timeit
import numpy as np
from sageflow import Stream

def benchmark_parallelism(parallelism: int, data_size: int = 10000):
    """基准测试不同并行度的性能"""
    data = list(range(data_size))
    
    def run_pipeline():
        stream = Stream.from_list(data).config(parallelism=parallelism) \
                       .map(lambda x: x * 2) \
                       .execute()
        return stream
    
    time_taken = timeit.timeit(run_pipeline, number=10)
    throughput = data_size * 10 / time_taken  # items per second
    return time_taken / 10, throughput  # average time, throughput

def main():
    """主函数"""
    print("SAGE Flow 并行度基准测试")
    print("=" * 40)
    
    parallelisms = [1, 2, 4, 8]
    data_size = 10000
    
    results = {}
    
    for p in parallelisms:
        avg_time, throughput = benchmark_parallelism(p, data_size)
        results[p] = (avg_time, throughput)
        print(f"并行度 {p}: 平均时间 {avg_time:.4f}s, 吞吐量 {throughput:.1f} items/s")
    
    # 比较性能
    print("\n性能比较:")
    base_throughput = results[1][1]
    for p, (t, tp) in results.items():
        improvement = (tp / base_throughput - 1) * 100
        print(f"并行度 {p}: 比单线程提升 {improvement:.1f}%")

if __name__ == "__main__":
    main()