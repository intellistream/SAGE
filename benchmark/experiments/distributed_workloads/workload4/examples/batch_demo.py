"""
Workload 4 批处理集成示例

演示如何在 SAGE pipeline 中使用双层批处理。
"""

import time

import sys
from pathlib import Path

# 添加父目录到 path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from sage.kernel.api.local_environment import LocalEnvironment

# 导入数据模型
from models import DocumentEvent, JoinedEvent, QueryEvent

# 导入批处理模块
from batching import create_batch_pipeline_stage


def run_batching_demo():
    """运行批处理演示"""
    
    print("=" * 80)
    print("Workload 4 批处理集成演示")
    print("=" * 80)
    
    # 1. 创建环境
    env = LocalEnvironment()
    
    # 2. 创建批处理 stage
    category_agg, global_agg, coordinator = create_batch_pipeline_stage(
        category_batch_size=3,
        category_timeout_ms=500,
        global_batch_size=8,
        global_timeout_ms=1000,
    )
    
    print("\n✓ Batch pipeline stage created:")
    print(f"  - Category batch: size={category_agg.batch_size}, "
          f"timeout={category_agg.timeout_ms * 1000}ms")
    print(f"  - Global batch: size={global_agg.batch_size}, "
          f"timeout={global_agg.timeout_ms * 1000}ms")
    
    # 3. 创建模拟数据源
    def create_test_events(count: int):
        """创建测试事件"""
        categories = ["finance", "healthcare", "technology", "general"]
        
        for i in range(count):
            category = categories[i % len(categories)]
            yield JoinedEvent(
                joined_id=f"join_{i}",
                query=QueryEvent(
                    query_id=f"q{i}",
                    query_text=f"Test query {i}",
                    query_type="factual",
                    category=category,
                    timestamp=time.time(),
                ),
                matched_docs=[],
                join_timestamp=time.time(),
                semantic_score=0.8 + (i % 10) * 0.01,
            )
    
    # 4. 模拟 pipeline 流程
    print("\n" + "=" * 80)
    print("Processing Events")
    print("=" * 80)
    
    events = list(create_test_events(20))
    print(f"\n✓ Created {len(events)} test events")
    
    # 4.1 Stage 1: Category batching
    print("\n--- Stage 1: Category Batching ---")
    category_batches = []
    
    for i, event in enumerate(events):
        result = category_agg.execute(event)
        if result:
            category_batches.append(result)
            coordinator.record_category_batch(result)
            print(f"  [{i+1:2d}] Category batch created: {result.batch_id} "
                  f"(size={result.batch_size}, category={result.category})")
    
    # 强制刷新剩余
    remaining = category_agg.flush_all()
    if remaining:
        print(f"\n  Flushing {len(remaining)} remaining category batches:")
        for batch in remaining:
            category_batches.append(batch)
            coordinator.record_category_batch(batch)
            print(f"    - {batch.batch_id} (size={batch.batch_size}, "
                  f"category={batch.category})")
    
    print(f"\n✓ Total category batches: {len(category_batches)}")
    
    # 4.2 Stage 2: Global batching
    print("\n--- Stage 2: Global Batching ---")
    global_batches = []
    
    for i, category_batch in enumerate(category_batches):
        result = global_agg.execute(category_batch)
        if result:
            global_batches.append(result)
            coordinator.record_global_batch(result)
            print(f"  [{i+1:2d}] Global batch created: {result.batch_id} "
                  f"(size={result.batch_size})")
    
    # 强制刷新剩余
    remaining_global = global_agg.flush_all()
    if remaining_global:
        print(f"\n  Flushing {len(remaining_global)} remaining global batches:")
        for batch in remaining_global:
            global_batches.append(batch)
            coordinator.record_global_batch(batch)
            print(f"    - {batch.batch_id} (size={batch.batch_size})")
    
    print(f"\n✓ Total global batches: {len(global_batches)}")
    
    # 5. 打印统计摘要
    print("\n" + "=" * 80)
    coordinator.print_summary()
    
    # 6. 验证数据完整性
    print("\n" + "=" * 80)
    print("Data Integrity Check")
    print("=" * 80)
    
    # 统计所有 global batch 中的 items
    total_items_in_global = sum(b.batch_size for b in global_batches)
    
    print(f"  Input events:         {len(events)}")
    print(f"  Category batches:     {len(category_batches)}")
    print(f"  Global batches:       {len(global_batches)}")
    print(f"  Items in global:      {total_items_in_global}")
    
    if total_items_in_global == len(events):
        print("\n  ✅ Data integrity verified: All events processed!")
    else:
        print(f"\n  ⚠️  Data mismatch: {len(events)} events → "
              f"{total_items_in_global} in global batches")
    
    # 7. 分析批次效率
    print("\n" + "=" * 80)
    print("Batch Efficiency Analysis")
    print("=" * 80)
    
    category_sizes = [b.batch_size for b in category_batches]
    global_sizes = [b.batch_size for b in global_batches]
    
    print(f"\n  Category batch sizes: {category_sizes}")
    print(f"    - Min: {min(category_sizes)}, Max: {max(category_sizes)}, "
          f"Avg: {sum(category_sizes) / len(category_sizes):.2f}")
    
    print(f"\n  Global batch sizes: {global_sizes}")
    print(f"    - Min: {min(global_sizes)}, Max: {max(global_sizes)}, "
          f"Avg: {sum(global_sizes) / len(global_sizes):.2f}")
    
    # 计算批处理效率（接近满批次的比例）
    category_efficiency = sum(
        1 for size in category_sizes if size >= category_agg.batch_size * 0.8
    ) / len(category_sizes) * 100
    
    global_efficiency = sum(
        1 for size in global_sizes if size >= global_agg.batch_size * 0.8
    ) / len(global_sizes) * 100
    
    print(f"\n  Batch efficiency (≥80% full):")
    print(f"    - Category: {category_efficiency:.1f}%")
    print(f"    - Global:   {global_efficiency:.1f}%")
    
    print("\n" + "=" * 80)
    print("✅ Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    run_batching_demo()
