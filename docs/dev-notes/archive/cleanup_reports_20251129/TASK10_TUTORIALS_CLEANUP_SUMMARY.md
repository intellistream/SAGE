# Task 10: 教程与示例更新 - 清理摘要

**执行日期**: 2024-12-01
**任务范围**: `docs-public/docs_src/tutorials/`
**状态**: ✅ 完成

## 概述

Task 10 是文档清理阶段二的任务，主要目标是更新教程文档中的代码示例，确保与最新的 SAGE API 保持一致，并完善占位页面的内容。

## 执行内容

### 1. 导入路径更新

将过时的导入路径更新为当前正确的路径：

| 旧路径 | 新路径 |
|--------|--------|
| `sage.core.api.local_environment` | `sage.kernel.api.local_environment` |
| `sage.core.api.function.map_function` | `sage.common.core.functions.map_function` |
| `sage.core.api.function.batch_function` | `sage.common.core.functions.batch_function` |
| `sage.core.api.function.sink_function` | `sage.common.core.functions.sink_function` |
| `sage.core.api.function.filter_function` | `sage.common.core.functions.filter_function` |
| `sage.core.api.function.flatmap_function` | `sage.common.core.functions.flatmap_function` |
| `sage.core.api.function.comap_function` | `sage.common.core.functions.comap_function` |
| `sage.core.api.function.keyby_function` | `sage.common.core.functions.keyby_function` |
| `sage.core.api.function.join_function` | `sage.common.core.functions.join_function` |
| `sage.core.api.function.base_function` | `sage.common.core.functions.base_function` |

### 2. 更新的文件

#### basic/

| 文件 | 更新内容 |
|------|----------|
| `streaming-101.md` | 更新导入路径 |
| `hello_batch.md` | 更新导入路径 (2处) |
| `operators/hello_filter_world.md` | 更新导入路径、GitHub 链接 |
| `operators/hello_flatmap_world.md` | 更新导入路径、GitHub 链接 |
| `operators/hello_join_world.md` | 更新导入路径、GitHub 链接 |
| `operators/hello_filter_world_comap.md` | 更新导入路径、GitHub 链接 |
| `operators/hello_future_world.md` | 更新导入路径、GitHub 链接 |

#### advanced/

| 文件 | 更新内容 |
|------|----------|
| `advanced-rag.md` | **重写整个文档**：添加 UnifiedInferenceClient 使用教程、RAG Pipeline 示例、多源检索、分层检索、重排序、混合检索等完整内容 |
| `performance-tuning.md` | **重写整个文档**：添加性能分析、LLM 优化、Embedding 批处理、Pipeline 并行、内存优化、GPU 优化、基准测试等完整内容 |
| `distributed-pipeline.md` | 无需更新（内容完整） |
| `custom-operators.md` | 无需更新（导入路径正确） |
| `fault-tolerance.md` | 保持占位状态（内容规划已列出） |
| `complex-workflows.md` | 保持占位状态（内容规划已列出） |
| `index.md` | 无需更新（索引页面） |

### 3. GitHub 链接更新

将示例代码链接从旧的 `transformation-api/` 目录更新为当前的分层目录结构：

- `transformation-api/` → `L3-kernel/operators/`
- `transformation-api/` → `L3-kernel/functions/`
- `transformation-api/` → `L3-kernel/stream/`

### 4. 新增内容

#### advanced-rag.md 新增内容
- UnifiedInferenceClient 快速入门
- 基础 RAG Pipeline 完整示例
- 多源检索实现
- 分层检索（两阶段检索）
- Cross-Encoder 重排序
- 混合检索（向量 + BM25）
- Control Plane 模式使用
- 最佳实践总结

#### performance-tuning.md 新增内容
- 性能分析（cProfile、自定义 Profiler）
- LLM 推理优化（Control Plane、批量请求）
- Embedding 批处理优化
- Pipeline 并行优化
- 内存优化（流式处理、资源释放、监控）
- GPU 优化（显存管理、混合精度）
- 网络优化（连接池、本地优先）
- 性能基准测试（sage-benchmark 使用）

## 未处理项目

以下页面保持为占位状态，待后续完善：

1. **fault-tolerance.md** - 容错与可靠性
   - 检查点机制
   - 重试策略
   - 异常处理
   - 监控告警

2. **complex-workflows.md** - 复杂工作流
   - 多分支 Pipeline
   - 流连接 (Join)
   - 迭代处理
   - 窗口和聚合

## 验证清单

- [x] 所有基础教程导入路径已更新
- [x] GitHub 链接指向正确的示例文件
- [x] advanced-rag.md 包含 UnifiedInferenceClient 示例
- [x] performance-tuning.md 包含 Control Plane 调度内容
- [x] 代码示例与 examples/tutorials/ 中的实际代码保持一致
- [x] 无遗留的 `sage.core.api` 导入

## 相关任务

- Task 4: 跨层文档清理 (cross-layer/) - 已完成
- Task 5: 归档清理 - 已完成
- 文件名标准化 (UPPER_SNAKE_CASE.md) - 已完成

---

**下一步建议**:
1. 完善 fault-tolerance.md 和 complex-workflows.md 的具体内容
2. 检查 guides/ 目录下的 API 文档是否需要同步更新
3. 运行文档构建验证链接有效性
