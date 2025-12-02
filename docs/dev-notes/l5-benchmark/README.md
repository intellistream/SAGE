# L5 Benchmark Notes

`sage-benchmark` 属于 L5（应用 & 评测层），目前已经包含四类基准套件。该目录用于追踪这些套件的设计、迁移、以及与 `examples/` 的对齐情况。

| Suite | 位置 | 作用 | 入口 / 快速命令 | 依赖 / 数据 |
| --- | --- | --- | --- | --- |
| `benchmark_rag` | `packages/sage-benchmark/src/sage/benchmark/benchmark_rag/` | RAG 管道基准，含 `implementations/`, `evaluation/`, `config/` | `python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment`、`python -m ...implementations.pipelines.qa_dense_retrieval_milvus` | 需要 `packages/sage-benchmark/src/sage/data/qa/` 数据子模块、Milvus/Chroma/FAISS 组件、`examples/apps` 不再直接附带 RAG 数据 |
| `benchmark_memory` | `.../benchmark_memory/` | 内存系统（SAGE Memory Service）吞吐/延迟评测；包含 `experiment/`, `evaluation/` | `python -m sage.benchmark.benchmark_memory.experiment.run_memory_experiment` (示例) | 依赖 `sage.middleware.components.sage_mem`、自带 yaml 配置；README 待补内容 |
| `benchmark_libamm` | `.../benchmark_libamm/` | LibAMM 矩阵乘性能基准 & C++ 评测 | `cmake .. && cmake --build .`、`python pythonTest.py` | 数据存放于 `packages/sage-benchmark/src/sage/data/libamm-benchmark/` (来自 `sageData` 子模块) |
| `benchmark_scheduler` | `.../benchmark_scheduler/` | 调度策略比较（Ray vs Local 等），目前提供 `scheduler_comparison.py` | `python -m sage.benchmark.benchmark_scheduler.scheduler_comparison` | 使用 `examples/tutorials/L2-platform/scheduler/` 同源代码，主要依赖 `sage.kernel` 调度接口 |

## 当前状态（2025-11）

1. **RAG 示例彻底迁出 `examples/`**：所有 RAG/向量数据库示例均集中在 `benchmark_rag/implementations/`；`examples/tutorials/` 仅保留入门级示例。
2. **数据子模块统一管理**：`packages/sage-benchmark/src/sage/data` 作为 git submodule，包含 `qa_knowledge_base.*`, `queries.jsonl`, `libamm-benchmark` 数据。任何新的基准数据应放入该子模块或 `.sage/` 缓存（避免重新引入 `examples/data/`).
3. **CI 策略**：
	- `benchmark_rag` 和 `benchmark_memory` 默认标记为 `slow`，由 `sage-dev project test --coverage` 的扩展阶段触发。
	- `benchmark_libamm` 采用独立 CMake 构建，不在常规 CI 中运行；本地需要 `cmake`, `openblas` 等依赖。
4. **待补文档**：`benchmark_memory/README.md` 为空，需要在未来 PR 中补充实验说明；若新增 suite，请在此 dev-note 追加行并在 `docs-public` 对应章节更新。

## 建议工作流

1. **提交新的 benchmark**：
	- 在 `packages/sage-benchmark/src/sage/benchmark/<suite>/` 内新增目录与 README。
	- 如果需要示例/入口脚本，可在 `examples/tutorials/L5-apps/` 或 `examples/apps/` 中添加轻量包装。
	- 将运行命令、依赖、数据路径同步到本 README 与 docs-public（参考 `docs-public/docs_src/guides/packages/sage-benchmark/`).
2. **数据管理**：大体量数据放入 `packages/sage-benchmark/src/sage/data/` 子模块；运行期产物写入 `.sage/benchmark_results/`。
3. **测试标签**：在任何 CLI/脚本文件头部添加 `@test_category: benchmark`、`@test_speed: slow`、`@test_skip_ci: true/false` 等元数据，以便 `sage-dev project test` 分类执行。

## 参考

- `packages/sage-benchmark/README.md`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_rag/README.md`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/README.md`
- `packages/sage-benchmark/src/sage/data/README.md` (数据目录)
- `docs-public/docs_src/guides/packages/sage-benchmark/`（公共文档，若不存在需创建）
