# docs-src 全量刷新任务指引

> 目标：在不破坏层级约束的前提下，让 `docs-public/docs_src` 与当前代码实现保持 1:1 对齐。以下 5 组任务可以并行推进，每组任务需先对照源码再落地文档，所有输出统一走
> PR 模板并互相交叉评审。

## 任务 A · 架构与分层基线

- **范围**：`docs-public/docs_src/dev-notes/package-architecture.md`、`concepts/architecture/overview.md`、`concepts/architecture/package-structure.md`
- **代码对照**：`packages/` 下 10+ 包的
  `pyproject.toml`、`packages/sage-platform/src/sage/platform/**`、`packages/sage-common/src/sage/common/config/layers.py`
- **重点**：
  1. 复核 L1-L6 描述是否与最新包职责一致（尤其是 2025 Q4 新增的 `sage-platform`、`sage-cli` 扩展点和 `sage-tools` CLI 合规说明）。
  1. 加入 `register_rpc_queue_factory` 等跨层工厂模式示例，解释“接口在 L2、实现自注册于 L3”的模式，标注真实文件路径。
  1. 在架构图 + Layer 表中补充当前测试通过率、层间依赖、C++
     扩展位置（`packages/sage-middleware/src/sage/middleware/components/**`）等动态指标。
- **交付物**：更新后的三份文档（含变更日志区块）+ 1 张 ASCII/PlantUML 层级图。

## 任务 B · sageLLM Control Plane & 服务栈

- **范围**：`guides/packages/sage-common/overview.md`、`api-reference/common/index.md`、`tutorials/advanced/performance-tuning.md`、`tutorials/advanced/advanced-rag.md`
- **代码对照**：`packages/sage-llm-core/src/sage/llm/**`、`packages/sage-common/src/sage/common/components/sage_embedding/**`、`packages/sage-common/src/sage/common/config/ports.py`、`packages/sage-common/src/sage/common/config/network.py`
- **重点**：
  1. 重新绘制 Control Plane 架构（RequestClassifier → HybridSchedulingPolicy → ExecutionCoordinator /
     EmbeddingExecutor），确认 API 名称与源码一致。
  1. 明确 `sage llm serve`、`create_with_control_plane()`、`EmbeddingFactory + EmbeddingClientAdapter`
     的差异场景，并补充端口表引用 `SagePorts` 常量，禁止硬编码端口示例。
  1. 加入 WSL2 端口回退、`detect_china_mainland()` + `ensure_hf_mirror_configured()` 自动镜像流程，以及 `.env` 样例。
- **交付物**：更新 4 篇文档 + 1 份控制面示例代码块（含多实例配置与 SLA 说明）。

## 任务 C · 开发流程与工具链

- **范围**：`developers/development-setup.md`、`developers/commands.md`、`developers/ci-cd.md`、`getting-started/installation.md`（若缺则新增）
- **代码对照**：`quickstart.sh`、`manage.sh`、`tools/install/check_tool_versions.sh`、`sage-dev`
  CLI（`packages/sage-tools/src/sage/tools/dev/**`）
- **重点**：
  1. 用“交互式 vs 非交互式”流程图描述 `quickstart.sh`
     选项（`--dev/--core/--standard/--full`、`--pip/--conda`、`--sync-submodules`）。
  1. 补全 CI 安装矩阵（GitHub Actions、Conda、国内自建 runner），解释 `unset CI GITHUB_ACTIONS` 与
     `SAGE_FORCE_CHINA_MIRROR=true` 的原因，并引用脚本位置。
  1. 更新 `sage-dev` 子命令表（project test/quality/examples/docs 等），将
     `tools/pre-commit-config.yaml`、`tools/ruff.toml` 的版本约束写成操作步骤。
- **交付物**：文档更新 + 新增的流程示意图（ASCII 亦可） + `developers/commands.md` 内的命令速查表。

## 任务 D · 示例与教程联动

- **范围**：`docs-public/docs_src/tutorials/**/*`、`guides/packages/*` 中涉及示例的部分
- **代码对照**：`examples/tutorials/`（尤其是
  `L3-kernel/cpu_node_demo.py`、`LLM/control_plane_sample.py`）、`examples/apps/`、`docs/dev-notes/l3-kernel/cpu-node-setup.md`
- **重点**：
  1. 为每个教程附上“源码入口 + 运行命令 + 预期日志”三件套，确保路径真实可执行。
  1. 把过时的 API（如旧版 `sage.libs.io_utils`、`EmbeddingFactory.embed(texts=...)`）替换为当前实现，并在文档中标注迁移提示。
  1. 在高阶教程中加入“Control Plane 模式 + 作业管理 + 质量守护（`sage-dev quality`）”的综合示例，展示端到端 pipeline。
- **交付物**：更新后的教程正文 + 1 份示例清单表（列出教程 \<-> `examples/` 文件映射）。

## 任务 E · API Reference & 配置一致性

- **范围**：`api-reference/index.md`、`api-reference/common/index.md`、`concepts/architecture/design-decisions/*`、`community/faq.md`
- **代码对照**：`.env.template`、`packages/sage-common/src/sage/common/config/*.py`、`packages/sage-llm-gateway/src/sage/gateway/**`、`packages/sage-cli/src/sage/cli/commands/**`
- **重点**：
  1. 保证 OpenAI 兼容 API、Gateway、Studio、Embedding、Benchmark 端口/环境变量写法全部引用 `SagePorts` &
     `SageEnvKeys`，并提供 `curl`/`UnifiedInferenceClient` 双示例。
  1. 将 `.env.template` 中的关键变量（`OPENAI_API_KEY`, `HF_TOKEN`, `SAGE_CHAT_*`）解释搬到 API
     Reference，注明何时需要真实云端 Key、何时允许本地 mock。
  1. 整理常见 FAQ（WSL2 端口、子模块、C++ 构建、CI 失败定位）并链接到对应工具/脚本。
- **交付物**：API Reference 更新 + FAQ 扩写 + 一张配置决策对照表（场景 / 变量 / 参考脚本）。

______________________________________________________________________

- **质控要求**：每个任务完成后需运行 `sage-dev quality --check-only` 与相关示例/单测，截图或粘贴关键日志到 PR 描述。
- **协同方式**：每日快速站会同步阻塞项，若文档互相引用需开共享草稿（可在 `docs-public/docs_src/templates/` 下建临时文件）。
