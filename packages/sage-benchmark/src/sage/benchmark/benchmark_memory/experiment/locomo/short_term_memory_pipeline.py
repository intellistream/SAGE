"""Locomo 长轮对话记忆实验 - Pipeline-as-Service 架构

架构说明：
===========

【2条 Pipeline】：
1. 主 Pipeline (Controller Pipeline):
   - LocomoSource → LocomoControllerMap → LocomoSink
   - 逐轮喂入对话历史，通过 call_service() 调用服务 Pipeline

2. 服务 Pipeline (Locomo Service):
   - PipelineServiceSource → LocomoServiceMap → PipelineServiceSink
   - 从 PipelineBridge 拉取请求，存储历史，检测问题，生成答案
   - 同时作为 Pipeline 和 Service（双重身份）

【关键机制】：
- 背压 (Backpressure): 主 Pipeline 的 call_service() 会阻塞，保证顺序处理
- Pipeline-as-Service: 通过 PipelineBridge 实现双向通信
- 历史状态: 服务 Pipeline 内部维护对话历史，问题不破坏历史状态
- 增量检测: 使用 get_question_list() 检测新触发的问题
- autostop: 主 Pipeline 处理完所有批次后自动停止并清理资源

运行: python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/locomo/short_term_memory_pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from libs.locomo_io import LocomoSink, LocomoSource

# 导入业务相关的算子
from locomo_operators import LocomoControllerMap, LocomoServiceMap

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.data.locomo.dataloader import LocomoDataLoader
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
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
    config_file = script_dir / "config" / "short_term_memory_pipeline.yaml"

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
    # 第四步：注册服务 Pipeline
    # ============================================================
    print("\n【创建桥梁】PipelineBridge（连接服务和 Pipeline）")
    locomo_bridge = PipelineBridge()

    print("【注册服务】Locomo Service（Pipeline 即服务）")
    env.register_service("locomo_service", PipelineService, locomo_bridge)

    # ============================================================
    # 第五步：创建 2 条 Pipeline
    # ============================================================
    print("\n【创建 Pipeline 1】服务 Pipeline")
    print("  └─ 架构: PipelineServiceSource → LocomoServiceMap → PipelineServiceSink")
    print("  └─ 职责: 存储历史、检测问题、生成答案")
    env.from_source(PipelineServiceSource, locomo_bridge).map(LocomoServiceMap, config).sink(
        PipelineServiceSink
    )

    print("\n【创建 Pipeline 2】主 Pipeline")
    print("  └─ 架构: LocomoSource → LocomoControllerMap → LocomoSink")
    print("  └─ 职责: 逐轮喂入对话，调用服务处理，保存结果")
    env.from_batch(LocomoSource, sample_id=test_sample_id).map(LocomoControllerMap).sink(
        LocomoSink, output_name=f"result_{test_sample_id}"
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
    print(f"\n📁 结果已保存至: .benchmarks/benchmark_memory/locomo/result_{test_sample_id}.json")
    print("\n架构总结：")
    print("  • 2条 Pipeline: 主 Pipeline + 服务 Pipeline")
    print("  • 1个 Service: Locomo Service（Pipeline 即服务）")
    print("  • 1个桥梁: PipelineBridge 实现双向通信")
    print("  • 背压机制: call_service() 阻塞保证顺序执行")
    print("  • 历史状态: 服务内部维护，问题不破坏历史\n")


if __name__ == "__main__":
    print("=== 程序开始执行 ===\n")
    main()
    print("\n=== 程序执行完毕 ===")
