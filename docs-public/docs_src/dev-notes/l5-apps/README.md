# L5 Apps Dev Notes

面向 L5（应用层）示例与 `examples/` 目录的最新状态记录。聚焦以下内容：

- `examples/tutorials/` 中与应用层有关的学习路径
- `examples/apps/` 下的应用入口脚本与 `sage-apps` 包的衔接
- 数据、配置、CI 约束等会影响应用示例可运行性的决策

## 当前状态（2025-11）

| 路径                                      | 角色                    | 现状摘要                                                                                                                                                                    |
| ----------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `examples/tutorials/`                     | 教程主目录              | 2025-10-29 起按 L1-L6 架构分层，`L5-apps/` 目前仅含 README，占位等待示例补齐。                                                                                              |
| `examples/apps/`                          | 应用入口                | 包含 `run_article_monitoring.py`, `run_auto_scaling_chat.py`, `run_medical_diagnosis.py`, `run_smart_home.py`, `run_video_intelligence.py`，均通过 `sage.apps.*` 对应实现。 |
| `packages/sage-apps/`                     | 应用实现                | 提供实际业务逻辑与依赖，入口脚本仅负责参数解析与调用。                                                                                                                      |
| `packages/sage-benchmark/`                | 高级 RAG/benchmark 示例 | 原 `examples/rag/` 与 RAG 数据迁入此处，示例通过 `benchmark_rag` 目录提供。                                                                                                 |
| `examples/tutorials/L3-libs/agents/data/` | Agent 示例数据          | 保存 `agent_queries*.jsonl` 等轻量数据；原 `examples/data` 目录已移除，仅保留遗留符号链接，待后续删掉。                                                                     |

## 关键决策与结论

1. **示例分层**：示例与教程以 SAGE 6 层架构为单位维护，任何跨层依赖必须回落到下层实现。应用层示例应仅依赖 `sage-apps` 暴露的 API。详见
   `examples/tutorials/README.md`。
1. **入口与实现解耦**：`examples/apps/*.py` 仅提供 CLI/参数校验，核心逻辑位于
   `packages/sage-apps/src/sage/apps/*`。新增或调整应用时，先在包内实现，再补入口脚本和 README。
1. **数据与配置收敛**：教程示例使用就近的数据与配置目录（如 `L3-libs/agents/data/`）；更大的语料与评测素材统一存放在
   `packages/sage-benchmark/src/sage/data/`，不再放在 `examples/data/`。
1. **测试策略**：入口脚本包含 `@test_*` 元数据（参见 `run_video_intelligence.py`）以供 `sage-dev project test`
   分类运行。应用示例普遍标记为 `slow` 并在 CI 中跳过，防止缺少外部资源时失败。

## 已完成的主要工作

- 2024-10 ~ 2025-10：完成 legacy `agents/`, `memory/`, `rag/`, `service/` 等目录向 L 层结构迁移。
- 2025-10-29：`examples/tutorials/` 结构重排并新增分层 README/学习路径。
- 2025-11：RAG 基准示例与大体量数据同步至 `packages/sage-benchmark`；`examples/apps` 新增 3 个入口脚本（auto-scaling
  chat、smart home、article monitoring）。

### 医疗诊断应用：特征抽取实现概览

在 `copilot/extract-features-with-models` 分支中，完成了医疗诊断应用中图像特征抽取从“随机特征”到“预训练模型特征”的升级，对应实现集中在
`ImageAnalyzer` 以及其单元测试与 Demo：

- **模型支持**：集成 CLIP (`openai/clip-vit-base-patch32`) 与 DINOv2 (`facebook/dinov2-base`)，自动检测 GPU/CPU。
- **特征质量**：输出 L2 归一化向量（CLIP 512 维、DINOv2 768 维），统一用于相似度检索。
- **健壮性设计**：模型下载失败或运行异常时，回退到可控的 mock 特征，保证 Demo 与上层 Agent 不会崩溃。
- **配置驱动**：通过 `agent_config.yaml` 中的 `image_processing.feature_extraction`
  字段选择模型与维度，保持应用层仅依赖配置而非硬编码。
- **完整测试链路**：`test_image_analyzer.py` 覆盖模型初始化、特征抽取、错误处理与集成流程，并提供
  `examples/apps/demo_feature_extraction.py` 作为交互式示例脚本。

> 详细实现过程与性能评估可参考 `archive/feature-extraction-implementation.md`；对于新增应用示例，推荐沿用“配置驱动 + 预训练模型封装 + Demo
> \+ 测试”的组合模式。

## 待办与风险

1. **补齐 L5 教程示例**：`examples/tutorials/L5-apps/` 仍缺少代码示例，可考虑从 `examples/apps`
   中提炼裁剪版。（阻塞：需要确定可开源的业务逻辑子集）。
1. **修复数据符号链接**：`examples/data -> tutorials/agents/data` 目前指向不存在的目录，后续需要移除该符号链接并更新仍引用老路径的配置（在
   `tools/pre-commit-config.yaml` 中尚有遗留）。
1. ~~**更新 `examples/apps/README.md`**：文件仍只提到 2 个应用，需要覆盖当前 5 个入口及对应依赖标签。~~ ✅ 已更新（2025-11-29）

## 参考资料

- `examples/README.md`
- `examples/tutorials/README.md`
- `examples/apps/README.md`
- `packages/sage-apps/README.md`
- `packages/sage-benchmark/README.md`
- `docs-public/docs_src/dev-notes/package-architecture.md`
