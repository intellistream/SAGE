"""
Distributed CPU-Intensive Workloads for SAGE Benchmark
=======================================================

4个递进式复杂度的分布式CPU密集型工作负载，用于测试SAGE的：
- 分布式调度能力
- 跨节点资源管理
- CPU密集型计算性能
- 复杂Pipeline协调能力

Workloads:
- Workload 1: 基准RAG Pipeline (30-50% CPU)
- Workload 2: 多阶段RAG + 双路Join (50-70% CPU)
- Workload 3: 双流Semantic Join + 双VDB (70-85% CPU)
- Workload 4: 极致复杂度 + 双层Batch (85-95% CPU)
"""

from .join_operators import (
    DocKeyExtractor,
    LargeWindowSemanticJoinFunction,
    QueryKeyExtractor,
    SemanticJoinFunction,
)
from .workload_config import (
    TEST_SCENARIOS,
    WORKLOAD_CONFIGS,
    TestScenario,
    WorkloadConfig,
    get_config,
    get_scenario,
)

__all__ = [
    # Config
    "WorkloadConfig",
    "TestScenario",
    "WORKLOAD_CONFIGS",
    "TEST_SCENARIOS",
    "get_config",
    "get_scenario",
    # Join operators
    "SemanticJoinFunction",
    "LargeWindowSemanticJoinFunction",
    "QueryKeyExtractor",
    "DocKeyExtractor",
]
