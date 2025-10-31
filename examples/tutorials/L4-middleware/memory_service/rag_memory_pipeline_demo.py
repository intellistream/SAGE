"""简化的 Pipeline-as-Service 示例 - 用于理解背压机制

架构说明：
===========

【2条 Pipeline】：
1. 主 Pipeline (Controller Pipeline):
   - QuestionBatch → ProcessQuestion → DisplayAnswer
   - 顺序发送问题，通过 call_service() 调用 QA Pipeline Service

2. 服务 Pipeline (QA Pipeline):
   - QAPipelineSource → QAPipelineMap → QAPipelineSink
   - 从 PipelineBridge 拉取请求，处理后返回结果
   - 同时作为 Pipeline 和 Service（双重身份）

【2个 Service】：
1. Memory Service (纯服务):
   - MockMemoryService
   - 提供 retrieve() 和 insert() 接口
   - 被 QA Pipeline 调用

2. QA Pipeline Service (Pipeline 即服务):
   - QAPipelineService + PipelineBridge
   - 将 QA Pipeline 包装成可调用的 Service
   - 被主 Pipeline 调用

【关键机制】：
- 背压 (Backpressure): 主 Pipeline 的 call_service() 会阻塞，直到 QA Pipeline 完成
- Pipeline-as-Service: 通过 PipelineBridge 实现 Service 和 Pipeline 之间的双向通信
- StopSignal: 通过数据流自然传递停止信号，优雅关闭 QA Pipeline

运行: python examples/tutorials/L4-middleware/memory_service/rag_memory_pipeline_demo.py
"""

from __future__ import annotations


from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSource,
    PipelineServiceSink,
)

# 导入业务相关的算子和服务
from pipeline_as_service_operators import (
    MockMemoryService,
    QAPipelineMap,
    QuestionBatch,
    ProcessQuestion,
    DisplayAnswer,
)


def main():
    """主函数 - 演示 Pipeline-as-Service 架构"""

    print("=" * 60)
    print("Pipeline-as-Service 架构演示")
    print("2条 Pipeline + 2个 Service")
    print("=" * 60)

    CustomLogger.disable_global_console_debug()

    # 测试数据
    questions = [
        "问题1：什么是背压机制？",
        "问题2：SAGE 如何实现 Pipeline-as-Service？",
        "问题3：PipelineBridge 的作用是什么？",
    ]

    print(f"\n将依次处理 {len(questions)} 个问题")
    print("观察输出验证：背压机制 → 顺序执行\n")

    # ============================================================
    # 第一步：创建环境
    # ============================================================
    env = LocalEnvironment("pipeline_as_service_demo")

    # ============================================================
    # 第二步：注册 2 个 Service
    # ============================================================
    print("【注册 Service 1】Memory Service（纯服务）")
    env.register_service("mock_memory", MockMemoryService)

    print("【创建桥梁】PipelineBridge（连接 Service 和 Pipeline）")
    qa_bridge = PipelineBridge()

    print("【注册 Service 2】QA Pipeline Service（Pipeline 即服务）")
    env.register_service("qa_pipeline", PipelineService, qa_bridge)

    # ============================================================
    # 第三步：创建 2 条 Pipeline
    # ============================================================
    print("\n【创建 Pipeline 1】QA Pipeline（服务 Pipeline）")
    print("  └─ 架构: PipelineServiceSource → QAPipelineMap → PipelineServiceSink")
    print("  └─ 职责: 从 Bridge 拉取请求，调用 Memory Service，返回结果")
    env.from_source(PipelineServiceSource, qa_bridge).map(QAPipelineMap).sink(
        PipelineServiceSink
    )

    print("\n【创建 Pipeline 2】主 Pipeline（Controller Pipeline）")
    print("  └─ 架构: QuestionBatch → ProcessQuestion → DisplayAnswer")
    print("  └─ 职责: 批量发送问题，调用 QA Pipeline Service，显示结果")
    env.from_batch(QuestionBatch, questions).map(ProcessQuestion).sink(DisplayAnswer)

    print("\n" + "=" * 60)
    print("🚀 启动所有 Pipeline（autostop=True）")
    print("=" * 60 + "\n")

    # ============================================================
    # 第四步：启动并自动等待完成
    # ============================================================
    # autostop=True 会：
    # 1. 等待主 Pipeline 所有批次处理完成
    # 2. 自动调用 env.close() 清理资源（得益于前面的修复）
    # 3. shutdown 命令会通过数据流传递，优雅关闭 QA Pipeline
    env.submit(autostop=True)

    print("\n" + "=" * 60)
    print("✅ 所有 Pipeline 执行完成!")
    print("=" * 60)
    print("✅ 资源已由 autostop 自动清理")
    print("\n架构总结：")
    print("  • 2条 Pipeline: 主 Pipeline + QA Pipeline")
    print("  • 2个 Service: Memory Service + QA Pipeline Service")
    print("  • 1个桥梁: PipelineBridge 实现双向通信")
    print("  • 背压机制: call_service() 阻塞保证顺序执行\n")


if __name__ == "__main__":
    main()
