"""Locomo 长轮对话记忆实验 - Pipeline 架构

详细架构说明和测试机制请参考: mem_docs/Pipeline_README.md
注意：修改代码时请同步更新该文档
"""

from __future__ import annotations

from sage.benchmark.benchmark_memory.experiment.libs.memory_evaluation import (
    MemoryEvaluation,
)
from sage.benchmark.benchmark_memory.experiment.libs.memory_insert import MemoryInsert
from sage.benchmark.benchmark_memory.experiment.libs.memory_retrieval import MemoryRetrieval
from sage.benchmark.benchmark_memory.experiment.libs.memory_sink import MemorySink
from sage.benchmark.benchmark_memory.experiment.libs.memory_source import MemorySource
from sage.benchmark.benchmark_memory.experiment.libs.pipeline_caller import PipelineCaller
from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert
from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import PostRetrieval
from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert
from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import PreRetrieval
from sage.benchmark.benchmark_memory.experiment.utils import RuntimeConfig, parse_args
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
)
from sage.middleware.components.sage_mem.services import MemoryServiceFactory


def main():
    """主函数"""
    CustomLogger.disable_global_console_debug()

    # 解析命令行参数并加载配置
    args = parse_args()
    config = RuntimeConfig.load(args.config, args.task_id)

    # 创建环境
    env = LocalEnvironment("memory_test_experiment")

    # 注册服务 - 使用工厂模式动态创建服务
    service_name = config.get("services.register_memory_service", "short_term_memory")
    factory = MemoryServiceFactory.create(service_name, config)
    env.register_service_factory(service_name, factory)

    # 获取服务超时配置（默认 300 秒，足够 link_evolution 等耗时操作）
    pipeline_service_timeout = config.get("runtime.pipeline_service_timeout", 300.0)

    insert_bridge = PipelineBridge()
    env.register_service(
        "memory_insert_service",
        PipelineService,
        insert_bridge,
        request_timeout=pipeline_service_timeout,
    )

    test_bridge = PipelineBridge()
    env.register_service(
        "memory_test_service",
        PipelineService,
        test_bridge,
        request_timeout=pipeline_service_timeout,
    )

    # 创建 Pipeline
    # 记忆插入Pipeline
    (
        env.from_source(PipelineServiceSource, insert_bridge)
        .map(PreInsert, config)
        .map(MemoryInsert, config)
        .map(PostInsert, config)
        .sink(PipelineServiceSink)
    )

    # 记忆测试（包含检索）Pipeline
    (
        env.from_source(PipelineServiceSource, test_bridge)
        .map(PreRetrieval, config)
        .map(MemoryRetrieval, config)
        .map(PostRetrieval, config)
        .map(MemoryEvaluation, config)
        .sink(PipelineServiceSink)
    )

    # 主Pipeline，通过背压机制实现one by one处理
    (env.from_batch(MemorySource, config).map(PipelineCaller, config).sink(MemorySink, config))

    # 启动并等待完成
    env.submit(autostop=True)


if __name__ == "__main__":
    main()
