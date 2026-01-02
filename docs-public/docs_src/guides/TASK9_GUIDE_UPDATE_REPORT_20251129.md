# Task 9 – Guides Update Report (2025-11-29)

## Modified Files

| 文件                                      | 目的                                                                                                                                                              |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `guides/packages/sage-libs/embedding.md`  | 重写为新的 Embedding 架构，添加 `UnifiedInferenceClient`、`EmbeddingFactory`、`EmbeddingClientAdapter`、`EmbeddingService` 等用法及端口配置、最佳实践、迁移指南。 |
| `guides/packages/sage-libs/agents.md`     | 从空白状态扩展为完整的 Agent 框架指南，涵盖 Profile、Planner、MCP Registry、AgentRuntime、预置 Bot 以及与 `UnifiedInferenceClient`、Memory 的集成。               |
| `guides/packages/sage-common/overview.md` | 添加 sageLLM Control Plane、Embedding 服务、SagePorts 说明与端口表，提供完整的 `UnifiedInferenceClient` / `EmbeddingFactory` 示例并更新架构图。                   |
| `guides/deployment/index.md`              | 扩展部署章节，新增 `sage stack` 快速启动命令、LLM/Embedding/Gateway 独立部署步骤、端口管理、环境变量模板以及常见问题。                                            |
| `guides/packages/sage-libs/rag.md`        | 在生成器章节加入 `sage stack` + `UnifiedInferenceClient` 的推荐集成示例，指引用户复用统一推理客户端。                                                             |

## Verified (No Changes Needed)

| 目录                               | 结果                                                    |
| ---------------------------------- | ------------------------------------------------------- |
| `guides/packages/sage-middleware/` | 现有 NeuroMem / Memory 文档已同步至最新实现，无需修改。 |

## Outstanding Issues / Follow-ups

- 暂无。

## Next Steps

- 若后续在 Task 10/11 中更新教程与导航，请引用本报告列出的文件以保持指南和示例一致。
