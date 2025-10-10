#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度器对比示例
演示如何使用不同的调度策略并对比性能指标
"""

import time
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.function.source_function import SourceFunction
from sage.kernel.api.function.map_function import MapFunction
from sage.kernel.api.function.sink_function import SinkFunction
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler


class DataSource(SourceFunction):
    """简单的数据源，生成一批测试数据"""
    
    def __init__(self, total_items=20, **kwargs):
        super().__init__(**kwargs)
        self.total_items = total_items
        self.current = 0
    
    def execute(self):
        if self.current >= self.total_items:
            return None
        
        data = f"data_{self.current}"
        self.current += 1
        print(f"📤 Source: {data}")
        return data


class HeavyProcessor(MapFunction):
    """模拟资源密集型处理"""
    
    def execute(self, data):
        # 模拟耗时计算
        time.sleep(0.1)
        result = f"processed_{data}"
        print(f"⚙️  HeavyProcessor: {data} -> {result}")
        return result


class LightFilter(MapFunction):
    """模拟轻量级过滤"""
    
    def execute(self, data):
        # 只保留偶数编号的数据
        item_id = int(data.split("_")[-1])
        if item_id % 2 == 0:
            print(f"✅ LightFilter: {data} passed")
            return data
        else:
            print(f"❌ LightFilter: {data} filtered")
            return None


class ResultSink(SinkFunction):
    """收集结果"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []
    
    def execute(self, data):
        if data:
            self.results.append(data)
            print(f"💾 Sink: {data}")


def run_with_scheduler(scheduler, env_class, scheduler_name):
    """使用指定调度器运行 pipeline"""
    print(f"\n{'='*60}")
    print(f"🚀 运行实验: {scheduler_name}")
    print(f"{'='*60}\n")
    
    # 创建环境并指定调度器
    if env_class == LocalEnvironment:
        env = LocalEnvironment(
            name=f"scheduler_test_{scheduler_name}",
            scheduler=scheduler
        )
    else:
        env = RemoteEnvironment(
            name=f"scheduler_test_{scheduler_name}",
            scheduler=scheduler
        )
    
    # 构建 pipeline
    # 注意：并行度在 operator 级别指定
    (env.from_source(DataSource, total_items=20)
        .map(HeavyProcessor, parallelism=4)   # 资源密集型 operator，4 个并行实例
        .filter(LightFilter, parallelism=2)   # 轻量级 operator，2 个并行实例
        .sink(ResultSink))
    
    # 记录开始时间
    start_time = time.time()
    
    # 提交执行
    print(f"▶️  开始执行 pipeline (调度器: {scheduler_name})...\n")
    env.submit(autostop=True)
    
    # 记录结束时间
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 获取调度器指标
    metrics = env.scheduler.get_metrics()
    
    print(f"\n{'='*60}")
    print(f"📊 {scheduler_name} 执行结果")
    print(f"{'='*60}")
    print(f"总耗时: {elapsed:.2f} 秒")
    print(f"调度器指标:")
    for key, value in metrics.items():
        print(f"  - {key}: {value}")
    print(f"{'='*60}\n")
    
    return {
        "scheduler": scheduler_name,
        "elapsed_time": elapsed,
        "metrics": metrics
    }


def main():
    """主函数：对比不同调度策略"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║           SAGE 调度器对比示例                                  ║
║  演示如何在 Environment 级别配置不同的调度策略                  ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # 实验 1: FIFO 调度器 (LocalEnvironment)
    print("\n🧪 实验 1: FIFO 调度器 (Local)")
    result1 = run_with_scheduler(
        scheduler=FIFOScheduler(),
        env_class=LocalEnvironment,
        scheduler_name="FIFO_Local"
    )
    results.append(result1)
    
    time.sleep(2)  # 等待一下
    
    # 实验 2: 负载感知调度器 (LocalEnvironment)
    print("\n🧪 实验 2: 负载感知调度器 (Local)")
    result2 = run_with_scheduler(
        scheduler=LoadAwareScheduler(max_concurrent=10),
        env_class=LocalEnvironment,
        scheduler_name="LoadAware_Local"
    )
    results.append(result2)
    
    # 可选：如果有 Ray 环境，可以测试 RemoteEnvironment
    # 注意：需要先启动 JobManager daemon
    try_remote = False  # 设置为 True 以测试 RemoteEnvironment
    
    if try_remote:
        time.sleep(2)
        
        # 实验 3: FIFO 调度器 (RemoteEnvironment)
        print("\n🧪 实验 3: FIFO 调度器 (Remote)")
        result3 = run_with_scheduler(
            scheduler="fifo",  # 也可以使用字符串
            env_class=RemoteEnvironment,
            scheduler_name="FIFO_Remote"
        )
        results.append(result3)
        
        time.sleep(2)
        
        # 实验 4: 负载感知调度器 (RemoteEnvironment)
        print("\n🧪 实验 4: 负载感知调度器 (Remote)")
        result4 = run_with_scheduler(
            scheduler="load_aware",  # 也可以使用字符串
            env_class=RemoteEnvironment,
            scheduler_name="LoadAware_Remote"
        )
        results.append(result4)
    
    # 打印对比总结
    print("\n" + "="*80)
    print("📈 调度器性能对比总结")
    print("="*80)
    
    for result in results:
        print(f"\n{result['scheduler']}:")
        print(f"  总耗时: {result['elapsed_time']:.2f} 秒")
        print(f"  调度策略: {result['metrics'].get('scheduler_type', 'N/A')}")
        print(f"  已调度任务数: {result['metrics'].get('total_scheduled', 'N/A')}")
        if 'avg_latency_ms' in result['metrics']:
            print(f"  平均延迟: {result['metrics']['avg_latency_ms']:.2f} ms")
        if 'avg_resource_utilization' in result['metrics']:
            print(f"  平均资源利用率: {result['metrics']['avg_resource_utilization']:.2%}")
    
    print("\n" + "="*80)
    print("✅ 所有实验完成！")
    print("="*80)
    
    print("""
💡 关键要点：
  1. 用户在创建 Environment 时指定调度策略
     - env = LocalEnvironment(scheduler="fifo")
     - env = RemoteEnvironment(scheduler=LoadAwareScheduler())
  
  2. 并行度在定义 transformation 时指定
     - .map(HeavyProcessor, parallelism=4)
     - .filter(LightFilter, parallelism=2)
  
  3. 调度器在应用级别工作，对用户透明
     - 自动根据策略调度所有任务
     - 开发者可以轻松对比不同策略的性能
    """)


if __name__ == "__main__":
    main()
