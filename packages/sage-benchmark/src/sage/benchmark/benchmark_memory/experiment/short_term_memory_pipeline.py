"""Locomo 长轮对话记忆实验 - 3条Pipeline架构

架构说明：
===========

【3条 Pipeline】：
1. 主 Pipeline (Controller Pipeline):
   - LocomoSource → PipelineCaller → MemorySink
   - 逐轮喂入对话历史，调用两个服务Pipeline

2. 记忆存储 Pipeline (Memory Insert Service):
   - PipelineServiceSource → PreInsert → MemoryInsert → PostInsert → PipelineServiceSink
   - 职责：存储对话到短期记忆服务

3. 记忆测试 Pipeline (Memory Test Service):
   - PipelineServiceSource → PreRetrieval → MemoryRetrieval → PostRetrieval → MemoryTest → PipelineServiceSink
   - 职责：检索历史、生成答案

【关键机制】：
- 背压 (Backpressure): 主 Pipeline 的 call_service() 会阻塞，保证顺序处理
- Pipeline-as-Service: 通过 PipelineBridge 实现双向通信
- 两阶段处理：
  * 阶段1：记忆存储（总是执行）
  * 阶段2：记忆测试（有问题时对所有可见问题进行测试）
- autostop: 主 Pipeline 处理完所有批次后自动停止并清理资源

运行: python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/short_term_memory_pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from sage.benchmark.benchmark_memory.experiment.libs.memory_source import MemorySource
from sage.benchmark.benchmark_memory.experiment.libs.memory_sink import MemorySink

# 导入业务相关的算子
from sage.benchmark.benchmark_memory.experiment.libs.pipeline_caller import PipelineCaller

# 导入记忆操作算子
from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert
from sage.benchmark.benchmark_memory.experiment.libs.memory_insert import MemoryInsert
from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert
from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import PreRetrieval
from sage.benchmark.benchmark_memory.experiment.libs.memory_retrieval import MemoryRetrieval
from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import PostRetrieval
from sage.benchmark.benchmark_memory.experiment.libs.memory_test import MemoryTest

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.data.locomo.dataloader import LocomoDataLoader
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
)
from sage.middleware.components.sage_mem.services.short_term_memory_service import (
    ShortTermMemoryService,
)


def main():
    """主函数 - Locomo 长轮对话记忆实验"""

    # 禁用日志
    CustomLogger.disable_global_console_debug()
    import logging

    logging.getLogger("root").setLevel(logging.WARNING)

    print("=" * 60)
    print("Locomo 长轮对话记忆实验")
    print("Pipeline-as-Service 架构")
    print("=" * 60)

    # ============================================================
    # 第一步：加载配置
    # ============================================================
    script_dir = Path(__file__).parent
    config_file = script_dir / "config" / "locomo_short_term_memory_pipeline.yaml"

    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)

    print(f"📄 加载配置文件: {config_file}")
    with open(config_file) as f:
        config = yaml.safe_load(f)

    # ============================================================
    # 第二步：选择测试样本
    # ============================================================
    loader = LocomoDataLoader()
    sample_ids = loader.get_sample_id()
    test_sample_id = sample_ids[0]  # 使用第一个样本进行测试

    print(f"\n📊 使用样本: {test_sample_id}")
    turns = loader.get_turn(test_sample_id)
    total_sessions = len(turns)
    total_dialogs = sum((max_idx + 1) for _, max_idx in turns)

    print(f"   - 总会话数: {total_sessions}")
    print(f"   - 总对话数: {total_dialogs}")

    # ============================================================
    # 第三步：创建环境
    # ============================================================
    env = LocalEnvironment("locomo_memory_experiment")

    # ============================================================
    # 第四步：注册服务和创建桥梁
    # ============================================================
    print("\n【注册服务 1】短期记忆服务（ShortTermMemoryService）")
    print("  └─ 职责: 存储和检索对话历史")
    # 使用3轮对话窗口（每轮2条消息 = 6条消息）
    env.register_service("short_term_memory", ShortTermMemoryService, max_dialog=3)

    print("\n【创建桥梁 1】记忆存储服务桥梁")
    insert_bridge = PipelineBridge()
    print("【注册服务 2】记忆存储服务（Pipeline 即服务）")
    env.register_service("memory_insert_service", PipelineService, insert_bridge)

    print("\n【创建桥梁 2】记忆测试服务桥梁")
    test_bridge = PipelineBridge()
    print("【注册服务 3】记忆测试服务（Pipeline 即服务）")
    env.register_service("memory_test_service", PipelineService, test_bridge)

    # ============================================================
    # 第五步：创建 3 条 Pipeline
    # ============================================================
    print("\n【创建 Pipeline 1】记忆存储 Pipeline")
    print("  └─ 架构: PipelineServiceSource → PreInsert → MemoryInsert → PostInsert → PipelineServiceSink")
    print("  └─ 职责: 存储对话到短期记忆")
    (
        env.from_source(PipelineServiceSource, insert_bridge)
        .map(PreInsert, action="none")
        .map(MemoryInsert)
        .map(PostInsert, action="none")
        .sink(PipelineServiceSink)
    )

    print("\n【创建 Pipeline 2】记忆测试 Pipeline")
    print("  └─ 架构: PipelineServiceSource → PreRetrieval → MemoryRetrieval → PostRetrieval → MemoryTest → PipelineServiceSink")
    print("  └─ 职责: 检索历史、生成答案")
    (
        env.from_source(PipelineServiceSource, test_bridge)
        .map(PreRetrieval, action="none")
        .map(MemoryRetrieval)
        .map(PostRetrieval, action="none")
        .map(MemoryTest, config)
        .sink(PipelineServiceSink)
    )
    
    print("\n【创建 Pipeline 3】主 Pipeline")
    print("  └─ 架构: MemorySource → PipelineCaller → MemorySink")
    print("  └─ 职责: 逐轮喂入对话，调用两个服务处理，保存结果")
    (
        env.from_batch(MemorySource, dataset="locomo", task_id=test_sample_id)
        .map(PipelineCaller, dataset="locomo", task_id=test_sample_id)
        .sink(MemorySink, dataset_name="locomo", output_name=f"result_{test_sample_id}")
    )

    print("\n" + "=" * 60)
    print("🚀 启动所有 Pipeline（autostop=True）")
    print("=" * 60 + "\n")

    # ============================================================
    # 第六步：启动并自动等待完成
    # ============================================================
    # autostop=True 会：
    # 1. 等待主 Pipeline 所有批次处理完成
    # 2. 自动调用 env.close() 清理资源
    # 3. shutdown 命令通过数据流传递，优雅关闭服务 Pipeline
    env.submit(autostop=True)

    print("\n" + "=" * 60)
    print("✅ 所有 Pipeline 执行完成!")
    print("=" * 60)
    print("✅ 资源已由 autostop 自动清理")
    print(f"\n📁 结果已保存至: .sage/benchmarks/benchmark_memory/locomo/result_{test_sample_id}.txt")
    print("\n架构总结：")
    print("  • 3条 Pipeline:")
    print("    1. 主 Pipeline: 数据源 → 调用服务 → 结果收集")
    print("    2. 记忆存储 Pipeline: PreInsert → MemoryInsert → PostInsert")
    print("    3. 记忆测试 Pipeline: PreRetrieval → MemoryRetrieval → PostRetrieval → MemoryTest")
    print("  • 3个 Service:")
    print("    - ShortTermMemoryService: 管理对话历史窗口")
    print("    - Memory Insert Service: Pipeline 即服务（记忆存储）")
    print("    - Memory Test Service: Pipeline 即服务（记忆测试）")
    print("  • 2个桥梁: PipelineBridge 实现双向通信")
    print("  • 背压机制: call_service() 阻塞保证顺序执行，两个服务共享 ShortTermMemoryService 不会冲突")
    print("  • 两大阶段:")
    print("    - 阶段1: 记忆存储（总是执行）")
    print("    - 阶段2: 记忆测试（有问题时对所有可见问题进行测试）\n")


if __name__ == "__main__":
    print("=== 程序开始执行 ===\n")
    main()
    print("\n=== 程序执行完毕 ===")
